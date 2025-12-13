"""Tests for ASRSupportMixin."""

import os
import tempfile
import time
from unittest.mock import Mock

from pjsua_bot.calls.mixins.asr_support import ASRSupportMixin


class MockCall(ASRSupportMixin):
    """Mock call class that uses ASRSupportMixin."""

    def __init__(self, acc_ref: Mock) -> None:
        self._acc_ref = acc_ref
        self._init_asr_support()


class TestASRSupportMixin:
    """Test cases for ASRSupportMixin."""

    def test_init_asr_support_disabled(self) -> None:
        """Test ASR support initialization when disabled."""
        mock_account = Mock()
        mock_account.enable_asr = False
        mock_account._asr_service = None
        mock_account._asr_available = False

        call = MockCall(mock_account)
        assert call._asr_enabled is False
        assert call._asr is None
        assert call._asr_available is False
        assert call._asr_chunk_texts == []
        assert call._asr_queue is None
        assert call._asr_thread is None

    def test_init_asr_support_enabled(self) -> None:
        """Test ASR support initialization when enabled."""
        mock_asr_service = Mock()
        mock_asr_service.available = True

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        assert call._asr_enabled is True
        assert call._asr == mock_asr_service
        assert call._asr_available is True
        assert call._asr_chunk_texts == []
        assert call._last_transcribed_chunk_count == 0

    def test_init_asr_support_service_unavailable(self) -> None:
        """Test ASR support when service is not available."""
        mock_asr_service = Mock()
        mock_asr_service.available = False

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = False

        call = MockCall(mock_account)
        assert call._asr_enabled is True
        assert call._asr == mock_asr_service
        assert call._asr_available is False

    def test_start_asr_thread_when_disabled(self) -> None:
        """Test starting ASR thread when ASR is disabled."""
        mock_account = Mock()
        mock_account.enable_asr = False
        mock_account._asr_service = None
        mock_account._asr_available = False

        call = MockCall(mock_account)
        call._start_asr_thread()
        assert call._asr_thread is None

    def test_start_asr_thread_when_enabled(self) -> None:
        """Test starting ASR thread when ASR is enabled."""
        mock_asr_service = Mock()
        mock_asr_service.available = True

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        call._start_asr_thread()
        assert call._asr_thread is not None
        assert call._asr_thread.is_alive()
        assert call._asr_queue is not None

        # Cleanup
        call._stop_asr_thread()

    def test_start_asr_thread_idempotent(self) -> None:
        """Test that starting ASR thread multiple times doesn't create multiple threads."""
        mock_asr_service = Mock()
        mock_asr_service.available = True

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        call._start_asr_thread()
        first_thread = call._asr_thread

        call._start_asr_thread()
        assert call._asr_thread == first_thread

        # Cleanup
        call._stop_asr_thread()

    def test_stop_asr_thread_when_not_started(self) -> None:
        """Test stopping ASR thread when not started."""
        mock_account = Mock()
        mock_account.enable_asr = False
        mock_account._asr_service = None
        mock_account._asr_available = False

        call = MockCall(mock_account)
        call._stop_asr_thread()  # Should not raise

    def test_stop_asr_thread_when_started(self) -> None:
        """Test stopping ASR thread when started."""
        mock_asr_service = Mock()
        mock_asr_service.available = True

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        call._start_asr_thread()
        assert call._asr_thread is not None

        call._stop_asr_thread()
        # Thread should be stopped (may take a moment)
        time.sleep(0.1)
        assert call._asr_thread is None

    def test_submit_transcription_task_when_disabled(self) -> None:
        """Test submitting transcription task when ASR is disabled."""
        mock_account = Mock()
        mock_account.enable_asr = False
        mock_account._asr_service = None
        mock_account._asr_available = False

        call = MockCall(mock_account)
        call._submit_transcription_task("/path/to/file.wav", 0)
        assert call._asr_queue is None

    def test_submit_transcription_task_when_enabled(self) -> None:
        """Test submitting transcription task when ASR is enabled."""
        mock_asr_service = Mock()
        mock_asr_service.available = True

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            call._submit_transcription_task(temp_path, 0)
            assert call._asr_queue is not None
            assert call._asr_thread is not None
        finally:
            call._stop_asr_thread()
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_asr_worker_thread_processes_task(self) -> None:
        """Test that ASR worker thread processes transcription tasks."""
        mock_result = Mock()
        mock_result.text = "test transcription"

        mock_asr_service = Mock()
        mock_asr_service.available = True
        mock_asr_service.transcribe = Mock(return_value=mock_result)

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            f.write(b"fake wav data")

        try:
            call._start_asr_thread()
            call._submit_transcription_task(temp_path, 0)

            # Wait for task to be processed
            time.sleep(0.5)

            # Check that transcription was added
            with call._asr_lock:
                assert len(call._asr_chunk_texts) > 0
                assert "test transcription" in call._asr_chunk_texts
        finally:
            call._stop_asr_thread()
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_asr_worker_thread_handles_missing_file(self) -> None:
        """Test that ASR worker thread handles missing files gracefully."""
        mock_asr_service = Mock()
        mock_asr_service.available = True

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        call._start_asr_thread()
        call._submit_transcription_task("/nonexistent/file.wav", 0)

        # Wait a bit
        time.sleep(0.3)

        # Should not crash, transcription should not be added
        with call._asr_lock:
            assert len(call._asr_chunk_texts) == 0

        call._stop_asr_thread()

    def test_asr_worker_thread_handles_transcription_error(self) -> None:
        """Test that ASR worker thread handles transcription errors gracefully."""
        mock_asr_service = Mock()
        mock_asr_service.available = True
        mock_asr_service.transcribe = Mock(side_effect=Exception("Transcription error"))

        mock_account = Mock()
        mock_account.enable_asr = True
        mock_account._asr_service = mock_asr_service
        mock_account._asr_available = True

        call = MockCall(mock_account)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            f.write(b"fake wav data")

        try:
            call._start_asr_thread()
            call._submit_transcription_task(temp_path, 0)

            # Wait for task to be processed
            time.sleep(0.3)

            # Should not crash, transcription should not be added
            with call._asr_lock:
                assert len(call._asr_chunk_texts) == 0
        finally:
            call._stop_asr_thread()
            if os.path.exists(temp_path):
                os.unlink(temp_path)
