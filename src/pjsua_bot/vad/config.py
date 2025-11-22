from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VADConfig:
    target_sample_rate: int = 16000
    threshold: float = 0.5  # Silero default
    min_speech_duration_ms: int = 150
    min_silence_duration_ms: int = 100
    window_size_samples: int = 16000 // 10  # 100ms
    max_chunk_duration_sec: float = 15.0  # Maximum chunk duration in seconds
    min_chunk_duration_sec: float = 5.0  # Minimum chunk duration in seconds
    min_silence_for_boundary_sec: float = (
        0.5  # Minimum silence duration to create chunk boundary
    )
    keep_wav_for_asr: bool = (
        False  # Keep WAV files instead of converting to MP3 (for ASR compatibility)
    )
