"""Silero VAD integration utilities.

This module provides a thin wrapper around Silero VAD for incremental
processing of growing WAV recordings. It is designed to be called
periodically from the event pump to detect the last time speech was
observed from the caller.
"""

from __future__ import annotations

import os
import wave
from typing import Any, Callable, List, Optional, Tuple, cast

import numpy as np

from .audio_reader import StreamingWavReader
from .chunk_manager import ChunkManager
from .config import VADConfig
from .silence import SilenceTracker
from .types import VoiceChunk

try:
    import torch
    import torchaudio

    _TORCH_AVAILABLE = True
    _TORCH_ERROR = None
except ImportError as e:  # pragma: no cover - optional dependency at runtime
    torch = None
    torchaudio = None
    _TORCH_AVAILABLE = False
    _TORCH_ERROR = str(e)
except Exception as e:
    torch = None
    torchaudio = None
    _TORCH_AVAILABLE = False
    _TORCH_ERROR = str(e)


class SileroVAD:
    """Incremental VAD over a growing WAV file recorded by PJSUA2.

    Usage:
    - Create once per call using the path to the incoming recording WAV file
    - Call `process_new_audio()` periodically; it will read appended frames only
    - Check `last_speech_time_monotonic` to decide on hangup timing
    """

    def __init__(
        self,
        wav_path: str,
        config: Optional[VADConfig] = None,
        chunks_output_dir: Optional[str] = None,
    ):
        self.wav_path = wav_path
        self.cfg = config or VADConfig()
        self._model: Any = None
        self._resampler = None
        self.last_speech_time_monotonic: Optional[float] = None
        self.available: bool = False
        self._load_error: Optional[str] = None

        # New modular components
        self.reader = StreamingWavReader(wav_path)
        self.chunks = ChunkManager(
            reader=self.reader, cfg=self.cfg, chunks_output_dir=chunks_output_dir
        )
        self.silence = SilenceTracker()

        # VAD confidence tracking for metrics
        self._speech_probabilities: List[float] = []

        # Legacy/read-path attributes kept for compatibility with internal readers
        self._wav_sample_rate: Optional[int] = None
        self._last_frame_idx: int = 0
        self._manual_wav_info: Optional[
            Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]
        ] = None

        self._load_model_if_possible()

    def _load_model_if_possible(self) -> None:
        if torch is None:
            self._load_error = (
                f"torch/torchaudio not available: {_TORCH_ERROR or 'import failed'}"
            )
            return
        try:
            model_result = torch.hub.load(
                "snakers4/silero-vad", "silero_vad", force_reload=False, onnx=False
            )
            # Handle both: model may be returned directly or as (model, utils)
            if isinstance(model_result, tuple):
                self._model = model_result[0]  # Extract model from tuple
            else:
                self._model = model_result
            assert self._model is not None
            self._model.eval()
            self.available = True
            self._load_error = None
        except Exception as e:
            # leave unavailable; caller will skip VAD
            self._model = None
            self.available = False
            self._load_error = f"model loading failed: {str(e)}"

    def _ensure_resampler(self, input_sr: int) -> Optional[Any]:
        if torch is None or torchaudio is None:
            return None
        if self._resampler is None and input_sr != self.cfg.target_sample_rate:
            self._resampler = torchaudio.transforms.Resample(
                orig_freq=input_sr,
                new_freq=self.cfg.target_sample_rate,
            )
        return self._resampler

    def _is_wav_ready(self) -> bool:
        """Check if the WAV file is ready (has valid headers and can be opened).

        WAV files need at least 44 bytes for headers, and should start with 'RIFF'.
        We also try to actually open it with wave.open() to ensure it's truly ready.
        """
        if not os.path.exists(self.wav_path):
            return False

        # Check file size - WAV headers are at least 44 bytes
        try:
            size = os.path.getsize(self.wav_path)
            if size < 44:
                return False

            # Check if it starts with RIFF (WAV file signature)
            with open(self.wav_path, "rb") as f:
                header = f.read(12)
                if len(header) < 12 or not header.startswith(b"RIFF"):
                    return False
                # Check for 'WAVE' after RIFF
                if header[8:12] != b"WAVE":
                    return False

            # Try wave.open() to verify readability.
            # For streaming files, wave.open() might fail initially even with
            # valid headers, so if RIFF/WAVE and data exist, try reading anyway.
            try:
                with wave.open(self.wav_path, "rb") as test_wf:
                    # Try to read the header info
                    test_wf.getnchannels()
                    test_wf.getframerate()
                    test_wf.getnframes()
                # Success! Cache that it's ready
                self._file_was_ready = True
                return True
            except (wave.Error, Exception):
                # File has RIFF header but wave.open() fails
                # For streaming files being written by PJSUA2, this might be normal
                # If file is large enough (has data), we'll try reading it anyway
                # The actual read will handle errors gracefully
                if size > 1000:  # File has substantial data (more than just header)
                    # Cache that we've seen it ready once to avoid repeated checks
                    if not hasattr(self, "_file_was_ready"):
                        self._file_was_ready = False
                    return True  # Try reading; errors handled in _read_new_frames
                return False
        except Exception:
            return False

        return False

    def _parse_wav_header(
        self,
    ) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """Manually parse WAV header and return basic format info.

        Returns (n_channels, sampwidth, framerate, data_offset) or
        (None, None, None, None) on error.
        """
        try:
            with open(self.wav_path, "rb") as f:
                # Read RIFF header
                riff = f.read(4)
                if riff != b"RIFF":
                    return None, None, None, None

                # Skip file size (4 bytes)
                f.read(4)

                # Read WAVE header
                wave_hdr = f.read(4)
                if wave_hdr != b"WAVE":
                    return None, None, None, None

                # Find 'fmt ' chunk
                fmt_found = False
                while True:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        return None, None, None, None

                    chunk_size = int.from_bytes(f.read(4), "little")

                    if chunk_id == b"fmt ":
                        fmt_found = True
                        # Read fmt chunk data (discard audio_format)
                        f.read(2)
                        n_channels = int.from_bytes(f.read(2), "little")
                        framerate = int.from_bytes(f.read(4), "little")
                        f.read(4)  # byte_rate
                        f.read(2)  # block_align
                        bits_per_sample = int.from_bytes(f.read(2), "little")
                        # Convert bits to bytes (Python's wave module uses bytes)
                        sampwidth = bits_per_sample // 8

                        # Skip any remaining fmt chunk data
                        if chunk_size > 16:
                            f.read(chunk_size - 16)
                        break
                    else:
                        # Skip this chunk
                        f.read(chunk_size)

                if not fmt_found:
                    return None, None, None, None

                # Find 'data' chunk
                data_offset = None
                while True:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        break

                    chunk_size = int.from_bytes(f.read(4), "little")

                    if chunk_id == b"data":
                        data_offset = f.tell()
                        break
                    else:
                        # Skip this chunk
                        f.read(chunk_size)

                if data_offset is None:
                    return None, None, None, None

                return n_channels, sampwidth, framerate, data_offset

        except Exception:
            return None, None, None, None

    def _read_new_frames(self) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Read newly appended PCM frames from the WAV file.

        Returns (float32_pcm, input_sample_rate). PCM is mono float32 in [-1, 1].
        Returns (None, None) if no new data available or file isn't ready yet.
        """
        if not os.path.exists(self.wav_path):
            return None, None

        # Wait for WAV file to be ready (headers complete)
        if not self._is_wav_ready():
            # Debug: report that we're waiting for file to be ready
            if not hasattr(self, "_last_wait_time"):
                self._last_wait_time = 0.0
            import time as time_module

            if time_module.time() - self._last_wait_time > 3.0:
                try:
                    size = os.path.getsize(self.wav_path)
                    print(
                        f"***VAD: waiting for WAV file to be ready (size={size} bytes)"
                    )
                except Exception:
                    print("***VAD: waiting for WAV file to be ready")
                self._last_wait_time = time_module.time()
            return None, None

        # Try to use wave.open() first, but fall back to manual parsing if it fails
        try:
            with wave.open(self.wav_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()

                if self._wav_sample_rate is None:
                    self._wav_sample_rate = framerate
                    # Debug: print file info on first read
                    import time as time_module

                    print(
                        (
                            f"***VAD: WAV file opened - {n_channels}ch, "
                            f"{sampwidth}byte/sample, {framerate}Hz, {n_frames} frames"
                        )
                    )

                if n_frames <= self._last_frame_idx:
                    # Debug: occasionally report that we're waiting for new data
                    if not hasattr(self, "_last_no_data_time"):
                        self._last_no_data_time = 0.0
                    import time as time_module

                    if time_module.time() - self._last_no_data_time > 5.0:
                        print(
                            (
                                f"***VAD: waiting for new audio "
                                f"(last_idx={self._last_frame_idx}, total={n_frames})"
                            )
                        )
                    self._last_no_data_time = time_module.time()
                    return None, None

                wf.setpos(self._last_frame_idx)
                frames_to_read = n_frames - self._last_frame_idx
                raw = wf.readframes(frames_to_read)
                self._last_frame_idx = n_frames

        except (wave.Error, Exception):
            # wave.open() failed - try manual parsing for streaming WAV files
            # Cache the parsed info to avoid re-parsing every time
            if self._manual_wav_info is None:
                self._manual_wav_info = self._parse_wav_header()

            if self._manual_wav_info is None or any(
                x is None for x in self._manual_wav_info
            ):
                # Can't parse header - wait for file to be ready
                if not hasattr(self, "_last_error_time"):
                    self._last_error_time = 0.0
                import time as time_module

                if time_module.time() - self._last_error_time > 10.0:
                    print(
                        (
                            "***VAD: WAV read error - cannot parse WAV header "
                            "(trying manual parsing)"
                        )
                    )
                    self._last_error_time = time_module.time()
                return None, None

            n_channels, sampwidth, framerate, data_offset = cast(
                Tuple[int, int, int, int], self._manual_wav_info
            )

            # Initialize on first read
            if self._wav_sample_rate is None:
                self._wav_sample_rate = framerate
                import time as time_module

                # Fix display - sampwidth is in bytes, but output was confusing
                print(
                    (
                        f"***VAD: WAV file parsed manually - {n_channels}ch, "
                        f"{sampwidth * 8}bit/sample, {framerate}Hz"
                    )
                )

            # Read new frames manually
            try:
                with open(self.wav_path, "rb") as f:
                    bytes_per_frame = n_channels * sampwidth
                    current_data_pos = data_offset + (
                        self._last_frame_idx * bytes_per_frame
                    )

                    # Calculate how much data is available
                    file_size = os.path.getsize(self.wav_path)
                    available_bytes = file_size - current_data_pos

                    # Debug occasionally
                    if not hasattr(self, "_last_debug_time"):
                        self._last_debug_time = 0.0
                    import time as time_module

                    if time_module.time() - self._last_debug_time > 5.0:
                        print(
                            (
                                f"***VAD: manual read - file_size={file_size}, "
                                f"data_offset={data_offset}, "
                                f"current_pos={current_data_pos}, "
                                f"available={available_bytes}, "
                                f"bytes_per_frame={bytes_per_frame}, "
                                f"last_idx={self._last_frame_idx}"
                            )
                        )
                        self._last_debug_time = time_module.time()

                    if available_bytes < bytes_per_frame:
                        # No new frames available
                        if not hasattr(self, "_last_no_data_time"):
                            self._last_no_data_time = 0.0
                        import time as time_module

                        if time_module.time() - self._last_no_data_time > 5.0:
                            print("***VAD: waiting for new audio (manual read)")
                            self._last_no_data_time = time_module.time()
                        return None, None

                    # Seek to current position and read
                    f.seek(current_data_pos)
                    raw = f.read(available_bytes)
                    frames_read = len(raw) // bytes_per_frame
                    self._last_frame_idx += frames_read

                    # Debug: report occasionally when we read frames (reduce spam)
                    if frames_read > 0:
                        if not hasattr(self, "_last_read_report_time"):
                            self._last_read_report_time = 0.0
                        import time as time_module

                        if time_module.time() - self._last_read_report_time > 5.0:
                            print(
                                (
                                    f"***VAD: read {frames_read} frames "
                                    f"({len(raw)} bytes) manually "
                                    f"(total_idx={self._last_frame_idx})"
                                )
                            )
                            self._last_read_report_time = time_module.time()

            except Exception as e:
                # Error reading manually
                if not hasattr(self, "_last_error_time"):
                    self._last_error_time = 0.0
                import time as time_module

                if time_module.time() - self._last_error_time > 10.0:
                    print(f"***VAD: manual read error: {e}")
                    self._last_error_time = time_module.time()
                return None, None

        if not raw:
            return None, None

        # Convert raw bytes to mono float32
        dtype = {1: np.int8, 2: np.int16, 3: None, 4: np.int32}.get(sampwidth)
        if dtype is None:
            # 24-bit not handled; skip
            return None, None
        pcm = np.frombuffer(raw, dtype=dtype)
        if n_channels > 1:
            pcm = pcm.reshape(-1, n_channels).mean(axis=1)
        # normalize to float32 -1..1
        max_val = float(np.iinfo(dtype).max)
        pcm_f32 = (pcm.astype(np.float32) / max_val).clip(-1.0, 1.0)
        return pcm_f32, framerate

    def _start_new_chunk(self, monotonic_time: float, start_sample_idx: int) -> None:
        # Delegated to ChunkManager; keeping method removed to avoid duplicate state
        raise NotImplementedError("use ChunkManager.start_new_chunk")

    def _check_chunk_boundaries(
        self,
        monotonic_time: float,
        current_sample_idx: int,
        has_speech: bool,
    ) -> None:
        """Boundary handling using ChunkManager state machine."""
        if has_speech:
            if self.chunks.get_current_chunk() is None:
                self.chunks.start_new_chunk(monotonic_time, current_sample_idx)
            else:
                self.chunks.mark_speech_at(current_sample_idx)
        else:
            self.chunks.note_possible_silence(monotonic_time)
            self.chunks.try_finalize_on_silence(monotonic_time)

        if self.chunks.get_current_chunk() is not None:
            exceeded = self.chunks.try_finalize_on_max_duration(monotonic_time)
            if exceeded:
                print(
                    (
                        "***VAD: chunk split due to max duration ("
                        f"{self.cfg.max_chunk_duration_sec}s)"
                    )
                )
                if has_speech:
                    self.chunks.start_new_chunk(monotonic_time, current_sample_idx)

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

    # Removed stub for set_bot_playback_state; use delegated method below

    def process_new_audio(self, monotonic_time_fn: Callable[[], float]) -> None:
        """Process newly appended audio and update last speech time.

        monotonic_time_fn: callable returning a monotonic time base (e.g., time.time())
        """
        if not self.available or self._model is None:
            return

        chunk, input_sr = self.reader.read_new_frames()
        if chunk is None or input_sr is None or chunk.size == 0:
            return

        # Debug: check if we're getting audio
        if not hasattr(self, "_last_audio_check_time"):
            self._last_audio_check_time = 0.0
        import time as time_module

        if time_module.time() - self._last_audio_check_time > 5.0:
            print(f"***VAD: read {len(chunk)} samples at {input_sr} Hz")
            self._last_audio_check_time = time_module.time()

        # Convert to torch and resample if needed
        if torch is None:
            return
        waveform = torch.from_numpy(chunk).unsqueeze(0)  # (1, N)

        # Determine the actual sample rate to use with the model
        # Silero VAD supports 8000 and 16000 Hz
        actual_sr = input_sr

        # Resample to target sample rate if needed
        if input_sr != self.cfg.target_sample_rate:
            if torchaudio is None:
                # Can't resample - use original sample rate if supported
                # (8000 or 16000)
                if input_sr not in (8000, 16000):
                    # Skip this chunk if sample rate isn't supported
                    if not hasattr(self, "_last_unsupported_sr_time"):
                        self._last_unsupported_sr_time = 0.0
                    import time as time_module
            if time_module.time() - self._last_unsupported_sr_time > 10.0:
                print(
                    (
                        f"***VAD: cannot resample from {input_sr}Hz "
                        "(not 8kHz/16kHz and torchaudio unavailable)"
                    )
                )
                self._last_unsupported_sr_time = time_module.time()
                return
                # Use original sample rate if it's supported
                actual_sr = input_sr
            else:
                resampler = self._ensure_resampler(input_sr)
                if resampler is None:
                    # Resampler creation failed - use original if supported
                    if input_sr in (8000, 16000):
                        actual_sr = input_sr
                    else:
                        return
                else:
                    with torch.no_grad():
                        waveform = resampler(waveform)
                    actual_sr = self.cfg.target_sample_rate

        # Frame-wise VAD - Silero VAD requires exactly 32ms windows:
        # - 256 samples for 8000 Hz (256/8000 = 32ms)
        # - 512 samples for 16000 Hz (512/16000 = 32ms)
        if actual_sr == 8000:
            window = 256
        elif actual_sr == 16000:
            window = 512
        else:
            # Unsupported sample rate
            if not hasattr(self, "_last_unsupported_sr_time"):
                self._last_unsupported_sr_time = 0.0
            import time as time_module

            if time_module.time() - self._last_unsupported_sr_time > 10.0:
                print(
                    (
                        f"***VAD: unsupported sample rate {actual_sr}Hz "
                        "(must be 8000 or 16000)"
                    )
                )
                self._last_unsupported_sr_time = time_module.time()
            return

        # Debug: check waveform size
        if waveform.shape[1] < window:
            # Debug: report if waveform is too small
            if not hasattr(self, "_last_small_waveform_time"):
                self._last_small_waveform_time = 0.0
            import time as time_module

            if time_module.time() - self._last_small_waveform_time > 5.0:
                print(
                    (
                        f"***VAD: waveform too small ({waveform.shape[1]} samples, "
                        f"need {window} for {actual_sr}Hz)"
                    )
                )
                self._last_small_waveform_time = time_module.time()
            return

        # Debug: track processing stats
        frames_processed = 0
        max_prob = 0.0
        total_frames_available = (waveform.shape[1] - window + 1) // window

        # Calculate sample rate ratio to map resampled indices back to original WAV
        sample_rate_ratio = input_sr / actual_sr if actual_sr > 0 else 1.0

        # Calculate starting index in original WAV for this chunk
        # After read_new_frames(), last_frame_idx points to end of what we read
        chunk_start_sample = self.reader.last_frame_idx - len(chunk)

        # Validate chunk_start_sample is non-negative
        if chunk_start_sample < 0:
            # This shouldn't happen, but handle gracefully
            chunk_start_sample = max(0, self.reader.last_frame_idx - len(chunk))

        monotonic_time_fn_ref = monotonic_time_fn

        with torch.no_grad():
            # Process in 32ms windows (non-overlapping for now)
            for _window_idx, start in enumerate(
                range(0, waveform.shape[1] - window + 1, window)
            ):
                frame = waveform[:, start : start + window]

                # Calculate sample index in original WAV file
                # Map from resampled waveform position to original WAV position
                resampled_sample_pos = start
                original_sample_pos = int(
                    chunk_start_sample + (resampled_sample_pos * sample_rate_ratio)
                )

                # Get current monotonic time for chunk boundary detection
                current_monotonic_time = float(monotonic_time_fn_ref())

                # Silero VAD requires: model(waveform_tensor, sample_rate_int)
                has_speech = False
                try:
                    # Use the actual sample rate of the waveform
                    sample_rate = int(actual_sr)
                    prob = self._model(frame, sample_rate).item()
                except Exception as e:
                    # Report error only occasionally to avoid spam
                    if not hasattr(self, "_last_model_error_time"):
                        self._last_model_error_time = 0.0
                    import time as time_module

                    if time_module.time() - self._last_model_error_time > 10.0:
                        print(f"***VAD: model call error: {e}")
                        self._last_model_error_time = time_module.time()
                    # Continue processing other frames even if one fails
                    # For chunk detection, treat error frames as non-speech
                    prob = 0.0

                frames_processed += 1
                max_prob = max(max_prob, prob)

                # Track speech probabilities for confidence calculation
                if prob >= self.cfg.threshold:
                    self._speech_probabilities.append(prob)

                # Check if this frame contains speech
                has_speech = prob >= self.cfg.threshold

                # Update chunk boundaries based on speech detection
                self._check_chunk_boundaries(
                    monotonic_time=current_monotonic_time,
                    current_sample_idx=original_sample_pos,
                    has_speech=has_speech,
                )

                # Track silence periods (when neither caller nor bot are speaking)
                if has_speech:
                    # Speech detected - end any current silence period
                    self.silence.note_non_silence(current_monotonic_time)
                    prev_time = self.last_speech_time_monotonic
                    self.last_speech_time_monotonic = current_monotonic_time
                    # Print when speech is first detected or after a gap
                    # (avoid spam on continuous speech)
                    if (
                        prev_time is None
                        or (self.last_speech_time_monotonic - prev_time) > 0.5
                    ):
                        print(
                            (
                                f"***VAD: speech detected (prob={prob:.3f}, "
                                f"time={self.last_speech_time_monotonic:.3f}, "
                                f"sample={original_sample_pos})"
                            )
                        )
                else:
                    # Possibly a silence period depending on bot playback state
                    self.silence.note_possible_silence(current_monotonic_time)

        # Debug output: print max probability occasionally to diagnose issues
        if frames_processed > 0:
            # Only print debug every few seconds to avoid spam
            import time as time_module

            if (
                not hasattr(self, "_last_debug_time")
                or time_module.time() - getattr(self, "_last_debug_time", 0) > 5.0
            ):
                print(
                    (
                        f"***VAD: processed {frames_processed}/"
                        f"{total_frames_available} "
                        f"frames, max_prob={max_prob:.3f} "
                        f"(threshold={self.cfg.threshold:.3f})"
                    )
                )
                self._last_debug_time = time_module.time()
        elif total_frames_available > 0:
            # No frames processed but frames available - something went wrong
            import time as time_module

            if not hasattr(self, "_last_no_proc_time"):
                self._last_no_proc_time = 0.0
            if time_module.time() - self._last_no_proc_time > 5.0:
                print(
                    (
                        f"***VAD: {total_frames_available} frames available but none "
                        "processed (check model errors)"
                    )
                )
                self._last_no_proc_time = time_module.time()

    # ---- Delegating public helpers to smaller modules ----
    def get_chunks(self) -> List[VoiceChunk]:
        return self.chunks.get_chunks()

    def get_speech_duration(self) -> float:
        return self.chunks.get_speech_duration()

    def get_chunk_count(self) -> int:
        return self.chunks.get_chunk_count()

    def get_current_chunk(self) -> Optional[VoiceChunk]:
        return self.chunks.get_current_chunk()

    def finalize_all_chunks(self, monotonic_time_fn: Callable[[], float]) -> None:
        self.chunks.finalize_all_chunks(float(monotonic_time_fn()))

    def set_bot_playback_state(
        self, is_playing: bool, monotonic_time_fn: Callable[[], float]
    ) -> None:
        self.silence.set_bot_playback_state(is_playing, monotonic_time_fn)

    def get_silence_duration(self, monotonic_time_fn: Callable[[], float]) -> float:
        return self.silence.get_silence_duration(monotonic_time_fn)

    def finalize_silence_tracking(self, monotonic_time_fn: Callable[[], float]) -> None:
        self.silence.finalize(monotonic_time_fn)
