"""Tests for VAD types."""

from pjsua_bot.vad.types import VoiceChunk


class TestVoiceChunk:
    """Test cases for VoiceChunk dataclass."""

    def test_voice_chunk_creation(self) -> None:
        """Test creating a VoiceChunk."""
        chunk = VoiceChunk(
            start_time_monotonic=100.0,
            end_time_monotonic=105.0,
            start_sample_idx=0,
            end_sample_idx=16000,
            duration_seconds=5.0,
            sample_rate=16000,
        )
        assert chunk.start_time_monotonic == 100.0
        assert chunk.end_time_monotonic == 105.0
        assert chunk.start_sample_idx == 0
        assert chunk.end_sample_idx == 16000
        assert chunk.duration_seconds == 5.0
        assert chunk.sample_rate == 16000
        assert chunk.file_path is None

    def test_voice_chunk_with_file_path(self) -> None:
        """Test creating a VoiceChunk with file path."""
        chunk = VoiceChunk(
            start_time_monotonic=200.0,
            end_time_monotonic=210.0,
            start_sample_idx=16000,
            end_sample_idx=32000,
            duration_seconds=10.0,
            sample_rate=16000,
            file_path="/path/to/chunk.wav",
        )
        assert chunk.file_path == "/path/to/chunk.wav"

    def test_voice_chunk_duration_calculation(self) -> None:
        """Test that duration matches time difference."""
        chunk = VoiceChunk(
            start_time_monotonic=0.0,
            end_time_monotonic=2.5,
            start_sample_idx=0,
            end_sample_idx=40000,
            duration_seconds=2.5,
            sample_rate=16000,
        )
        assert (
            chunk.end_time_monotonic - chunk.start_time_monotonic
            == chunk.duration_seconds
        )
