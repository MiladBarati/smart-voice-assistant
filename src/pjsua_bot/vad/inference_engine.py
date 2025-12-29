"""VAD inference engine for running Silero VAD models.

This module provides a unified interface for running VAD inference using
either TorchScript or ONNX Runtime backends. It handles the complexity
of different model formats and state management automatically.

The engine supports:
    - TorchScript models (original PyTorch format)
    - ONNX Runtime sessions (optimized inference)
    - ONNX callable wrappers (torch.hub format)
    - Stateful models with hidden state management (h/c or combined state)

State Management:
    ONNX models are stateful and maintain hidden states between frames.
    The engine automatically manages:
    - Separate h/c states for Silero VAD v4/v5 models
    - Combined state for older model versions
    - State initialization and updates between inference calls
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

# Optional dependency imports
try:
    import torch as _torch
except Exception:  # pragma: no cover
    _torch = None

try:
    import onnxruntime
except Exception:  # pragma: no cover
    onnxruntime = None


class VADInferenceEngine:
    """Handles VAD inference for both TorchScript and ONNX models.
    
    Provides a unified interface for running VAD inference regardless of
    the underlying model format. Automatically handles state management
    for stateful ONNX models.
    
    Example:
        engine = VADInferenceEngine(
            model=torchscript_model,
            use_onnx=False
        )
        prob = engine.infer(frame_tensor, sample_rate=16000)
    """

    def __init__(
        self,
        model: Any = None,
        onnx_session: Any = None,
        use_onnx: bool = False,
    ):
        """Initialize inference engine.

        Args:
            model: TorchScript model or ONNX callable wrapper.
            onnx_session: ONNX Runtime session (if using ONNX).
            use_onnx: Whether to use ONNX backend.
        """
        self._model = model
        self._onnx_session = onnx_session
        self._use_onnx = use_onnx

        # ONNX state management
        self._onnx_state: Optional[np.ndarray] = None
        self._onnx_h: Optional[np.ndarray] = None
        self._onnx_c: Optional[np.ndarray] = None
        self._onnx_input_names: Optional[list[str]] = None

        if self._onnx_session is not None:
            # Only initialize states if not already provided
            # (they may be set externally, e.g., by model loader)
            if (
                self._onnx_state is None
                and self._onnx_h is None
                and self._onnx_c is None
            ):
                self._initialize_onnx_states()
            else:
                # States provided externally, just get input names
                self._onnx_input_names = [
                    inp.name for inp in self._onnx_session.get_inputs()
                ]

    def _initialize_onnx_states(self) -> None:
        """Initialize ONNX hidden states based on model inputs."""
        if self._onnx_session is None:
            return

        self._onnx_input_names = [
            inp.name for inp in self._onnx_session.get_inputs()
        ]

        if "h" in self._onnx_input_names and "c" in self._onnx_input_names:
            # Separate h and c states (Silero VAD v4/v5)
            self._onnx_h = np.zeros((2, 1, 64), dtype=np.float32)
            self._onnx_c = np.zeros((2, 1, 64), dtype=np.float32)
        elif "state" in self._onnx_input_names:
            # Combined state (older versions)
            self._onnx_state = np.zeros((2, 1, 128), dtype=np.float32)

    def infer(self, frame: Any, sample_rate: int) -> float:
        """Run VAD inference on a single frame.

        Args:
            frame: Audio frame tensor/array (1, N) shape.
            sample_rate: Sample rate in Hz.

        Returns:
            Speech probability (0.0 to 1.0).

        Raises:
            RuntimeError: If model is not properly initialized.
        """
        if self._use_onnx:
            return self._infer_onnx(frame, sample_rate)
        else:
            return self._infer_torchscript(frame, sample_rate)

    def _infer_torchscript(self, frame: Any, sample_rate: int) -> float:
        """Run TorchScript model inference."""
        if self._model is None:
            raise RuntimeError("TorchScript model not initialized")
        return self._model(frame, sample_rate).item()

    def _infer_onnx(self, frame: Any, sample_rate: int) -> float:
        """Run ONNX model inference."""
        if self._onnx_session is not None:
            return self._infer_onnx_session(frame, sample_rate)
        elif self._model is not None and callable(self._model):
            # ONNX callable wrapper
            return self._model(frame, sample_rate).item()
        else:
            raise RuntimeError("ONNX model not properly initialized")

    def _infer_onnx_session(self, frame: Any, sample_rate: int) -> float:
        """Run inference using ONNX Runtime session."""
        if self._onnx_session is None:
            raise RuntimeError("ONNX session not initialized")

        # Convert frame to numpy array
        if _torch is not None and isinstance(frame, _torch.Tensor):
            frame_np = frame.cpu().numpy().astype(np.float32)
        else:
            frame_np = np.asarray(frame, dtype=np.float32)

        # Ensure correct shape (1, samples)
        if len(frame_np.shape) == 1:
            frame_np = frame_np.reshape(1, -1)
        elif len(frame_np.shape) == 2 and frame_np.shape[0] > 1:
            frame_np = frame_np[0:1, :]

        # Prepare sample rate
        sr_np = np.array(sample_rate, dtype=np.int64)

        # Build inputs based on model requirements
        onnx_inputs = self._build_onnx_inputs(frame_np, sr_np)

        # Run inference
        outputs = self._onnx_session.run(None, onnx_inputs)

        # Extract probability
        prob = float(outputs[0][0])

        # Update states for next frame
        self._update_onnx_states(outputs)

        return prob

    def _build_onnx_inputs(
        self, frame_np: np.ndarray, sr_np: np.ndarray
    ) -> dict[str, Any]:
        """Build ONNX input dictionary based on model requirements."""
        if self._onnx_input_names is None:
            raise RuntimeError("ONNX input names not initialized")

        if "h" in self._onnx_input_names and "c" in self._onnx_input_names:
            # Separate h and c states
            if self._onnx_h is None:
                self._onnx_h = np.zeros((2, 1, 64), dtype=np.float32)
            if self._onnx_c is None:
                self._onnx_c = np.zeros((2, 1, 64), dtype=np.float32)

            return {
                "input": frame_np,
                "h": self._onnx_h,
                "c": self._onnx_c,
                "sr": sr_np,
            }
        else:
            # Combined state
            if self._onnx_state is None:
                self._onnx_state = np.zeros((2, 1, 128), dtype=np.float32)

            return {
                "input": frame_np,
                "state": self._onnx_state,
                "sr": sr_np,
            }

    def _update_onnx_states(self, outputs: list[Any]) -> None:
        """Update ONNX hidden states from model outputs."""
        if self._onnx_input_names is None:
            return

        if "h" in self._onnx_input_names and "c" in self._onnx_input_names:
            # Separate h and c outputs
            if len(outputs) > 1:
                self._onnx_h = outputs[1]
            if len(outputs) > 2:
                self._onnx_c = outputs[2]
        else:
            # Combined state output
            if len(outputs) > 1:
                self._onnx_state = outputs[1]

