"""Tests for IntentHandlerMixin."""

import os
import tempfile
import threading
import time
from typing import Any
from unittest.mock import Mock, patch

from pjsua_bot.calls.mixins.intent_handler import IntentHandlerMixin
from pjsua_bot.intent.classifier import RuleBasedClassifier


class MockCall(IntentHandlerMixin):
    """Mock call class that uses IntentHandlerMixin."""

    def __init__(self, acc_ref: Mock) -> None:
        self._acc_ref = acc_ref
        self._asr_enabled = False
        self._asr_available = False
        self._asr_chunk_texts: list[str] = []
        self._asr_lock: threading.Lock = threading.Lock()
        self._call_media = None
        self._collected_events: list[dict[str, Any]] = []

        def _collect_event(event_type: str, **kwargs: Any) -> None:
            self._collected_events.append({"event_type": event_type, **kwargs})

        self._collect_event = _collect_event
        self._init_intent_state()


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
        assert call._intent_results == []

    def test_init_intent_state_enabled(self) -> None:
        """Test intent state initialization when enabled."""
        mock_classifier = Mock()
        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = mock_classifier

        call = MockCall(mock_account)
        assert call._intent_enabled is True
        assert call._intent_classifier == mock_classifier

    def test_setup_intent_classifier(self) -> None:
        """Test setting up intent classifier."""
        mock_classifier = Mock()
        mock_account = Mock()
        mock_account.enable_intent = False
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        call._setup_intent_classifier(mock_classifier)
        assert call._intent_classifier == mock_classifier
        assert call._intent_enabled is True

    def test_classify_intent_when_disabled(self) -> None:
        """Test intent classification when disabled."""
        mock_account = Mock()
        mock_account.enable_intent = False
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        result = call._classify_intent()
        assert result is None

    def test_classify_intent_no_transcription(self) -> None:
        """Test intent classification with no transcription."""
        classifier = RuleBasedClassifier()
        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = classifier

        call = MockCall(mock_account)
        call._asr_chunk_texts = []
        call._asr_lock = threading.Lock()

        result = call._classify_intent()
        assert result is None

    def test_classify_intent_with_transcription(self) -> None:
        """Test intent classification with transcription."""
        classifier = RuleBasedClassifier()
        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = classifier

        call = MockCall(mock_account)
        call._asr_chunk_texts = ["کامپیوترم کند است"]
        call._asr_lock = threading.Lock()

        result = call._classify_intent()
        assert result is not None
        intent_name, confidence = result
        assert intent_name in ("slow_computer", "slow_computer_general")
        assert confidence > 0.0
        assert call._intent_classified is True
        assert call._classified_intent == intent_name

    def test_classify_intent_already_classified(self) -> None:
        """Test that classification is cached after first call."""
        classifier = RuleBasedClassifier()
        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = classifier

        call = MockCall(mock_account)
        call._asr_chunk_texts = ["کامپیوترم کند است"]
        call._asr_lock = threading.Lock()

        result1 = call._classify_intent()
        result2 = call._classify_intent()

        assert result1 == result2
        assert call._intent_classified is True

    def test_play_intent_response_no_intent(self) -> None:
        """Test playing intent response when no intent is classified."""
        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        call._play_intent_response()
        assert call._intent_response_played is False

    def test_play_intent_response_with_audio_file(self) -> None:
        """Test playing intent response with audio file."""
        classifier = RuleBasedClassifier()
        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = classifier

        call = MockCall(mock_account)
        call._asr_chunk_texts = ["کامپیوترم کند است"]
        call._asr_lock = threading.Lock()

        # Create a mock audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            f.write(b"fake wav data")

        try:
            # Mock the FAQ config to return our temp file
            with patch("pjsua_bot.intent.faq_config.FAQS") as mock_faqs:
                mock_faqs.get.return_value = {
                    "response_audio": temp_path,
                    "response_text": "Test response",
                }

                # Mock pjsua2 components - pj is imported inside the function
                mock_player = Mock()
                mock_pj_class = Mock(return_value=mock_player)
                mock_call_media = Mock()
                call._call_media = mock_call_media

                # Mock get_wav_duration and pjsua2 imports
                with patch("pjsua_bot.utils.get_wav_duration") as mock_duration:
                    mock_duration.return_value = 5.0

                    # Mock pjsua2 module
                    mock_pj = Mock()
                    mock_pj.AudioMediaPlayer = mock_pj_class

                    with patch.dict("sys.modules", {"pjsua2": mock_pj}):
                        call._play_intent_response()

                        # Should have attempted to play
                        assert call._intent_response_played is True
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_play_intent_response_no_call_media(self) -> None:
        """Test playing intent response when call media is not available."""
        classifier = RuleBasedClassifier()
        mock_account = Mock()
        mock_account.enable_intent = True
        mock_account._intent_classifier = classifier

        call = MockCall(mock_account)
        call._asr_chunk_texts = ["کامپیوترم کند است"]
        call._asr_lock = threading.Lock()
        call._call_media = None

        # Classify intent first
        call._classify_intent()

        # Create a mock audio file that exists
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            f.write(b"fake wav data")

        try:
            # Mock the FAQ config
            with patch("pjsua_bot.intent.faq_config.FAQS") as mock_faqs:
                mock_faqs.get.return_value = {
                    "response_audio": temp_path,
                    "response_text": "Test response",
                }

                call._play_intent_response()
                # When call_media is None, _play_response_audio sets
                # _intent_response_finished
                assert call._intent_response_finished is True
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_check_intent_response_status_not_played(self) -> None:
        """Test checking intent response status when not played."""
        mock_account = Mock()
        mock_account.enable_intent = False
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        assert call.check_intent_response_status() is True

    def test_check_intent_response_status_finished(self) -> None:
        """Test checking intent response status when finished."""
        mock_account = Mock()
        mock_account.enable_intent = False
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        call._intent_response_played = True
        call._intent_response_finished = True
        assert call.check_intent_response_status() is True

    def test_check_intent_response_status_still_playing(self) -> None:
        """Test checking intent response status when still playing."""
        mock_account = Mock()
        mock_account.enable_intent = False
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        call._intent_response_played = True
        call._intent_response_finished = False
        call._intent_response_stop_time = time.time() + 10.0
        assert call.check_intent_response_status() is False

    def test_check_intent_response_status_time_reached(self) -> None:
        """Test checking intent response status when stop time is reached."""
        mock_account = Mock()
        mock_account.enable_intent = False
        mock_account._intent_classifier = None

        call = MockCall(mock_account)
        call._intent_response_played = True
        call._intent_response_finished = False
        call._intent_response_stop_time = time.time() - 1.0  # Past time
        call._intent_response_player = Mock()

        with patch.object(call._intent_response_player, "stopTransmit"):
            result = call.check_intent_response_status()
            assert result is True
            assert call._intent_response_finished is True
