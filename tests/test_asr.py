"""Tests for ASR (Automatic Speech Recognition) service."""

import os
import sys
import tempfile
import wave
from unittest.mock import Mock, patch

from pjsua_bot.asr import ASRConfig, ASRService, TranscriptionResult


# Helper to mock torch
def _mock_torch() -> Mock:
    """Create and register mock torch module."""
    mock_torch = Mock()
    mock_torch.cuda.is_available.return_value = False
    sys.modules["torch"] = mock_torch
    return mock_torch


def _unmock_torch() -> None:
    """Remove mock torch from sys.modules."""
    if "torch" in sys.modules and isinstance(sys.modules["torch"], Mock):
        del sys.modules["torch"]


class TestASRConfig:
    """Test cases for ASRConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ASRConfig()
        assert config.model_name == "omniASR_CTC_1B"
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
        """Test custom configuration values."""
        config = ASRConfig(
            model_name="omniASR_CTC_350M",
            device="cpu",
            language="eng_Latn",
            target_language="fas_Arab",
            batch_size=4,
            max_retries=5,
            retry_delay=2.0,
            retry_backoff=3.0,
            skip_on_error=False,
            log_errors=False,
        )
        assert config.model_name == "omniASR_CTC_350M"
        assert config.device == "cpu"
        assert config.language == "eng_Latn"
        assert config.target_language == "fas_Arab"
        assert config.batch_size == 4
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.retry_backoff == 3.0
        assert config.skip_on_error is False
        assert config.log_errors is False


class TestTranscriptionResult:
    """Test cases for TranscriptionResult dataclass."""

    def test_minimal_result(self) -> None:
        """Test minimal transcription result."""
        result = TranscriptionResult(text="Hello world")
        assert result.text == "Hello world"
        assert result.language is None
        assert result.language_probability is None
        assert result.duration == 0.0
        assert result.processing_time == 0.0
        assert result.chunks is None
        assert result.metadata is None

    def test_full_result(self) -> None:
        """Test full transcription result with all fields."""
        metadata = {"test": "data"}
        chunks = [{"text": "chunk1", "start": 0.0, "end": 1.0}]
        result = TranscriptionResult(
            text="Hello world",
            language="eng_Latn",
            language_probability=0.95,
            duration=5.0,
            processing_time=2.5,
            chunks=chunks,
            metadata=metadata,
        )
        assert result.text == "Hello world"
        assert result.language == "eng_Latn"
        assert result.language_probability == 0.95
        assert result.duration == 5.0
        assert result.processing_time == 2.5
        assert result.chunks == chunks
        assert result.metadata == metadata


class TestASRService:
    """Test cases for ASRService class."""

    def test_init_with_default_config(self) -> None:
        """Test initialization with default config."""
        with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            assert service.cfg.model_name == "omniASR_CTC_1B"
            assert service.available is False
            assert service._pipeline is None

    def test_init_with_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = ASRConfig(model_name="omniASR_CTC_350M", device="cpu")
        with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
            service = ASRService(config)
            assert service.cfg.model_name == "omniASR_CTC_350M"
            assert service.cfg.device == "cpu"

    def test_init_when_omnilingual_unavailable(self) -> None:
        """Test initialization when omnilingual-asr is not available."""
        with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
            with patch("pjsua_bot.asr._omnilingual_error", "import failed"):
                service = ASRService()
                assert service.available is False
                assert service._load_error is not None
                assert "omnilingual-asr not available" in service._load_error

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    @patch("builtins.print")
    def test_init_loads_model_successfully(
        self, mock_print: Mock, mock_pipeline_class: Mock
    ) -> None:
        """Test successful model loading."""
        mock_pipeline = Mock()
        mock_pipeline_class.return_value = mock_pipeline

        _mock_torch()
        try:
            service = ASRService()
            assert service.available is True
            assert service._pipeline == mock_pipeline
            assert service._device == "cpu"
        finally:
            _unmock_torch()

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    @patch("builtins.print")
    def test_init_loads_model_with_cuda(
        self, mock_print: Mock, mock_pipeline_class: Mock
    ) -> None:
        """Test model loading with CUDA device."""
        mock_pipeline = Mock()
        mock_pipeline_class.return_value = mock_pipeline

        mock_torch = _mock_torch()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA GPU"
        try:
            service = ASRService()
            assert service.available is True
            assert service._device == "cuda"
        finally:
            _unmock_torch()

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    @patch("builtins.print")
    def test_init_model_loading_fails(
        self, mock_print: Mock, mock_pipeline_class: Mock
    ) -> None:
        """Test model loading failure."""
        mock_pipeline_class.side_effect = Exception("Model loading failed")

        _mock_torch()
        try:
            service = ASRService()
            assert service.available is False
            assert service._load_error is not None
            assert "model loading failed" in service._load_error
        finally:
            _unmock_torch()

    def test_get_audio_duration_success(self) -> None:
        """Test getting audio duration from WAV file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            # Create a minimal WAV file - 1 second of audio
            # 16000 samples/sec * 1 second = 16000 frames
            # Each frame is 2 bytes (16-bit samples) * 1 channel = 2 bytes per frame
            # So 16000 frames = 32000 bytes
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 32000)  # 1 second of audio

            try:
                with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
                    service = ASRService()
                    duration = service._get_audio_duration(tmp.name)
                    assert duration is not None
                    # Should be approximately 1 second
                    # (32000 bytes / 2 bytes per frame / 16000 frames per second)
                    assert abs(duration - 1.0) < 0.1  # Allow small tolerance
            finally:
                os.unlink(tmp.name)

    def test_get_audio_duration_file_not_found(self) -> None:
        """Test getting audio duration for non-existent file."""
        service = ASRService()
        duration = service._get_audio_duration("/nonexistent/file.wav")
        assert duration is None

    def test_get_audio_duration_invalid_file(self) -> None:
        """Test getting audio duration for invalid file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"not a wav file")
            tmp.flush()

            try:
                service = ASRService()
                duration = service._get_audio_duration(tmp.name)
                assert duration is None
            finally:
                os.unlink(tmp.name)

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    @patch("builtins.print")
    def test_transcribe_success(
        self, mock_print: Mock, mock_pipeline_class: Mock
    ) -> None:
        """Test successful transcription."""
        mock_pipeline = Mock()
        mock_pipeline.transcribe.return_value = ["Hello world"]
        mock_pipeline_class.return_value = mock_pipeline

        _mock_torch()
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                with wave.open(tmp.name, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b"\x00" * 16000)

                try:
                    service = ASRService()
                    result = service.transcribe(tmp.name)

                    assert result is not None
                    assert result.text == "Hello world"
                    assert result.language == "fas_Arab"
                    assert result.duration > 0
                    assert result.processing_time > 0
                    assert result.metadata is not None
                    assert result.metadata["audio_path"] == tmp.name
                finally:
                    os.unlink(tmp.name)
        finally:
            _unmock_torch()

    def test_transcribe_service_not_available(self) -> None:
        """Test transcription when service is not available."""
        with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            result = service.transcribe("/path/to/audio.wav")
            assert result is None

    def test_transcribe_file_not_found(self) -> None:
        """Test transcription when audio file doesn't exist."""
        with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            result = service.transcribe("/nonexistent/file.wav")
            assert result is None

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    @patch("builtins.print")
    @patch("time.sleep")
    def test_transcribe_with_retry(
        self, mock_sleep: Mock, mock_print: Mock, mock_pipeline_class: Mock
    ) -> None:
        """Test transcription with retry logic."""
        mock_pipeline = Mock()
        # First call fails, second succeeds
        mock_pipeline.transcribe.side_effect = [
            Exception("Transcription failed"),
            ["Hello world"],
        ]
        mock_pipeline_class.return_value = mock_pipeline

        _mock_torch()
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                with wave.open(tmp.name, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b"\x00" * 16000)

                try:
                    config = ASRConfig(max_retries=2, retry_delay=0.1)
                    service = ASRService(config)
                    result = service.transcribe(tmp.name)

                    assert result is not None
                    assert result.text == "Hello world"
                    assert mock_pipeline.transcribe.call_count == 2
                finally:
                    os.unlink(tmp.name)
        finally:
            _unmock_torch()

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    def test_transcribe_retry_exhausted(self, mock_pipeline_class: Mock) -> None:
        """Test transcription when all retries are exhausted."""
        mock_pipeline = Mock()
        mock_pipeline.transcribe.side_effect = Exception("Transcription failed")
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 16000)

            try:
                config = ASRConfig(max_retries=2, retry_delay=0.1, skip_on_error=True)
                _mock_torch()
                try:
                    with patch("time.sleep"):  # Speed up test
                        service = ASRService(config)
                        result = service.transcribe(tmp.name)

                        assert result is None  # skip_on_error=True returns None
                finally:
                    _unmock_torch()
            finally:
                os.unlink(tmp.name)

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    def test_transcribe_chunks(self, mock_pipeline_class: Mock) -> None:
        """Test transcribing multiple chunks."""
        mock_pipeline = Mock()
        mock_pipeline.transcribe.return_value = ["Text 1", "Text 2"]
        mock_pipeline_class.return_value = mock_pipeline

        audio_files = []
        try:
            for _i in range(2):
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                with wave.open(tmp.name, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b"\x00" * 16000)
                audio_files.append(tmp.name)

            _mock_torch()
            try:
                service = ASRService()
                results = service.transcribe_chunks(audio_files)

                assert len(results) == 2
                assert results[0] is not None
                assert results[1] is not None
            finally:
                _unmock_torch()
        finally:
            for f in audio_files:
                if os.path.exists(f):
                    os.unlink(f)

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    def test_transcribe_batch(self, mock_pipeline_class: Mock) -> None:
        """Test batch transcription."""
        mock_pipeline = Mock()
        mock_pipeline.transcribe.return_value = ["Text 1", "Text 2", "Text 3"]
        mock_pipeline_class.return_value = mock_pipeline

        audio_files = []
        try:
            for _i in range(3):
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                with wave.open(tmp.name, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b"\x00" * 16000)
                audio_files.append(tmp.name)

            _mock_torch()
            try:
                service = ASRService()
                results = service.transcribe_batch(audio_files)

                assert len(results) == 3
                assert all(r is not None for r in results)
                mock_pipeline.transcribe.assert_called_once()
            finally:
                _unmock_torch()
        finally:
            for f in audio_files:
                if os.path.exists(f):
                    os.unlink(f)

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    def test_transcribe_batch_with_languages(self, mock_pipeline_class: Mock) -> None:
        """Test batch transcription with different languages."""
        mock_pipeline = Mock()
        mock_pipeline.transcribe.return_value = ["Text 1", "Text 2"]
        mock_pipeline_class.return_value = mock_pipeline

        audio_files = []
        try:
            for _i in range(2):
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                with wave.open(tmp.name, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b"\x00" * 16000)
                audio_files.append(tmp.name)

            _mock_torch()
            try:
                service = ASRService()
                languages = ["eng_Latn", "fas_Arab"]
                results = service.transcribe_batch(audio_files, languages=languages)

                assert len(results) == 2
                assert results[0] is not None
                assert results[1] is not None
                assert results[0].language == "eng_Latn"
                assert results[1].language == "fas_Arab"
            finally:
                _unmock_torch()
        finally:
            for f in audio_files:
                if os.path.exists(f):
                    os.unlink(f)

    def test_transcribe_batch_service_not_available(self) -> None:
        """Test batch transcription when service is not available."""
        with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            results = service.transcribe_batch(["/path1.wav", "/path2.wav"])
            assert len(results) == 2
            assert all(r is None for r in results)

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    def test_transcribe_batch_failure(self, mock_pipeline_class: Mock) -> None:
        """Test batch transcription failure."""
        mock_pipeline = Mock()
        mock_pipeline.transcribe.side_effect = Exception("Batch failed")
        mock_pipeline_class.return_value = mock_pipeline

        config = ASRConfig(skip_on_error=True)
        _mock_torch()
        try:
            service = ASRService(config)
            results = service.transcribe_batch(["/path1.wav", "/path2.wav"])

            assert len(results) == 2
            assert all(r is None for r in results)
        finally:
            _unmock_torch()

    def test_get_model_info(self) -> None:
        """Test getting model information."""
        with patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", False):
            service = ASRService()
            info = service.get_model_info()

            assert "available" in info
            assert "model_name" in info
            assert "device" in info
            assert "load_error" in info
            assert "backend" in info
            assert info["backend"] == "omnilingual-asr"
            assert info["available"] is False

    @patch("pjsua_bot.asr.ASRInferencePipeline")
    @patch("pjsua_bot.asr._OMNILINGUAL_AVAILABLE", True)
    def test_get_model_info_when_loaded(self, mock_pipeline_class: Mock) -> None:
        """Test getting model information when model is loaded."""
        mock_pipeline = Mock()
        mock_pipeline_class.return_value = mock_pipeline

        _mock_torch()
        try:
            service = ASRService()
            info = service.get_model_info()

            assert info["available"] is True
            assert info["device"] == "cpu"
            assert info["load_error"] is None
        finally:
            _unmock_torch()
