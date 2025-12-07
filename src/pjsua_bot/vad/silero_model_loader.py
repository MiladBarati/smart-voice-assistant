"""Silero VAD model loading and backend selection.

This module handles loading Silero VAD models using either PyTorch/TorchScript
or ONNX Runtime, with fallback strategies for compatibility across PyTorch versions.
"""

from __future__ import annotations

import inspect
import os
import shutil
from typing import Any

from .silero_diagnostics import (
    log_cache_cleared,
    log_model_loaded,
    log_model_loading_error,
    log_model_loading_strategy,
    log_onnx_model_info,
    log_onnx_providers,
    log_reusing_cached_model,
)

# Optional dependency imports
_torch_error: str | None = None
torch: Any
try:
    import torch as _torch_import
except Exception as exc:  # pragma: no cover - optional dependency at runtime
    torch = None
    _torch_error = str(exc)
else:
    torch = _torch_import
    _torch_error = None

torchaudio: Any
try:
    import torchaudio as _torchaudio_import
except Exception as exc:  # pragma: no cover - optional dependency at runtime
    torchaudio = None
    if _torch_error is None:
        _torch_error = str(exc)
else:
    torchaudio = _torchaudio_import
_TORCH_AVAILABLE = torch is not None and torchaudio is not None
_TORCH_ERROR = None if _TORCH_AVAILABLE else _torch_error

onnxruntime: Any
try:
    import onnxruntime as _onnxruntime_import
except Exception:  # pragma: no cover - optional dependency at runtime
    onnxruntime = None
else:
    onnxruntime = _onnxruntime_import
_ONNXRUNTIME_AVAILABLE = onnxruntime is not None


class SileroModelLoader:
    """Handles loading and caching of Silero VAD models.

    Supports both TorchScript and ONNX backends with automatic fallback strategies.
    Uses class-level caching to share models across instances.
    """

    # Class-level cache for the loaded model to share across instances
    _shared_model: Any = None
    _shared_onnx_session: Any = None
    _shared_use_onnx: bool = False
    _model_loaded: bool = False

    @classmethod
    def get_providers(cls) -> list[str]:
        """Get ONNX Runtime execution providers based on available hardware.

        Returns:
            List of provider names, with CUDA first if available, else CPU only.
        """
        if torch and torch.cuda.is_available():
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    @classmethod
    def clear_cache_if_needed(cls) -> None:
        """Proactively clear cache for PyTorch 2.5+ to avoid _construct errors.

        This is a known issue with PyTorch 2.5+ and TorchScript models.
        Only clears cache if model hasn't been loaded yet.
        """
        if cls._model_loaded:
            return

        if not _TORCH_AVAILABLE:
            return

        try:
            torch_version = torch.__version__
            # Check if PyTorch version is 2.5 or higher
            major, minor = map(int, torch_version.split(".")[:2])
            if major > 2 or (major == 2 and minor >= 5):
                cache_dir = os.path.join(
                    os.path.expanduser("~"), ".cache", "torch", "hub"
                )
                silero_cache = os.path.join(cache_dir, "snakers4_silero-vad_master")
                if os.path.exists(silero_cache):
                    log_cache_cleared(torch_version)
                    shutil.rmtree(silero_cache, ignore_errors=True)
        except Exception:
            # Ignore cache clearing errors, continue with loading
            pass

    @classmethod
    def clear_cache_on_error(cls) -> None:
        """Clear cache when encountering _construct errors during loading."""
        try:
            cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub")
            silero_cache = os.path.join(cache_dir, "snakers4_silero-vad_master")
            if os.path.exists(silero_cache):
                log_cache_cleared("(error recovery)")
                shutil.rmtree(silero_cache, ignore_errors=True)
        except Exception:
            # Ignore cache clearing errors
            pass

    @classmethod
    def get_loading_strategies(cls) -> list[dict[str, Any]]:
        """Get list of model loading strategies to try in order.

        Returns:
            List of strategy dictionaries with loading parameters.
        """
        return [
            # Strategy 1: ONNX with torch.hub.load (best for PyTorch 2.5+)
            {
                "force_reload": False,
                "trust_repo": True,
                "onnx": True,
                "name": "ONNX via torch.hub force_reload",
            },
            # Strategy 2: ONNX normal load
            {
                "force_reload": False,
                "trust_repo": True,
                "onnx": True,
                "name": "ONNX via torch.hub normal load",
            },
            # Strategy 3: TorchScript with force reload and trust_repo
            {
                "force_reload": True,
                "trust_repo": True,
                "onnx": False,
                "name": "TorchScript force_reload with trust_repo",
            },
            # Strategy 4: TorchScript normal load with trust_repo
            {
                "force_reload": False,
                "trust_repo": True,
                "onnx": False,
                "name": "TorchScript normal load with trust_repo",
            },
            # Strategy 5: TorchScript force reload without trust_repo (original)
            {
                "force_reload": True,
                "trust_repo": False,
                "onnx": False,
                "name": "TorchScript force_reload (original)",
            },
            # Strategy 6: TorchScript normal load (original fallback)
            {
                "force_reload": False,
                "trust_repo": False,
                "onnx": False,
                "name": "TorchScript normal load (original)",
            },
        ]

    @classmethod
    def try_reuse_cached_model(cls, instance: Any) -> bool:
        """Try to reuse a previously loaded model from class cache.

        Args:
            instance: SileroVAD instance to populate with cached model.

        Returns:
            True if cached model was reused, False otherwise.
        """
        if not cls._model_loaded:
            return False

        if cls._shared_use_onnx:
            if cls._shared_onnx_session is not None:
                instance._onnx_session = cls._shared_onnx_session
                instance._use_onnx = True
                instance.available = True
                instance._load_error = None
                log_reusing_cached_model("ONNX session")
                return True
            elif cls._shared_model is not None:
                instance._model = cls._shared_model
                instance._use_onnx = True
                instance.available = True
                instance._load_error = None
                log_reusing_cached_model("ONNX wrapper")
                return True
        else:
            if cls._shared_model is not None:
                instance._model = cls._shared_model
                instance._use_onnx = False
                instance.available = True
                instance._load_error = None
                log_reusing_cached_model("TorchScript")
                return True

        return False

    @classmethod
    def load_model(cls, instance: Any) -> None:
        """Load Silero VAD model using available backends.

        Args:
            instance: SileroVAD instance to populate with loaded model.
        """
        if not _TORCH_AVAILABLE:
            instance._load_error = (
                f"torch/torchaudio not available: {_TORCH_ERROR or 'import failed'}"
            )
            return

        # Try to reuse cached model first
        if cls.try_reuse_cached_model(instance):
            return

        # Clear cache proactively for PyTorch 2.5+ compatibility
        cls.clear_cache_if_needed()

        # Try multiple loading strategies
        strategies = cls.get_loading_strategies()
        last_error = None
        cache_cleared = False

        for strategy_idx, strategy in enumerate(strategies):
            try:
                log_model_loading_strategy(
                    strategy_idx + 1, len(strategies), strategy["name"]
                )

                # If we hit a _construct error in previous attempt,
                # try clearing cache once
                if last_error and "_construct" in str(last_error) and not cache_cleared:
                    cls.clear_cache_on_error()
                    cache_cleared = True
                    # After clearing cache, force reload on this attempt
                    strategy = strategy.copy()
                    strategy["force_reload"] = True

                # Build kwargs for torch.hub.load
                kwargs = {
                    "repo_or_dir": "snakers4/silero-vad",
                    "model": "silero_vad",
                    "force_reload": strategy["force_reload"],
                    "onnx": strategy["onnx"],
                }
                # trust_repo was added in PyTorch 1.13+, use it if available
                if strategy.get("trust_repo") and hasattr(torch.hub, "load"):
                    sig = inspect.signature(torch.hub.load)
                    if "trust_repo" in sig.parameters:
                        kwargs["trust_repo"] = strategy["trust_repo"]

                model_result = torch.hub.load(**kwargs)

                # Handle ONNX models differently
                if strategy["onnx"]:
                    if not _ONNXRUNTIME_AVAILABLE:
                        log_model_loading_error(
                            strategy_idx + 1,
                            "ONNX Runtime not available, skipping ONNX strategy",
                        )
                        raise ImportError(
                            "ONNX Runtime not available, skipping ONNX strategy"
                        )

                    # torch.hub.load with onnx=True returns (model, utils) tuple
                    # where model is a callable ONNX wrapper
                    if isinstance(model_result, tuple):
                        onnx_model = model_result[0]
                    else:
                        onnx_model = model_result

                    # Check if it's a callable ONNX wrapper FIRST (most common case)
                    if callable(onnx_model):
                        instance._model = onnx_model
                        cls._shared_model = onnx_model
                        instance._use_onnx = True
                        cls._shared_use_onnx = True
                        instance.available = True
                        cls._model_loaded = True
                        instance._load_error = None
                        log_model_loaded(strategy["name"], "callable wrapper")
                        cls.initialize_onnx_states(instance)
                        return
                    elif isinstance(onnx_model, str) and os.path.exists(onnx_model):
                        # If it's a string path, load it with ONNX Runtime
                        providers = cls.get_providers()
                        log_onnx_providers(providers)
                        instance._onnx_session = onnxruntime.InferenceSession(
                            onnx_model, providers=providers
                        )
                        log_onnx_model_info(instance._onnx_session)
                        cls._shared_onnx_session = instance._onnx_session
                        instance._use_onnx = True
                        cls._shared_use_onnx = True
                        instance.available = True
                        cls._model_loaded = True
                        instance._load_error = None
                        log_model_loaded(strategy["name"], f"from path: {onnx_model}")
                        cls.initialize_onnx_states(instance)
                        return
                    else:
                        raise ValueError(
                            f"ONNX model result format not recognized: "
                            f"{type(onnx_model)}"
                        )
                else:
                    # Handle TorchScript models (original logic)
                    if isinstance(model_result, tuple):
                        instance._model = model_result[0]  # Extract model from tuple
                    else:
                        instance._model = model_result
                    assert instance._model is not None
                    instance._model.eval()
                    cls._shared_model = instance._model
                    instance._use_onnx = False
                    cls._shared_use_onnx = False
                    instance.available = True
                    cls._model_loaded = True
                    instance._load_error = None
                    log_model_loaded(strategy["name"], "TorchScript")
                    return
            except Exception as e:
                last_error = e
                log_model_loading_error(strategy_idx + 1, f"{type(e).__name__}: {e}")
                # Continue to next strategy
                continue

        # All strategies failed
        instance._model = None
        instance.available = False
        error_msg = str(last_error) if last_error else "unknown error"
        instance._load_error = (
            f"model loading failed after trying all strategies: {error_msg}"
        )

    @classmethod
    def initialize_onnx_states(cls, instance: Any) -> None:
        """Initialize ONNX hidden states based on model input requirements.

        Args:
            instance: SileroVAD instance to initialize states on.
        """
        if instance._onnx_session is None:
            return

        input_names = [inp.name for inp in instance._onnx_session.get_inputs()]
        if "h" in input_names and "c" in input_names:
            # Separate h and c states (newer Silero VAD v4/v5)
            # Shape is typically (2, 1, 64) for 16kHz
            import numpy as np

            instance._onnx_h = np.zeros((2, 1, 64), dtype=np.float32)
            instance._onnx_c = np.zeros((2, 1, 64), dtype=np.float32)
            instance._onnx_state = None
            from .silero_diagnostics import log_onnx_states_initialized

            log_onnx_states_initialized("h/c", instance._onnx_h.shape)
        elif "state" in input_names:
            # Combined state (older versions)
            import numpy as np

            instance._onnx_state = np.zeros((2, 1, 128), dtype=np.float32)
            instance._onnx_h = None
            instance._onnx_c = None
            from .silero_diagnostics import log_onnx_states_initialized

            log_onnx_states_initialized("combined", instance._onnx_state.shape)
        else:
            from .silero_diagnostics import log_onnx_unknown_state_format

            log_onnx_unknown_state_format(input_names)
