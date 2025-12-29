from __future__ import annotations

import logging
import os
import wave
from typing import List, Optional

from ..utils import convert_wav_to_mp3
from .audio_reader import StreamingWavReader
from .config import VADConfig
from .types import VoiceChunk

logger = logging.getLogger(__name__)


class ChunkManager:
    """Manage detection state and saving of voice chunks."""

    def __init__(
        self,
        reader: StreamingWavReader,
        cfg: VADConfig,
        chunks_output_dir: Optional[str] = None,
    ) -> None:
        self.reader = reader
        self.cfg = cfg
        self._chunks_output_dir = chunks_output_dir

        # Tracking state
        self._chunks: List[VoiceChunk] = []
        self._current_chunk_start_time: Optional[float] = None
        self._current_chunk_start_sample: Optional[int] = None
        self._current_chunk_end_sample: Optional[int] = None
        self._last_speech_sample: Optional[int] = None
        self._silence_start_time: Optional[float] = None
        self._chunk_counter = 0

    # Public getters
    def get_chunks(self) -> List[VoiceChunk]:
        return self._chunks.copy()

    def get_speech_duration(self) -> float:
        total = sum(chunk.duration_seconds for chunk in self._chunks)
        current = self.get_current_chunk()
        if current:
            total += current.duration_seconds
        return round(total, 2)

    def get_chunk_count(self) -> int:
        count = len(self._chunks)
        if self._current_chunk_start_time is not None:
            count += 1
        return count

    def get_current_chunk(self) -> Optional[VoiceChunk]:
        if (
            self._current_chunk_start_time is None
            or self.reader.wav_sample_rate is None
        ):
            return None
        import time as time_module

        now = time_module.time()
        duration = now - self._current_chunk_start_time
        return VoiceChunk(
            start_time_monotonic=self._current_chunk_start_time,
            end_time_monotonic=now,
            start_sample_idx=self._current_chunk_start_sample or 0,
            end_sample_idx=self._current_chunk_end_sample or 0,
            duration_seconds=duration,
            sample_rate=self.reader.wav_sample_rate,
            file_path=None,
        )

    def finalize_all_chunks(self, monotonic_time: float) -> None:
        if self._current_chunk_start_time is None:
            return
        end_sample = (
            self._last_speech_sample
            if self._last_speech_sample is not None
            else self._current_chunk_end_sample
        )
        if end_sample is None:
            end_sample = self.reader.last_frame_idx
        self._finalize_current_chunk_internal(monotonic_time, end_sample, force=True)

    # State transitions used by orchestrator
    def start_new_chunk(self, monotonic_time: float, start_sample_idx: int) -> None:
        self._current_chunk_start_time = monotonic_time
        self._current_chunk_start_sample = start_sample_idx
        self._current_chunk_end_sample = start_sample_idx
        self._last_speech_sample = start_sample_idx
        self._silence_start_time = None

    def mark_speech_at(self, current_sample_idx: int) -> None:
        self._current_chunk_end_sample = current_sample_idx
        self._last_speech_sample = current_sample_idx

    def note_possible_silence(self, monotonic_time: float) -> None:
        if (
            self._silence_start_time is None
            and self._current_chunk_start_time is not None
        ):
            self._silence_start_time = monotonic_time

    def try_finalize_on_silence(self, monotonic_time: float) -> None:
        if self._silence_start_time is None or self._current_chunk_start_time is None:
            return
        silence_duration = monotonic_time - self._silence_start_time
        if silence_duration < self.cfg.min_silence_for_boundary_sec:
            return
        chunk_duration = monotonic_time - self._current_chunk_start_time
        if chunk_duration < self.cfg.min_chunk_duration_sec:
            return
        end_sample = self._last_speech_sample or self._current_chunk_end_sample
        self._finalize_current_chunk_internal(monotonic_time, end_sample)

    def try_finalize_on_max_duration(self, monotonic_time: float) -> bool:
        if self._current_chunk_start_time is None:
            return False
        if (
            monotonic_time - self._current_chunk_start_time
        ) < self.cfg.max_chunk_duration_sec:
            return False
        end_sample = self._last_speech_sample or self._current_chunk_end_sample
        finalized = self._finalize_current_chunk_internal(
            monotonic_time, end_sample, force=True
        )
        return finalized is not None

    # Internal helpers
    def _finalize_current_chunk_internal(
        self,
        monotonic_time: float,
        end_sample_idx: Optional[int],
        force: bool = False,
    ) -> Optional[VoiceChunk]:
        if self._current_chunk_start_time is None:
            return None
        if self.reader.wav_sample_rate is None:
            return None

        duration = monotonic_time - self._current_chunk_start_time
        start_sample = self._current_chunk_start_sample
        end_sample = (
            end_sample_idx
            if end_sample_idx is not None
            else self._current_chunk_end_sample
        )
        if start_sample is None or end_sample is None:
            return None

        if not force and duration < self.cfg.min_chunk_duration_sec:
            logger.info(
                (
                    "***VAD: chunk too short "
                    "({duration:.2f}s < {min_duration}s minimum), "
                    "waiting for more speech"
                ).format(
                    duration=duration,
                    min_duration=self.cfg.min_chunk_duration_sec,
                )
            )
            return None

        chunk_file_path = self._save_chunk_audio_internal(
            start_sample, end_sample, duration
        )

        chunk = VoiceChunk(
            start_time_monotonic=self._current_chunk_start_time,
            end_time_monotonic=monotonic_time,
            start_sample_idx=start_sample,
            end_sample_idx=end_sample,
            duration_seconds=duration,
            sample_rate=self.reader.wav_sample_rate,
            file_path=chunk_file_path,
        )
        self._chunks.append(chunk)

        self._current_chunk_start_time = None
        self._current_chunk_start_sample = None
        self._current_chunk_end_sample = None
        self._silence_start_time = None

        logger.info(
            (
                "***VAD: chunk finalized - duration={duration:.2f}s, "
                "samples={start_sample}-{end_sample}"
            ).format(
                duration=duration,
                start_sample=start_sample,
                end_sample=end_sample,
            )
        )
        return chunk

    def _save_chunk_audio_internal(
        self, start_sample: int, end_sample: int, duration: float
    ) -> Optional[str]:
        if self._chunks_output_dir is None:
            return None
        try:
            os.makedirs(self._chunks_output_dir, exist_ok=True)
        except Exception as e:
            logger.error("***VAD: error creating chunks directory: %s", e)
            return None

        self._chunk_counter += 1
        import time as time_module

        chunk_filename = (
            f"chunk_{self._chunk_counter:04d}_{int(time_module.time())}.wav"
        )
        chunk_path = os.path.join(self._chunks_output_dir, chunk_filename)

        try:
            with wave.open(self.reader.wav_path, "rb") as wf_in:
                n_channels = wf_in.getnchannels()
                sampwidth = wf_in.getsampwidth()
                framerate = wf_in.getframerate()
                n_frames = wf_in.getnframes()
                if end_sample > n_frames:
                    return self._save_chunk_audio_manual(
                        start_sample, end_sample, chunk_path
                    )
                wf_in.setpos(start_sample)
                num_samples = end_sample - start_sample
                if num_samples <= 0:
                    logger.warning(
                        "***VAD: invalid chunk sample range (%s-%s)",
                        start_sample,
                        end_sample,
                    )
                    return None
                raw_audio = wf_in.readframes(num_samples)
                if len(raw_audio) == 0:
                    return self._save_chunk_audio_manual(
                        start_sample, end_sample, chunk_path
                    )
                with wave.open(chunk_path, "wb") as wf_out:
                    wf_out.setnchannels(n_channels)
                    wf_out.setsampwidth(sampwidth)
                    wf_out.setframerate(framerate)
                    wf_out.writeframes(raw_audio)
                logger.info(
                    ("***VAD: saved chunk %s to %s " "(%0.2fs)"),
                    self._chunk_counter,
                    chunk_path,
                    duration,
                )
                # Keep WAV file if ASR is enabled (ASR needs WAV format)
                if getattr(self.cfg, "keep_wav_for_asr", False):
                    return chunk_path
                mp3_path = convert_wav_to_mp3(chunk_path, delete_source=True)
                return mp3_path or chunk_path
        except wave.Error:
            return self._save_chunk_audio_manual(start_sample, end_sample, chunk_path)
        except Exception as e:
            logger.error("***VAD: error saving chunk: %s", e)
            try:
                return self._save_chunk_audio_manual(
                    start_sample, end_sample, chunk_path
                )
            except Exception as e2:
                logger.error("***VAD: error saving chunk manually: %s", e2)
                return None

    def _save_chunk_audio_manual(
        self, start_sample: int, end_sample: int, chunk_path: str
    ) -> Optional[str]:
        if self.reader.manual_wav_info is None:
            # Try parsing on demand
            # Accessing protected parse is intentionally avoided;
            # rely on prior population
            return None

        info = self.reader.manual_wav_info
        assert info is not None
        # WavInfo is a dataclass, not iterable. Access attributes directly
        # instead of unpacking as tuple.
        n_channels = info.channels
        sampwidth = info.sampwidth
        framerate = info.framerate
        data_offset = info.data_offset

        try:
            file_size = os.path.getsize(self.reader.wav_path)
            bytes_per_frame = n_channels * sampwidth
            start_byte_pos = data_offset + (start_sample * bytes_per_frame)
            num_samples = end_sample - start_sample
            num_bytes = num_samples * bytes_per_frame
            if num_samples <= 0:
                return None
            end_byte_pos = start_byte_pos + num_bytes
            if end_byte_pos > file_size:
                available_bytes = max(0, file_size - start_byte_pos)
                if available_bytes == 0:
                    logger.info(
                        (
                            "***VAD: chunk data not available yet "
                            "(file_size=%s, needed=%s)"
                        ),
                        file_size,
                        end_byte_pos,
                    )
                    return None
                num_bytes = available_bytes
                num_samples = available_bytes // bytes_per_frame
                if num_samples == 0:
                    return None
                logger.warning(
                    ("***VAD: warning - chunk file incomplete, " "reading %s/%s bytes"),
                    num_bytes,
                    end_sample - start_sample,
                )

            with open(self.reader.wav_path, "rb") as f_in:
                f_in.seek(start_byte_pos)
                raw_audio = f_in.read(num_bytes)
                if len(raw_audio) != num_bytes:
                    logger.warning(
                        ("***VAD: warning - read %s bytes, " "expected %s"),
                        len(raw_audio),
                        num_bytes,
                    )
                    if len(raw_audio) == 0:
                        return None
                with wave.open(chunk_path, "wb") as wf_out:
                    wf_out.setnchannels(int(n_channels))
                    wf_out.setsampwidth(int(sampwidth))
                    wf_out.setframerate(int(framerate))
                    wf_out.writeframes(raw_audio)
            # Keep WAV file if ASR is enabled (ASR needs WAV format)
            if getattr(self.cfg, "keep_wav_for_asr", False):
                return chunk_path
            mp3_path = convert_wav_to_mp3(chunk_path, delete_source=True)
            return mp3_path or chunk_path
        except Exception as e:
            logger.error("***VAD: error in manual chunk save: %s", e)
            return None
