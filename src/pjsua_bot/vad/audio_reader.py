from __future__ import annotations

import os
import time
import wave
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class WavInfo:
    """WAV file metadata."""
    channels: int
    sampwidth: int
    framerate: int
    data_offset: int


class ManualWavParser:
    """Helper class for manually parsing WAV files when wave module fails."""

    @staticmethod
    def parse(wav_path: str) -> Optional[WavInfo]:
        """Parse WAV header manually and return metadata."""
        try:
            with open(wav_path, "rb") as f:
                if not ManualWavParser._validate_riff_header(f):
                    return None

                fmt_info = ManualWavParser._find_fmt_chunk(f)
                if fmt_info is None:
                    return None

                n_channels, sampwidth, framerate = fmt_info
                data_offset = ManualWavParser._find_data_chunk(f)

                if data_offset is None:
                    return None

                return WavInfo(n_channels, sampwidth, framerate, data_offset)
        except Exception:
            return None

    @staticmethod
    def _validate_riff_header(f) -> bool:
        """Validate RIFF WAVE header."""
        header = f.read(12)
        return (
            len(header) >= 12
            and header.startswith(b"RIFF")
            and header[8:12] == b"WAVE"
        )

    @staticmethod
    def _find_fmt_chunk(f) -> Optional[Tuple[int, int, int]]:
        """Find and parse fmt chunk."""
        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                return None

            chunk_size = int.from_bytes(f.read(4), "little")

            if chunk_id == b"fmt ":
                audio_format = int.from_bytes(f.read(2), "little")  # noqa: F841
                n_channels = int.from_bytes(f.read(2), "little")
                framerate = int.from_bytes(f.read(4), "little")
                f.read(4)  # byte_rate
                f.read(2)  # block_align
                bits_per_sample = int.from_bytes(f.read(2), "little")
                sampwidth = bits_per_sample // 8

                # Skip any extra fmt chunk data
                if chunk_size > 16:
                    f.read(chunk_size - 16)

                return n_channels, sampwidth, framerate
            else:
                f.read(chunk_size)

    @staticmethod
    def _find_data_chunk(f) -> Optional[int]:
        """Find data chunk and return its offset."""
        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                return None

            chunk_size = int.from_bytes(f.read(4), "little")

            if chunk_id == b"data":
                return f.tell()
            else:
                f.read(chunk_size)


class LogThrottle:
    """Helper for throttling log messages."""

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self._last_log_time = 0.0

    def should_log(self) -> bool:
        """Return True if enough time has passed since last log."""
        now = time.time()
        if now - self._last_log_time >= self.interval:
            self._last_log_time = now
            return True
        return False


class StreamingWavReader:
    """Utility to incrementally read a growing WAV file.

    Maintains internal cursors so repeated calls only return newly appended
    frames. Designed for files being appended by an external process.
    """

    def __init__(self, wav_path: str):
        self.wav_path = wav_path
        self._last_frame_idx: int = 0
        self._wav_sample_rate: Optional[int] = None
        self._manual_wav_info: Optional[WavInfo] = None
        self._wait_log_throttle = LogThrottle()
        self._manual_wait_log_throttle = LogThrottle()

    # Expose read-only properties needed by orchestrator/managers
    @property
    def last_frame_idx(self) -> int:
        return self._last_frame_idx

    @property
    def wav_sample_rate(self) -> Optional[int]:
        return self._wav_sample_rate

    @property
    def manual_wav_info(self) -> Optional[WavInfo]:
        return self._manual_wav_info

    def _is_wav_ready(self) -> bool:
        """Check if WAV file exists and has valid header."""
        if not os.path.exists(self.wav_path):
            return False

        try:
            size = os.path.getsize(self.wav_path)
            if size < 44:  # Minimum WAV header size
                return False

            # Quick validation of RIFF header
            with open(self.wav_path, "rb") as f:
                header = f.read(12)
                if len(header) < 12 or not header.startswith(b"RIFF"):
                    return False
                if header[8:12] != b"WAVE":
                    return False

            # Try to open with wave module
            try:
                with wave.open(self.wav_path, "rb") as test_wf:
                    test_wf.getnchannels()
                    test_wf.getframerate()
                    test_wf.getnframes()
                return True
            except (wave.Error, Exception):
                # If wave module fails but file is large enough, allow manual parsing
                return size > 1000
        except Exception:
            return False

    def read_new_frames(self) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Return mono float32 PCM and input sample rate for newly appended audio."""
        if not os.path.exists(self.wav_path):
            return None, None

        if not self._is_wav_ready():
            self._log_waiting_for_file()
            return None, None

        # Try normal wave module path first
        result = self._read_with_wave_module()
        if result is not None:
            return result

        # Fall back to manual parsing
        return self._read_with_manual_parser()

    def _log_waiting_for_file(self) -> None:
        """Log that we're waiting for WAV file to be ready."""
        if self._wait_log_throttle.should_log():
            try:
                size = os.path.getsize(self.wav_path)
                print(f"***VAD: waiting for WAV file to be ready (size={size} bytes)")
            except Exception:
                print("***VAD: waiting for WAV file to be ready")

    def _read_with_wave_module(self) -> Optional[Tuple[np.ndarray, int]]:
        """Read new frames using the wave module."""
        try:
            with wave.open(self.wav_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()

                self._initialize_sample_rate(framerate, n_channels, sampwidth, n_frames)

                if n_frames <= self._last_frame_idx:
                    self._log_waiting_for_audio(n_frames)
                    return None

                wf.setpos(self._last_frame_idx)
                frames_to_read = n_frames - self._last_frame_idx
                raw = wf.readframes(frames_to_read)
                self._last_frame_idx = n_frames

                return self._convert_to_mono_float32(raw, n_channels, sampwidth, framerate)
        except (wave.Error, Exception):
            return None

    def _read_with_manual_parser(self) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Read new frames using manual WAV parsing."""
        if self._manual_wav_info is None:
            self._manual_wav_info = ManualWavParser.parse(self.wav_path)

        if self._manual_wav_info is None:
            print("***VAD: WAV read error - cannot parse WAV header (trying manual parsing)")
            return None, None

        info = self._manual_wav_info
        self._initialize_sample_rate(info.framerate, info.channels, info.sampwidth, None)

        try:
            raw = self._read_raw_bytes_manually(info)
            if raw is None:
                return None, None

            result = self._convert_to_mono_float32(raw, info.channels, info.sampwidth, info.framerate)
            return result
        except Exception as e:
            print(f"***VAD: manual read error: {e}")
            return None, None

    def _read_raw_bytes_manually(self, info: WavInfo) -> Optional[bytes]:
        """Read raw audio bytes manually from file."""
        with open(self.wav_path, "rb") as f:
            bytes_per_frame = info.channels * info.sampwidth
            current_data_pos = info.data_offset + (self._last_frame_idx * bytes_per_frame)
            file_size = os.path.getsize(self.wav_path)
            available_bytes = file_size - current_data_pos

            if available_bytes < bytes_per_frame:
                if self._manual_wait_log_throttle.should_log():
                    print("***VAD: waiting for new audio (manual read)")
                return None

            f.seek(current_data_pos)
            raw = f.read(available_bytes)
            frames_read = len(raw) // bytes_per_frame
            self._last_frame_idx += frames_read
            return raw

    def _initialize_sample_rate(
        self, framerate: int, n_channels: int, sampwidth: int, n_frames: Optional[int]
    ) -> None:
        """Initialize and log sample rate on first read."""
        if self._wav_sample_rate is None:
            self._wav_sample_rate = framerate
            if n_frames is not None:
                print(
                    f"***VAD: WAV file opened - {n_channels}ch, "
                    f"{sampwidth}byte/sample, {framerate}Hz, {n_frames} frames"
                )
            else:
                print(
                    f"***VAD: WAV file parsed manually - {n_channels}ch, "
                    f"{sampwidth * 8}bit/sample, {framerate}Hz"
                )

    def _log_waiting_for_audio(self, n_frames: int) -> None:
        """Log that we're waiting for new audio data."""
        if self._wait_log_throttle.should_log():
            print(
                f"***VAD: waiting for new audio "
                f"(last_idx={self._last_frame_idx}, total={n_frames})"
            )

    def _convert_to_mono_float32(
        self, raw: bytes, n_channels: int, sampwidth: int, framerate: int
    ) -> Tuple[np.ndarray, int]:
        """Convert raw audio bytes to mono float32 PCM."""
        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
        dtype = dtype_map.get(sampwidth)
        if dtype is None:
            raise ValueError(f"Unsupported sample width: {sampwidth}")

        pcm = np.frombuffer(raw, dtype=dtype)
        if n_channels > 1:
            pcm = pcm.reshape(-1, n_channels).mean(axis=1)

        max_val = float(np.iinfo(dtype).max)
        pcm_f32 = (pcm.astype(np.float32) / max_val).clip(-1.0, 1.0)
        return pcm_f32, framerate
