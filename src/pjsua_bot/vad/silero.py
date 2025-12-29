"""Silero VAD integration utilities.

This module provides the main SileroVAD orchestrator class that coordinates
multiple specialized components for incremental voice activity detection
over growing WAV recordings.

Architecture:
    The SileroVAD class orchestrates the following components:
    - StreamingWavReader: Incremental reading of growing WAV files
    - AudioPreprocessor: Audio preprocessing (resampling, gain adjustment)
    - VADInferenceEngine: Model inference (TorchScript/ONNX)
    - ChunkManager: Voice chunk detection and boundary management
    - SilenceTracker: Silence period tracking and bot playback awareness
    - SileroModelLoader: Model loading with fallback strategies

Usage:
    The module is designed to be called periodically from the event pump
    to detect the last time speech was observed from the caller.

    Example:
        vad = SileroVAD(
            wav_path="/path/to/recording.wav",
            config=VADConfig(threshold=0.15),
            chunks_output_dir="/path/to/chunks"
        )
        
        # Periodically process new audio
        vad.process_new_audio(lambda: time.time())
        
        # Check for speech
        if vad.last_speech_time_monotonic:
            time_since_speech = time.time() - vad.last_speech_time_monotonic
            if time_since_speech > 5.0:
                # Hang up after 5 seconds of silence
                hangup()
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from .audio_preprocessor import AudioPreprocessor
from .chunk_manager import ChunkManager
from .config import VADConfig
from .inference_engine import VADInferenceEngine
from .silence import SilenceTracker
from .silero_diagnostics import (
    log_audio_read,
    log_chunk_split_due_to_max_duration,
    log_model_call_error,
    log_no_frames_processed,
    log_processing_stats,
    log_speech_detected,
    log_unsupported_sample_rate,
    log_waveform_too_small,
)
from .silero_model_loader import SileroModelLoader
from .throttled_logger import ThrottledLogger
from .types import VoiceChunk

# Import torch for tensor operations
try:
    import torch as _torch
except Exception:  # pragma: no cover - optional dependency at runtime
    _torch = None  # type: ignore[assignment]

# Import StreamingWavReader from audio_reader
from .audio_reader import StreamingWavReader


class SileroVAD:
    """Incremental VAD over a growing WAV file recorded by PJSUA2.

    This class orchestrates multiple specialized components to provide
    voice activity detection on incrementally growing WAV files. It's designed
    to be called periodically from an event loop to process newly appended
    audio frames and detect speech activity.

    Architecture:
        The class coordinates:
        - StreamingWavReader: Reads new frames from growing WAV file
        - AudioPreprocessor: Preprocesses audio (resampling, gain)
        - VADInferenceEngine: Runs VAD model inference
        - ChunkManager: Detects and manages voice chunks
        - SilenceTracker: Tracks silence periods and bot playback

    Usage:
        Create once per call and call process_new_audio() periodically:

        Example:
            vad = SileroVAD(
                wav_path="/path/to/recording.wav",
                config=VADConfig(threshold=0.15),
                chunks_output_dir="/path/to/chunks"
            )

            # In event loop:
            while call_active:
                vad.process_new_audio(lambda: time.time())

                # Check for silence timeout
                if vad.last_speech_time_monotonic:
                    silence = time.time() - vad.last_speech_time_monotonic
                    if silence > 5.0:
                        hangup()

    Attributes:
        wav_path: Path to the WAV file being monitored
        cfg: VAD configuration
        last_speech_time_monotonic: Timestamp of last detected speech (None if none)
        available: Whether the VAD model is loaded and ready
        reader: StreamingWavReader instance for reading audio
        chunks: ChunkManager instance for chunk management
        silence: SilenceTracker instance for silence tracking
    """

    def __init__(
        self,
        wav_path: str,
        config: Optional[VADConfig] = None,
        chunks_output_dir: Optional[str] = None,
    ):
        self.wav_path = wav_path
        self.cfg = config or VADConfig()
        self.last_speech_time_monotonic: Optional[float] = None
        self.available: bool = False
        self._load_error: Optional[str] = None

        # Modular components
        self.reader = StreamingWavReader(wav_path)
        self.chunks = ChunkManager(
            reader=self.reader, cfg=self.cfg, chunks_output_dir=chunks_output_dir
        )
        self.silence = SilenceTracker()

        # VAD confidence tracking for metrics
        self._speech_probabilities: List[float] = []

        # Model and inference components (populated by model loader)
        self._model: Any = None
        self._onnx_session: Any = None
        self._use_onnx: bool = False
        # ONNX state variables (initialized by model loader)
        self._onnx_state: Any = None
        self._onnx_h: Any = None
        self._onnx_c: Any = None
        self._inference_engine: Optional[VADInferenceEngine] = None

        # Audio preprocessing
        self._preprocessor = AudioPreprocessor(
            target_sample_rate=self.cfg.target_sample_rate, gain=3.0
        )

        # Throttled loggers for different events
        self._loggers = {
            "audio_read": ThrottledLogger(5.0),
            "unsupported_sr": ThrottledLogger(10.0),
            "waveform_too_small": ThrottledLogger(5.0),
            "model_error": ThrottledLogger(10.0),
            "processing_stats": ThrottledLogger(5.0),
            "no_frames": ThrottledLogger(5.0),
        }

        # Load model using the model loader
        SileroModelLoader.load_model(self)

        # Initialize inference engine after model is loaded
        if self.available:
            self._inference_engine = VADInferenceEngine(
                model=self._model,
                onnx_session=self._onnx_session,
                use_onnx=self._use_onnx,
            )
            # Transfer ONNX states from instance to inference engine
            if self._use_onnx and self._inference_engine:
                self._inference_engine._onnx_state = self._onnx_state
                self._inference_engine._onnx_h = self._onnx_h
                self._inference_engine._onnx_c = self._onnx_c

    def get_vad_confidence(self) -> Optional[float]:
        """Calculate average VAD confidence from speech frame probabilities.

        Returns average probability across all speech frames, or None if no
        speech detected.
        """
        if not self._speech_probabilities:
            return None
        avg_confidence = sum(self._speech_probabilities) / len(
            self._speech_probabilities
        )
        return round(avg_confidence, 3)

    def process_new_audio(self, monotonic_time_fn: Callable[[], float]) -> None:
        """Process newly appended audio and update last speech time.

        Args:
            monotonic_time_fn: Callable returning a monotonic time base.
        """
        if not self.available or self._inference_engine is None:
            return

        # Read new audio frames
        chunk, input_sr = self.reader.read_new_frames()
        if chunk is None or input_sr is None or chunk.size == 0:
            return

        # Log audio read (throttled)
        self._loggers["audio_read"].log_if_ready(
            lambda: log_audio_read(len(chunk), input_sr)
        )

        # Preprocess audio (convert to tensor, apply gain, resample)
        waveform, actual_sr = self._preprocessor.preprocess(chunk, input_sr)
        if waveform is None or actual_sr is None:
            return

        # Validate sample rate and get window size
        window = AudioPreprocessor.get_window_size(actual_sr)
        if window is None:
            self._loggers["unsupported_sr"].log_if_ready(
                lambda: log_unsupported_sample_rate(actual_sr)
            )
            return

        # Validate waveform size
        if waveform.shape[1] < window:
            self._loggers["waveform_too_small"].log_if_ready(
                lambda: log_waveform_too_small(waveform.shape[1], window, actual_sr)
            )
            return

        # Process frames
        self._process_frames(
            waveform, window, actual_sr, input_sr, len(chunk), monotonic_time_fn
        )

    def _process_frames(
        self,
        waveform: Any,
        window: int,
        actual_sr: int,
        input_sr: int,
        chunk_length: int,
        monotonic_time_fn: Callable[[], float],
    ) -> None:
        """Process audio frames through VAD model.

        Args:
            waveform: Preprocessed audio tensor.
            window: Window size in samples.
            actual_sr: Actual sample rate after resampling.
            input_sr: Original input sample rate.
            chunk_length: Length of original audio chunk.
            monotonic_time_fn: Function to get current monotonic time.
        """
        if _torch is None or self._inference_engine is None:
            return

        # Calculate sample rate ratio for mapping indices
        sample_rate_ratio = input_sr / actual_sr if actual_sr > 0 else 1.0

        # Calculate starting index in original WAV
        chunk_start_sample = self.reader.last_frame_idx - chunk_length
        if chunk_start_sample < 0:
            chunk_start_sample = max(0, self.reader.last_frame_idx - chunk_length)

        # Processing statistics
        frames_processed = 0
        max_prob = 0.0
        total_frames_available = waveform.shape[1] // window

        with _torch.no_grad():
            # Process in 32ms windows (non-overlapping)
            for start in range(0, waveform.shape[1] - window + 1, window):
                frame = waveform[:, start : start + window]

                # Calculate sample index in original WAV file
                resampled_sample_pos = start
                original_sample_pos = int(
                    chunk_start_sample + (resampled_sample_pos * sample_rate_ratio)
                )

                # Get current monotonic time
                current_monotonic_time = float(monotonic_time_fn())

                # Run VAD inference
                prob = self._run_inference(frame, actual_sr)
                if prob is None:
                    continue

                frames_processed += 1
                max_prob = max(max_prob, prob)

                # Track speech probabilities for confidence
                if prob >= self.cfg.threshold:
                    self._speech_probabilities.append(prob)

                # Determine if this frame contains speech
                has_speech = prob >= self.cfg.threshold

                # Don't treat bot's own playback as caller speech
                bot_playback_active = getattr(
                    self.silence, "_bot_playback_active", False
                )
                effective_has_speech = has_speech and not bot_playback_active

                # Update chunk boundaries
                self._update_chunk_boundaries(
                    current_monotonic_time, original_sample_pos, effective_has_speech
                )

                # Update speech time and silence tracking
                self._update_speech_tracking(
                    current_monotonic_time,
                    original_sample_pos,
                    effective_has_speech,
                    prob,
                )

        # Log processing statistics
        self._log_processing_stats(frames_processed, total_frames_available, max_prob)

    def _run_inference(self, frame: Any, sample_rate: int) -> Optional[float]:
        """Run VAD inference on a single frame.

        Args:
            frame: Audio frame tensor.
            sample_rate: Sample rate in Hz.

        Returns:
            Speech probability or None on error.
        """
        if self._inference_engine is None:
            return None

        try:
            return self._inference_engine.infer(frame, sample_rate)
        except Exception as e:
            error_msg = str(e)
            self._loggers["model_error"].log_if_ready(
                lambda: log_model_call_error(error_msg)
            )
            return None

    def _update_chunk_boundaries(
        self,
        monotonic_time: float,
        current_sample_idx: int,
        has_speech: bool,
    ) -> None:
        """Update chunk boundaries based on speech detection.

        Args:
            monotonic_time: Current monotonic time.
            current_sample_idx: Current sample index in WAV file.
            has_speech: Whether speech was detected in this frame.
        """
        if has_speech:
            if self.chunks.get_current_chunk() is None:
                self.chunks.start_new_chunk(monotonic_time, current_sample_idx)
            else:
                self.chunks.mark_speech_at(current_sample_idx)
        else:
            self.chunks.note_possible_silence(monotonic_time)
            self.chunks.try_finalize_on_silence(monotonic_time)

        # Check for max duration split
        if self.chunks.get_current_chunk() is not None:
            exceeded = self.chunks.try_finalize_on_max_duration(monotonic_time)
            if exceeded:
                log_chunk_split_due_to_max_duration(self.cfg.max_chunk_duration_sec)
                if has_speech:
                    self.chunks.start_new_chunk(monotonic_time, current_sample_idx)

    def _update_speech_tracking(
        self,
        monotonic_time: float,
        sample_idx: int,
        has_speech: bool,
        prob: float,
    ) -> None:
        """Update speech time tracking and silence detection.

        Args:
            monotonic_time: Current monotonic time.
            sample_idx: Current sample index.
            has_speech: Whether speech was detected.
            prob: Speech probability.
        """
        if has_speech:
            # Speech detected from caller
            self.silence.note_non_silence(monotonic_time)
            prev_time = self.last_speech_time_monotonic
            self.last_speech_time_monotonic = monotonic_time

            # Log speech detection (avoid spam on continuous speech)
            if prev_time is None or (self.last_speech_time_monotonic - prev_time) > 0.5:
                log_speech_detected(prob, self.last_speech_time_monotonic, sample_idx)
        else:
            # Possibly a silence period
            self.silence.note_possible_silence(monotonic_time)

    def _log_processing_stats(
        self, frames_processed: int, total_frames: int, max_prob: float
    ) -> None:
        """Log processing statistics (throttled).

        Args:
            frames_processed: Number of frames processed.
            total_frames: Total frames available.
            max_prob: Maximum probability seen.
        """
        if frames_processed > 0:
            self._loggers["processing_stats"].log_if_ready(
                lambda: log_processing_stats(
                    frames_processed, total_frames, max_prob, self.cfg.threshold
                )
            )
        elif total_frames > 0:
            self._loggers["no_frames"].log_if_ready(
                lambda: log_no_frames_processed(total_frames)
            )

    # ---- Delegating public helpers to smaller modules ----
    def get_chunks(self) -> List[VoiceChunk]:
        """Get all finalized voice chunks."""
        return self.chunks.get_chunks()

    def get_speech_duration(self) -> float:
        """Get total speech duration across all chunks."""
        return self.chunks.get_speech_duration()

    def get_chunk_count(self) -> int:
        """Get total number of chunks (including current)."""
        return self.chunks.get_chunk_count()

    def get_current_chunk(self) -> Optional[VoiceChunk]:
        """Get current in-progress chunk, if any."""
        return self.chunks.get_current_chunk()

    def finalize_all_chunks(self, monotonic_time_fn: Callable[[], float]) -> None:
        """Finalize all chunks, including the current one."""
        self.chunks.finalize_all_chunks(float(monotonic_time_fn()))

    def set_bot_playback_state(
        self, is_playing: bool, monotonic_time_fn: Callable[[], float]
    ) -> None:
        """Set bot playback state for silence tracking."""
        self.silence.set_bot_playback_state(is_playing, monotonic_time_fn)

    def get_silence_duration(self, monotonic_time_fn: Callable[[], float]) -> float:
        """Get total silence duration."""
        return self.silence.get_silence_duration(monotonic_time_fn)

    def get_bot_playback_duration(
        self, monotonic_time_fn: Callable[[], float]
    ) -> float:
        """Get total duration that bot has been playing audio."""
        return self.silence.get_bot_playback_duration(monotonic_time_fn)

    def finalize_silence_tracking(self, monotonic_time_fn: Callable[[], float]) -> None:
        """Finalize silence tracking."""
        self.silence.finalize(monotonic_time_fn)
