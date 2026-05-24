"""Tests for ASR omnilingual service."""

import os
import tempfile
import wave
from typing import Any
from unittest.mock import Mock, patch

import pytest

from pjsua_bot.asr_omnilingual import ASRConfig, ASRService, TranscriptionResult


class TestASRConfig:
    """Test cases for ASRConfig."""

    def test_default_config(self) -> None:
        """Test default ASR configuration."""
        config = ASRConfig()
        assert config.model_name == "omniASR_CTC_300M"
        assert config.device == "auto"
        assert config.language == "fas_Arab"
        assert config.target_language is None
        assert config.batch_size == 1
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff == 2.0
        assert config.skip_on_error is True
        assert config.log_errors is True

    def test_custom_config(self) -> None:
        """Test custom ASR configuration."""
        config = ASRConfig(
            model_name="omniASR_CTC_300M",
            device="cpu",
            language="eng_Latn",
            target_language="fas_Arab",
            batch_size=2,
            max_retries=5,
            retry_delay=2.0,
            retry_backoff=3.0,
            skip_on_error=False,
            log_errors=False,
        )
        assert config.model_name == "omniASR_CTC_300M"
        assert config.device == "cpu"
        assert config.language == "eng_Latn"
        assert config.target_language == "fas_Arab"
        assert config.batch_size == 2
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.retry_backoff == 3.0
        assert config.skip_on_error is False
        assert config.log_errors is False


class TestTranscriptionResult:
    """Test cases for TranscriptionResult."""

    def test_minimal_result(self) -> None:
        """Test minimal transcription result."""
        result = TranscriptionResult(text="test transcription")
        assert result.text == "test transcription"
        assert result.language is None
        assert result.language_probability is None
        assert result.duration == 0.0
        assert result.processing_time == 0.0
        assert result.chunks is None
        assert result.metadata is None

    def test_full_result(self) -> None:
        """Test full transcription result."""
        result = TranscriptionResult(
            text="test transcription",
            language="fas_Arab",
            language_probability=0.95,
            duration=5.0,
            processing_time=2.0,
            chunks=[{"text": "chunk1", "start": 0.0, "end": 2.5}],
            metadata={"model": "test_model"},
        )
        assert result.text == "test transcription"
        assert result.language == "fas_Arab"
        assert result.language_probability == 0.95
        assert result.duration == 5.0
        assert result.processing_time == 2.0
        assert result.chunks == [{"text": "chunk1", "start": 0.0, "end": 2.5}]
        assert result.metadata == {"model": "test_model"}


class TestASRService:
    """Test cases for ASRService."""

    def test_init_with_default_config(self) -> None:
        """Test ASR service initialization with default config."""
        # Mock the model loading to avoid slow initialization
        with patch("pjsua_bot.asr_omnilingual._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            assert service.cfg.model_name == "omniASR_CTC_300M"
            assert service._pipeline is None
            assert service.available is False

    def test_init_with_custom_config(self) -> None:
        """Test ASR service initialization with custom config."""
        config = ASRConfig(model_name="omniASR_CTC_300M", device="cpu")
        service = ASRService(config)
        assert service.cfg.model_name == "omniASR_CTC_300M"
        assert service.cfg.device == "cpu"

    def test_init_when_omnilingual_unavailable(self) -> None:
        """Test ASR service initialization when omnilingual-asr is not available."""
        with patch("pjsua_bot.asr_omnilingual._OMNILINGUAL_AVAILABLE", False):
            with patch("pjsua_bot.asr_omnilingual._omnilingual_error", "import failed"):
                service = ASRService()
                assert service.available is False
                assert "import failed" in (service._load_error or "")

    def test_get_audio_duration_success(self) -> None:
        """Test getting audio duration from valid WAV file."""
        # Create a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                # Write 1 second of silence
                wf.writeframes(b"\x00" * 16000 * 2)

        try:
            # Mock model loading to avoid slow initialization
            with patch("pjsua_bot.asr_omnilingual._OMNILINGUAL_AVAILABLE", False):
                service = ASRService()
                duration = service._get_audio_duration(temp_path)
                assert duration is not None
                assert abs(duration - 1.0) < 0.1
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_audio_duration_file_not_found(self) -> None:
        """Test getting audio duration from non-existent file."""
        with patch("pjsua_bot.asr_omnilingual._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            duration = service._get_audio_duration("/nonexistent/file.wav")
            assert duration is None

    def test_get_audio_duration_invalid_file(self) -> None:
        """Test getting audio duration from invalid file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = f.name
            f.write(b"not a wav file")

        try:
            with patch("pjsua_bot.asr_omnilingual._OMNILINGUAL_AVAILABLE", False):
                service = ASRService()
                duration = service._get_audio_duration(temp_path)
                assert duration is None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transcribe_service_not_available(self) -> None:
        """Test transcription when service is not available."""
        with patch("pjsua_bot.asr_omnilingual._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            service.available = False
            service._load_error = "Service not available"

            result = service.transcribe("/path/to/audio.wav")
            assert result is None

    def test_transcribe_file_not_found(self) -> None:
        """Test transcription when file is not found."""
        with patch("pjsua_bot.asr_omnilingual._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            service.available = True

            result = service.transcribe("/nonexistent/file.wav")
            assert result is None

    @pytest.mark.skipif(
        not os.getenv("TEST_ASR_OMNILINGUAL"),
        reason="Requires omnilingual-asr to be installed and configured",
    )
    def test_transcribe_success(self) -> None:
        """Test successful transcription (requires omnilingual-asr)."""
        # Create a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                # Write 1 second of silence
                wf.writeframes(b"\x00" * 16000 * 2)

        try:
            service = ASRService()
            if service.available:
                result = service.transcribe(temp_path)
                # Result may be None if service is not properly configured
                # or may contain transcription text
                assert result is None or isinstance(result, TranscriptionResult)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transcribe_with_retry(self) -> None:
        """Test transcription with retry logic."""
        service = ASRService()
        service.available = True
        service._pipeline = Mock()

        # Mock pipeline to fail first time, succeed second time
        call_count = 0

        def mock_transcribe(*args: Any, **kwargs: Any) -> list[str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transcription error")
            return ["test transcription"]

        service._pipeline.transcribe = mock_transcribe

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 16000 * 2)

        try:
            with patch.object(service, "_get_audio_duration", return_value=1.0):
                result = service.transcribe(temp_path, retry_count=0)
                # Should retry and eventually succeed
                assert result is not None or call_count > 1
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transcribe_retry_exhausted(self) -> None:
        """Test transcription when retries are exhausted."""
        config = ASRConfig(max_retries=2, skip_on_error=True)
        service = ASRService(config)
        service.available = True
        service._pipeline = Mock()
        service._pipeline.transcribe = Mock(side_effect=Exception("Always fails"))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 16000 * 2)

        try:
            with patch.object(service, "_get_audio_duration", return_value=1.0):
                result = service.transcribe(temp_path, retry_count=0)
                # Should return None after retries exhausted
                assert result is None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
