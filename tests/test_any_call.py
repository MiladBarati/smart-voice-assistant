"""Tests for AnyCall class."""

import sys
from typing import Any
from unittest.mock import Mock, patch

import pytest

from tests.conftest import create_mock_pjsua2


class TestAnyCall:
    """Test cases for AnyCall class."""

    @pytest.fixture(autouse=True)
    def setup_pjsua2_mock(self) -> Any:
        """Setup mock pjsua2 before each test."""
        mock_pj = create_mock_pjsua2()
        with patch.dict(sys.modules, {"pjsua2": mock_pj}):
            # Re-import the any_call module with mocked pjsua2
            import importlib

            import pjsua_bot.calls.any_call

            importlib.reload(pjsua_bot.calls.any_call)
            self.AnyCall = pjsua_bot.calls.any_call.AnyCall
            self.mock_pj = mock_pj
            yield

    def _create_mock_account(self) -> Mock:
        """Create a mock account for tests."""
        mock_account = Mock()
        mock_account.play_file = None
        mock_account.goodbye_file = None
        mock_account.waiting_file = None
        mock_account.silence_after_speech_sec = 3.0
        mock_account.enable_vad = True
        mock_account.enable_intent = False
        mock_account._intent_classifier = None
        mock_account._asr_service = None
        mock_account._asr_available = False
        mock_account.max_followup_questions = 2  # Required for ConversationFlowMixin
        return mock_account

    def test_init(self) -> None:
        """Test AnyCall initialization."""
        mock_account = self._create_mock_account()

        call = self.AnyCall(mock_account, call_id=123)
        assert call._acc_ref == mock_account
        assert call._pjsua_call_id == 123
        assert call.unique_call_id is not None
        assert call._start_time_utc is None
        assert call._end_time_utc is None
        assert call._direction is None
        assert call._caller_number is None
        assert call._callee_ext is None

    def test_init_call_metadata(self) -> None:
        """Test call metadata initialization."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=456)
        call._init_call_metadata()

        assert call._start_time_utc is None
        assert call._end_time_utc is None
        assert call._direction is None
        assert call._caller_number is None
        assert call._callee_ext is None
        assert call._recording_metadata is None
        assert call._bot_playback_start_time is None
        assert call._total_bot_talk_duration == 0.0

    def test_start_bot_playback_tracking(self) -> None:
        """Test starting bot playback tracking."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=789)
        assert call._bot_playback_start_time is None

        call._start_bot_playback_tracking()
        assert call._bot_playback_start_time is not None

    def test_start_bot_playback_tracking_multiple_calls(self) -> None:
        """Test that multiple calls to start tracking don't reset the timer."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=101)
        call._start_bot_playback_tracking()
        first_time = call._bot_playback_start_time

        # Call again - should not change
        call._start_bot_playback_tracking()
        assert call._bot_playback_start_time == first_time

    def test_stop_bot_playback_tracking(self) -> None:
        """Test stopping bot playback tracking."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=202)
        call._start_bot_playback_tracking()

        call._stop_bot_playback_tracking()
        assert call._bot_playback_start_time is None
        assert call._total_bot_talk_duration >= 0

    def test_stop_bot_playback_tracking_when_not_started(self) -> None:
        """Test stopping tracking when not started."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=303)
        # Don't start tracking
        call._stop_bot_playback_tracking()
        # Should not raise error
        assert call._bot_playback_start_time is None
        assert call._total_bot_talk_duration == 0.0

    def test_get_total_bot_talk_duration(self) -> None:
        """Test getting total bot talk duration."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=404)
        # Initially zero
        assert call._get_total_bot_talk_duration() == 0.0

        # Start tracking
        call._start_bot_playback_tracking()
        duration = call._get_total_bot_talk_duration()
        assert duration >= 0.0

    def test_get_total_bot_talk_duration_with_accumulated(self) -> None:
        """Test getting total duration with accumulated time."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=505)
        call._start_bot_playback_tracking()
        call._stop_bot_playback_tracking()
        # Should have accumulated some time (or 0 if very fast)
        total = call._get_total_bot_talk_duration()
        assert total >= 0.0

    def test_init_recording_state(self) -> None:
        """Test recording state initialization."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=606)
        call._init_recording_state()

        assert call._recorder is None
        assert call._recording_file == ""
        assert call._recording_call_media is None
        assert call._recording_start_time is None
        assert call._recording_duration == 0.0
        assert call._call_recording_dir is None
        assert call._cleanup_done is False

    def test_init_vad_state(self) -> None:
        """Test VAD state initialization."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=707)
        call._init_vad_state()

        assert call._vad is None
        assert call._vad_available is False

    def test_init_asr_support(self) -> None:
        """Test ASR support initialization."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=808)
        call._init_asr_support()

        # Check ASR-related attributes are initialized
        assert hasattr(call, "_asr_queue")

    def test_init_intent_state(self) -> None:
        """Test intent state initialization."""
        mock_account = self._create_mock_account()
        call = self.AnyCall(mock_account, call_id=909)
        call._init_intent_state()

        # Check intent-related attributes are initialized
        assert hasattr(call, "_intent_results")
