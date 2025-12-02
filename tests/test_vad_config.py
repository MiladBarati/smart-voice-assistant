"""Tests for VAD configuration."""

from pjsua_bot.vad.config import VADConfig


class TestVADConfig:
    """Test cases for VADConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default VAD configuration values."""
        config = VADConfig()
        assert config.target_sample_rate == 16000
        assert config.threshold == 0.5
        assert config.min_speech_duration_ms == 150
        assert config.min_silence_duration_ms == 100
        assert config.window_size_samples == 1600  # 16000 // 10
        assert config.max_chunk_duration_sec == 15.0
        assert config.min_chunk_duration_sec == 5.0
        assert config.min_silence_for_boundary_sec == 0.5
        assert config.keep_wav_for_asr is False

    def test_custom_config(self) -> None:
        """Test custom VAD configuration values."""
        config = VADConfig(
            target_sample_rate=8000,
            threshold=0.7,
            min_speech_duration_ms=200,
            min_silence_duration_ms=150,
            window_size_samples=800,
            max_chunk_duration_sec=20.0,
            min_chunk_duration_sec=3.0,
            min_silence_for_boundary_sec=1.0,
            keep_wav_for_asr=True,
        )
        assert config.target_sample_rate == 8000
        assert config.threshold == 0.7
        assert config.min_speech_duration_ms == 200
        assert config.min_silence_duration_ms == 150
        assert config.window_size_samples == 800
        assert config.max_chunk_duration_sec == 20.0
        assert config.min_chunk_duration_sec == 3.0
        assert config.min_silence_for_boundary_sec == 1.0
        assert config.keep_wav_for_asr is True
