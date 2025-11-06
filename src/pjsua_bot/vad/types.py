from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class VoiceChunk:
    """Represents a detected voice chunk with boundary information."""
    start_time_monotonic: float
    end_time_monotonic: float
    start_sample_idx: int  # Sample index in original WAV file
    end_sample_idx: int    # Sample index in original WAV file
    duration_seconds: float
    sample_rate: int
    file_path: Optional[str] = None  # Path to saved chunk file, if saved
