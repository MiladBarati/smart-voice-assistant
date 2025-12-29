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

    The loader uses a modular architecture with programmatic strategy generation,
    unified cache management, and separate handlers for ONNX and TorchScript models.
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
    def _get_cache_path(cls) -> str:
        """Get the path to the Silero VAD cache directory."""
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub")
        return os.path.join(cache_dir, "snakers4_silero-vad_master")

    @classmethod
    def clear_cache(cls, reason: str = "manual") -> None:
        """Clear the Silero VAD cache directory.

        Args:
            reason: Reason for clearing cache (for logging).
        """
        try:
            cache_path = cls._get_cache_path()
            if os.path.exists(cache_path):
                log_cache_cleared(reason)
                shutil.rmtree(cache_path, ignore_errors=True)
        except Exception:
            # Ignore cache clearing errors
            pass

    @classmethod
    def _should_clear_cache_proactively(cls) -> bool:
        """Check if cache should be cleared proactively for PyTorch 2.5+."""
        if cls._model_loaded or not _TORCH_AVAILABLE:
            return False

        try:
            torch_version = torch.__version__
            major, minor = map(int, torch_version.split(".")[:2])
            return major > 2 or (major == 2 and minor >= 5)
        except Exception:
            return False

    @classmethod
    def _generate_strategies(cls) -> list[dict[str, Any]]:
        """Generate model loading strategies programmatically.

        Returns:
            List of strategy dictionaries ordered by preference.
        """
        strategies = []

        # ONNX strategies (preferred for PyTorch 2.5+)
        for force_reload in [False, True]:
            strategies.append(
                {
                    "force_reload": force_reload,
                    "trust_repo": True,
                    "onnx": True,
                    "name": (
                        f"ONNX via torch.hub "
                        f"({'force_reload' if force_reload else 'normal'})"
                    ),
                }
            )

        # TorchScript strategies with trust_repo
        for force_reload in [True, False]:
            strategies.append(
                {
                    "force_reload": force_reload,
                    "trust_repo": True,
                    "onnx": False,
                    "name": (
                        f"TorchScript {'force_reload' if force_reload else 'normal'} "
                        f"with trust_repo"
                    ),
                }
            )

        # TorchScript fallback strategies (original behavior)
        for force_reload in [True, False]:
            strategies.append(
                {
                    "force_reload": force_reload,
                    "trust_repo": False,
                    "onnx": False,
                    "name": (
                        f"TorchScript {'force_reload' if force_reload else 'normal'} "
                        f"(fallback)"
                    ),
                }
            )

        return strategies

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
            # Try ONNX session first, then wrapper
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
            # TorchScript model
            if cls._shared_model is not None:
                instance._model = cls._shared_model
                instance._use_onnx = False
                instance.available = True
                instance._load_error = None
                log_reusing_cached_model("TorchScript")
                return True

        return False

    @classmethod
    def _build_hub_kwargs(cls, strategy: dict[str, Any]) -> dict[str, Any]:
        """Build kwargs for torch.hub.load based on strategy.

        Args:
            strategy: Strategy dictionary with loading parameters.

        Returns:
            Dictionary of kwargs for torch.hub.load.
        """
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

        return kwargs

    @classmethod
    def _handle_onnx_model(
        cls, instance: Any, model_result: Any, strategy: dict[str, Any]
    ) -> bool:
        """Handle ONNX model result from torch.hub.load.

        Args:
            instance: SileroVAD instance to populate.
            model_result: Result from torch.hub.load.
            strategy: Strategy dictionary for logging.

        Returns:
            True if model was successfully loaded, False otherwise.
        """
        if not _ONNXRUNTIME_AVAILABLE:
            raise ImportError("ONNX Runtime not available")

        # Extract model from tuple if needed
        onnx_model = (
            model_result[0] if isinstance(model_result, tuple) else model_result
        )

        # Handle callable ONNX wrapper (most common case)
        if callable(onnx_model):
            cls._set_onnx_wrapper(instance, onnx_model, strategy)
            return True

        # Handle ONNX file path
        if isinstance(onnx_model, str) and os.path.exists(onnx_model):
            cls._load_onnx_session(instance, onnx_model, strategy)
            return True

        raise ValueError(f"ONNX model format not recognized: {type(onnx_model)}")

    @classmethod
    def _set_onnx_wrapper(
        cls, instance: Any, model: Any, strategy: dict[str, Any]
    ) -> None:
        """Set ONNX wrapper model on instance and cache.

        Args:
            instance: SileroVAD instance to populate.
            model: Callable ONNX wrapper model.
            strategy: Strategy dictionary for logging.
        """
        instance._model = model
        cls._shared_model = model
        instance._use_onnx = True
        cls._shared_use_onnx = True
        instance.available = True
        cls._model_loaded = True
        instance._load_error = None
        log_model_loaded(strategy["name"], "callable wrapper")
        cls.initialize_onnx_states(instance)

    @classmethod
    def _load_onnx_session(
        cls, instance: Any, model_path: str, strategy: dict[str, Any]
    ) -> None:
        """Load ONNX model from file path using ONNX Runtime.

        Args:
            instance: SileroVAD instance to populate.
            model_path: Path to ONNX model file.
            strategy: Strategy dictionary for logging.
        """
        providers = cls.get_providers()
        log_onnx_providers(providers)
        instance._onnx_session = onnxruntime.InferenceSession(
            model_path, providers=providers
        )
        log_onnx_model_info(instance._onnx_session)
        cls._shared_onnx_session = instance._onnx_session
        instance._use_onnx = True
        cls._shared_use_onnx = True
        instance.available = True
        cls._model_loaded = True
        instance._load_error = None
        log_model_loaded(strategy["name"], f"from path: {model_path}")
        cls.initialize_onnx_states(instance)

    @classmethod
    def _handle_torchscript_model(
        cls, instance: Any, model_result: Any, strategy: dict[str, Any]
    ) -> None:
        """Handle TorchScript model result from torch.hub.load.

        Args:
            instance: SileroVAD instance to populate.
            model_result: Result from torch.hub.load.
            strategy: Strategy dictionary for logging.
        """
        # Extract model from tuple if needed
        model = model_result[0] if isinstance(model_result, tuple) else model_result
        assert model is not None

        model.eval()
        instance._model = model
        cls._shared_model = model
        instance._use_onnx = False
        cls._shared_use_onnx = False
        instance.available = True
        cls._model_loaded = True
        instance._load_error = None
        log_model_loaded(strategy["name"], "TorchScript")

    @classmethod
    def _try_strategy(
        cls, instance: Any, strategy: dict[str, Any], strategy_idx: int, total: int
    ) -> bool:
        """Try loading model with a specific strategy.

        Args:
            instance: SileroVAD instance to populate.
            strategy: Strategy dictionary with loading parameters.
            strategy_idx: Zero-based index of current strategy.
            total: Total number of strategies.

        Returns:
            True if loading succeeded, False otherwise.
        """
        log_model_loading_strategy(strategy_idx + 1, total, strategy["name"])

        kwargs = cls._build_hub_kwargs(strategy)
        model_result = torch.hub.load(**kwargs)

        if strategy["onnx"]:
            return cls._handle_onnx_model(instance, model_result, strategy)
        else:
            cls._handle_torchscript_model(instance, model_result, strategy)
            return True

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

        # Try loading strategies in order
        strategies = cls._generate_strategies()
        last_error = None
        cache_cleared = False

        for idx, strategy in enumerate(strategies):
            try:
                # Clear cache if we hit a _construct error previously
                if last_error and "_construct" in str(last_error) and not cache_cleared:
                    cls.clear_cache("(error recovery)")
                    cache_cleared = True
                    # Force reload after clearing cache
                    strategy = strategy.copy()
                    strategy["force_reload"] = True

                if cls._try_strategy(instance, strategy, idx, len(strategies)):
                    return

            except Exception as e:
                last_error = e
                log_model_loading_error(idx + 1, f"{type(e).__name__}: {e}")
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

        import numpy as np

        from .silero_diagnostics import (
            log_onnx_states_initialized,
            log_onnx_unknown_state_format,
        )

        input_names = [inp.name for inp in instance._onnx_session.get_inputs()]

        if "h" in input_names and "c" in input_names:
            # Separate h and c states (newer Silero VAD v4/v5)
            # Shape is typically (2, 1, 64) for 16kHz
            instance._onnx_h = np.zeros((2, 1, 64), dtype=np.float32)
            instance._onnx_c = np.zeros((2, 1, 64), dtype=np.float32)
            instance._onnx_state = None
            log_onnx_states_initialized("h/c", instance._onnx_h.shape)
        elif "state" in input_names:
            # Combined state (older versions)
            instance._onnx_state = np.zeros((2, 1, 128), dtype=np.float32)
            instance._onnx_h = None
            instance._onnx_c = None
            log_onnx_states_initialized("combined", instance._onnx_state.shape)
        else:
            log_onnx_unknown_state_format(input_names)
