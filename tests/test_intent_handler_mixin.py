"""Tests for IntentHandlerMixin."""

from unittest.mock import Mock, patch

from pjsua_bot.calls.mixins.intent_handler import IntentHandlerMixin


class MockCall(IntentHandlerMixin):
    """Mock call class that uses IntentHandlerMixin."""

    def __init__(self, acc_ref: Mock) -> None:
        self._acc_ref = acc_ref
        self._asr_enabled = False
        self._asr_available = False
        self._asr_chunk_texts = []
        self._asr_lock = Mock()
        self._call_media = None
        self._collect_event = Mock()
        self._init_intent_state()

    def _collect_event(self, event_type: str, **kwargs) -> None:
        """Mock collect event."""
        pass


class TestIntentHandlerMixin:
    """Test cases for IntentHandlerMixin."""

    def test_init_intent_state_disabled(self) -> None:
        """Test intent state initialization when disabled."""
        mock_account = Mock()
        mock_account.enable_intent = False
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        assert call._intent_enabled is False
        assert call._intent_classifier is None
        assert call._intent_classified is False
        assert call._classified_intent is None
        assert call._intent_confidence == 0.0
        assert call._intent_response_played is False

    def test_init_intent_state_enabled(self) -> None:
        """Test intent state initialization when enabled."""
        mock_classifier = Mock()
        mock_classifier.__class__.__name__ = "TestClassifier"

        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = mock_classifier

        with patch("builtins.print"):
            call = MockCall(mock_account)
            assert call._intent_enabled is True
            assert call._intent_classifier == mock_classifier
            assert call._intent_classified is False
            assert call._classified_intent is None
            assert call._intent_confidence == 0.0

    def test_setup_intent_classifier(self) -> None:
        """Test setting up intent classifier."""
        mock_account = Mock()
        call = MockCall(mock_account)

        mock_classifier = Mock()
        mock_classifier.__class__.__name__ = "NewClassifier"

        with patch("builtins.print"):
            call._setup_intent_classifier(mock_classifier)
            assert call._intent_classifier == mock_classifier
            assert call._intent_enabled is True

