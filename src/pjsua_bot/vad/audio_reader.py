from __future__ import annotations

import os
import wave
from typing import Optional, Tuple, cast

import numpy as np


class StreamingWavReader:
    """Utility to incrementally read a growing WAV file.

    Maintains internal cursors so repeated calls only return newly appended
    frames. Designed for files being appended by an external process.
    """

    def __init__(self, wav_path: str):
        self.wav_path = wav_path
        self._last_frame_idx: int = 0
        self._wav_sample_rate: Optional[int] = None
        self._manual_wav_info: Optional[
            Tuple[Optional[int], Optional[int], Optional[int], Optional[int]
        ]] = None  # (channels, sampwidth, framerate, data_offset)
        self._file_was_ready: bool = False

    # Expose read-only properties needed by orchestrator/managers
    @property
    def last_frame_idx(self) -> int:
        return self._last_frame_idx

    @property
    def wav_sample_rate(self) -> Optional[int]:
        return self._wav_sample_rate

    @property
    def manual_wav_info(
        self,
    ) -> Optional[Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]]:
        return self._manual_wav_info

    def _is_wav_ready(self) -> bool:
        if not os.path.exists(self.wav_path):
            return False

        try:
            size = os.path.getsize(self.wav_path)
            if size < 44:
                return False

            with open(self.wav_path, 'rb') as f:
                header = f.read(12)
                if len(header) < 12 or not header.startswith(b'RIFF'):
                    return False
                if header[8:12] != b'WAVE':
                    return False

            try:
                with wave.open(self.wav_path, 'rb') as test_wf:
                    test_wf.getnchannels()
                    test_wf.getframerate()
                    test_wf.getnframes()
                self._file_was_ready = True
                return True
            except (wave.Error, Exception):
                if size > 1000:
                    if not hasattr(self, '_file_was_ready'):
                        self._file_was_ready = False
                    return True
                return False
        except Exception:
            return False

    def _parse_wav_header(self) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        try:
            with open(self.wav_path, 'rb') as f:
                if f.read(4) != b'RIFF':
                    return None, None, None, None
                f.read(4)  # file size
                if f.read(4) != b'WAVE':
                    return None, None, None, None

                fmt_found = False
                while True:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        return None, None, None, None
                    chunk_size = int.from_bytes(f.read(4), 'little')
                    if chunk_id == b'fmt ':
                        fmt_found = True
                        audio_format = int.from_bytes(f.read(2), 'little')  # noqa: F841
                        n_channels = int.from_bytes(f.read(2), 'little')
                        framerate = int.from_bytes(f.read(4), 'little')
                        f.read(4)  # byte_rate
                        f.read(2)  # block_align
                        bits_per_sample = int.from_bytes(f.read(2), 'little')
                        sampwidth = bits_per_sample // 8
                        if chunk_size > 16:
                            f.read(chunk_size - 16)
                        break
                    else:
                        f.read(chunk_size)

                if not fmt_found:
                    return None, None, None, None

                data_offset = None
                while True:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        break
                    chunk_size = int.from_bytes(f.read(4), 'little')
                    if chunk_id == b'data':
                        data_offset = f.tell()
                        break
                    else:
                        f.read(chunk_size)

                if data_offset is None:
                    return None, None, None, None

                return n_channels, sampwidth, framerate, data_offset
        except Exception:
            return None, None, None, None

    def read_new_frames(self) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Return mono float32 PCM and input sample rate for newly appended audio."""
        if not os.path.exists(self.wav_path):
            return None, None

        if not self._is_wav_ready():
            try:
                size = os.path.getsize(self.wav_path)
                print(f"***VAD: waiting for WAV file to be ready (size={size} bytes)")
            except Exception:
                print("***VAD: waiting for WAV file to be ready")
            return None, None

        # Predeclare variables for type-checker across try/except branches
        n_channels: Optional[int] = None
        sampwidth: Optional[int] = None
        framerate: Optional[int] = None
        raw: Optional[bytes] = None
        try:
            with wave.open(self.wav_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()

                if self._wav_sample_rate is None:
                    self._wav_sample_rate = framerate
                    import time as time_module
                    print(
                        f"***VAD: WAV file opened - {n_channels}ch, {sampwidth}byte/sample, {framerate}Hz, {n_frames} frames"
                    )

                if n_frames <= self._last_frame_idx:
                    # Throttle this log to avoid flooding the console
                    if not hasattr(self, '_last_no_data_time'):
                        self._last_no_data_time = 0.0
                    import time as time_module
                    if time_module.time() - self._last_no_data_time > 5.0:
                        print(
                            f"***VAD: waiting for new audio (last_idx={self._last_frame_idx}, total={n_frames})"
                        )
                        self._last_no_data_time = time_module.time()
                    return None, None

                wf.setpos(self._last_frame_idx)
                frames_to_read = n_frames - self._last_frame_idx
                raw = wf.readframes(frames_to_read)
                self._last_frame_idx = n_frames
        except (wave.Error, Exception):
            if self._manual_wav_info is None:
                self._manual_wav_info = self._parse_wav_header()

            if self._manual_wav_info is None or any(x is None for x in self._manual_wav_info):
                print("***VAD: WAV read error - cannot parse WAV header (trying manual parsing)")
                return None, None

            n_channels, sampwidth, framerate, data_offset = cast(
                Tuple[int, int, int, int], self._manual_wav_info
            )

            if self._wav_sample_rate is None:
                self._wav_sample_rate = framerate
                print(
                    f"***VAD: WAV file parsed manually - {n_channels}ch, {sampwidth*8}bit/sample, {framerate}Hz"
                )

            try:
                with open(self.wav_path, 'rb') as f:
                    bytes_per_frame = n_channels * sampwidth
                    current_data_pos = data_offset + (self._last_frame_idx * bytes_per_frame)
                    file_size = os.path.getsize(self.wav_path)
                    available_bytes = file_size - current_data_pos

                    if available_bytes < bytes_per_frame:
                        # Throttle manual-read wait logs
                        if not hasattr(self, '_last_manual_wait_time'):
                            self._last_manual_wait_time = 0.0
                        import time as time_module
                        if time_module.time() - self._last_manual_wait_time > 5.0:
                            print("***VAD: waiting for new audio (manual read)")
                            self._last_manual_wait_time = time_module.time()
                        return None, None

                    f.seek(current_data_pos)
                    raw = f.read(available_bytes)
                    frames_read = len(raw) // bytes_per_frame
                    self._last_frame_idx += frames_read
                    if frames_read > 0:
                        print(
                            f"***VAD: read {frames_read} frames ({len(raw)} bytes) manually (total_idx={self._last_frame_idx})"
                        )
            except Exception as e:
                print(f"***VAD: manual read error: {e}")
                return None, None

        if not raw:
            return None, None

        # At this point, n_channels/sampwidth/framerate are set in either branch
        assert sampwidth is not None and n_channels is not None and framerate is not None
        dtype = {1: np.int8, 2: np.int16, 3: None, 4: np.int32}.get(sampwidth)
        if dtype is None:
            return None, None
        pcm = np.frombuffer(raw, dtype=dtype)
        if n_channels > 1:
            pcm = pcm.reshape(-1, n_channels).mean(axis=1)
        max_val = float(np.iinfo(dtype).max)
        pcm_f32 = (pcm.astype(np.float32) / max_val).clip(-1.0, 1.0)
        return pcm_f32, framerate


