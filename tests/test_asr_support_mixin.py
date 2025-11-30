"""Tests for ASRSupportMixin."""

from unittest.mock import Mock, patch

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

