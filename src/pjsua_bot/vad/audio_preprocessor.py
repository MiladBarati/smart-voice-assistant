"""Audio preprocessing utilities for VAD.

This module handles all audio preprocessing steps required before VAD inference:
    - Conversion from numpy arrays to PyTorch tensors
    - Gain adjustment for low-level telephony audio
    - Resampling to target sample rate (8000 or 16000 Hz)
    - Window size calculation for different sample rates

The preprocessor caches resamplers by input sample rate to avoid
recreating them for each audio chunk.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

import numpy as np

# Optional dependency imports
try:
    import torch as _torch
except Exception:  # pragma: no cover
    _torch = None  # type: ignore[assignment]

try:
    import torchaudio
except Exception:  # pragma: no cover
    torchaudio = None


class AudioPreprocessor:
    """Handles audio preprocessing: resampling and gain adjustment.

    Prepares audio for VAD inference by converting to tensors, applying
    gain boost for telephony audio, and resampling to the target rate.

    Example:
        preprocessor = AudioPreprocessor(
            target_sample_rate=16000,
            gain=3.0
        )
        waveform, actual_sr = preprocessor.preprocess(audio_array, input_sr=8000)
    """

    def __init__(self, target_sample_rate: int = 16000, gain: float = 3.0):
        """Initialize audio preprocessor.

        Args:
            target_sample_rate: Target sample rate for VAD model.
            gain: Gain multiplier for low-level telephony audio.
        """
        self.target_sample_rate = target_sample_rate
        self.gain = gain
        self._resamplers: dict[int, Any] = {}  # Cache resamplers by input SR

    def preprocess(
        self, audio: np.ndarray, input_sr: int
    ) -> Tuple[Optional[Any], Optional[int]]:
        """Preprocess audio: convert to tensor, apply gain, resample if needed.

        Args:
            audio: Input audio as numpy array (mono float32).
            input_sr: Input sample rate in Hz.

        Returns:
            Tuple of (preprocessed_tensor, actual_sample_rate) or (None, None) on error.
        """
        if _torch is None:
            return None, None

        # Convert to torch tensor
        waveform = _torch.from_numpy(audio).unsqueeze(0)  # (1, N)

        # Apply gain boost for low-level telephony audio
        waveform = (waveform * self.gain).clamp(-1.0, 1.0)

        # Resample if needed
        actual_sr: int = input_sr
        if input_sr != self.target_sample_rate:
            resample_result = self._resample(waveform, input_sr)
            resampled_waveform, resampled_sr = resample_result
            if resampled_waveform is None or resampled_sr is None:
                return None, None
            waveform = resampled_waveform
            actual_sr = resampled_sr

        return waveform, actual_sr

    def _resample(
        self, waveform: Any, input_sr: int
    ) -> Tuple[Optional[Any], Optional[int]]:
        """Resample waveform to target sample rate.

        Args:
            waveform: Input waveform tensor.
            input_sr: Input sample rate.

        Returns:
            Tuple of (resampled_waveform, actual_sr) or (None, None) on error.
        """
        if torchaudio is None:
            # Can't resample - check if original rate is supported
            if input_sr in (8000, 16000):
                return waveform, input_sr
            return None, None

        # Get or create resampler
        resampler = self._get_resampler(input_sr)
        if resampler is None:
            # Resampler creation failed - check if original rate is supported
            if input_sr in (8000, 16000):
                return waveform, input_sr
            return None, None

        # Perform resampling
        with _torch.no_grad():
            resampled = resampler(waveform)

        return resampled, self.target_sample_rate

    def _get_resampler(self, input_sr: int) -> Optional[Any]:
        """Get or create resampler for given input sample rate."""
        if torchaudio is None:
            return None

        if input_sr not in self._resamplers:
            self._resamplers[input_sr] = torchaudio.transforms.Resample(
                orig_freq=input_sr,
                new_freq=self.target_sample_rate,
            )

        return self._resamplers[input_sr]

    @staticmethod
    def get_window_size(sample_rate: int) -> Optional[int]:
        """Get required window size for given sample rate.

        Silero VAD requires exactly 32ms windows:
        - 256 samples for 8000 Hz
        - 512 samples for 16000 Hz

        Args:
            sample_rate: Sample rate in Hz.

        Returns:
            Window size in samples, or None if unsupported.
        """
        if sample_rate == 8000:
            return 256
        elif sample_rate == 16000:
            return 512
        else:
            return None
