"""Tests for the satisfaction-flow state machine in `ConversationFlowMixin`.

These tests drive the state machine directly by manipulating the flags that
the surrounding mixins (`ASRSupportMixin`, `IntentHandlerMixin`,
`PlaybackMonitorMixin`, `GoodbyePlaybackMixin`) would normally toggle in
production. That keeps the tests fast and independent of pjsua2 / VAD / ASR.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional
from unittest.mock import patch

import pytest

from pjsua_bot.calls.mixins.conversation_flow import (
    AUDIO_FILES,
    ConversationFlowMixin,
    ConversationState,
    Turn,
    UserResponse,
)
from pjsua_bot.config import BotConfig


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


class MockAccount:
    """Minimal stand-in for `Account` used by the mixin."""

    def __init__(
        self,
        *,
        flow_mode: str = "satisfaction",
        max_satisfaction_retries: int = 2,
        support_transfer_extension: Optional[str] = None,
        max_followup_questions: int = 2,
    ) -> None:
        self.flow_mode = flow_mode
        self.max_satisfaction_retries = max_satisfaction_retries
        self.support_transfer_extension = support_transfer_extension
        self.max_followup_questions = max_followup_questions
        self.enable_conversation_flow = True
        self.domain = "test.local"
        self.goodbye_file = None


class MockCall(ConversationFlowMixin):
    """In-process call object that exposes just enough attributes for the mixin."""

    def __init__(self, account: MockAccount) -> None:
        self._acc_ref = account

        # Flags / collaborators the mixin reads.
        self._call_media = object()  # truthy placeholder
        self._mixed_recorder = None
        self._vad = None

        # ASR / intent state controlled directly by tests.
        self._asr_complete = False
        self._asr_chunk_texts: list[str] = []
        self._asr_lock = threading.Lock()
        self._intent_classified = False
        self._classified_intent: Optional[str] = None
        self._intent_confidence = 0.0
        self._classified_faq_config: dict[str, Any] | None = None
        self._intent_response_played = False
        self._intent_response_finished = False

        # Time-related stubs.
        self._hangup_time: Optional[float] = None
        self._welcome_finished_time: Optional[float] = None
        self._stop_player_time: Optional[float] = None
        self._time_state = None

        # Hook used by `_collect_event`.
        self.events: list[dict[str, Any]] = []

        # Track which prompts have been played and which goodbye/transfer were
        # invoked, so tests can assert on the surface behavior.
        self.prompts_played: list[str] = []
        self.goodbye_played = False
        self.transfer_attempts: list[str] = []

        # Bot-talk tracking no-ops.
        self._goodbye_playback_finished = False

        self._init_conversation_flow_state()

    # ---- Stubs replacing collaborator behavior ----

    def _collect_event(self, event_type: str, **kwargs: Any) -> None:
        self.events.append({"event_type": event_type, **kwargs})

    def _play_prompt(self, audio_key: str) -> bool:
        # Pretend the prompt finishes instantly. The dispatcher checks
        # `_check_prompt_finished()` which we override to return True below.
        assert audio_key in AUDIO_FILES, f"unknown audio_key: {audio_key}"
        self.prompts_played.append(audio_key)
        # Mark a prompt as "active and finished" so transitions can advance.
        self._flow_state.prompt_player = None
        self._flow_state.prompt_finished = True
        return True

    def _check_prompt_finished(self) -> bool:
        # In the real flow this checks elapsed time; for tests the prompt is
        # always done by the next tick.
        return True

    def _play_intent_response(self) -> None:
        # Real `_play_intent_response` would start audio playback. For tests
        # we treat it as instantly finished so the state machine can advance.
        self._intent_response_played = True
        self._intent_response_finished = True

    def _play_goodbye_message(self) -> None:
        self.goodbye_played = True
        self._goodbye_playback_finished = True
        self._hangup_time = 0.0

    def _mark_goodbye_finished(self) -> None:
        self._goodbye_playback_finished = True
        self._hangup_time = 0.0

    def _reset_asr_for_new_input(self) -> None:
        self._asr_complete = False
        self._intent_classified = False
        self._classified_intent = None
        self._classified_faq_config = None
        self._intent_response_played = False
        self._intent_response_finished = False
        self._asr_chunk_texts = []

    def _perform_support_transfer(self) -> bool:
        ext = getattr(self._acc_ref, "support_transfer_extension", None)
        if not ext:
            return False
        self.transfer_attempts.append(str(ext))
        return True


def _supply_classified_intent(
    call: MockCall,
    *,
    intent: str,
    faq_config: dict[str, Any],
    confidence: float = 0.95,
) -> None:
    """Pretend the intent classifier has just produced a result."""
    call._asr_complete = True
    call._intent_classified = True
    call._classified_intent = intent
    call._intent_confidence = confidence
    call._classified_faq_config = faq_config


def _supply_answer_finished(call: MockCall) -> None:
    """Pretend the per-FAQ answer audio has just finished playing."""
    call._intent_response_played = True
    call._intent_response_finished = True


def _supply_satisfaction_reply(
    call: MockCall,
    *,
    response: UserResponse,
) -> None:
    """Pretend ASR + intent classification on a satisfaction reply just landed."""
    call._asr_complete = True
    call._intent_classified = True
    if response == UserResponse.YES:
        call._classified_intent = "yes_response"
        call._classified_faq_config = {"is_control_intent": True}
    elif response == UserResponse.NO:
        call._classified_intent = "no_response"
        call._classified_faq_config = {"is_control_intent": True}
    else:
        # Unclear: classifier matched something else (not yes / not no).
        call._classified_intent = "default"
        call._classified_faq_config = {}


_FAQ = {
    "response_text": "ok",
    "response_audio": "assets/audio/faq_slow_computer.wav",
    "keywords": ["slow"],
}


def _drive_until_state(
    call: MockCall, target: ConversationState, *, max_ticks: int = 20
) -> None:
    """Tick the dispatcher until the state machine reaches `target`."""
    for _ in range(max_ticks):
        if call._flow_state.current_state == target:
            return
        call._handle_satisfaction_flow()
    raise AssertionError(
        f"state machine did not reach {target}; "
        f"stuck at {call._flow_state.current_state}"
    )


def _start_first_turn(call: MockCall) -> None:
    """Walk through ASR -> intent classify -> answer-finished -> awaiting-sat."""
    _supply_classified_intent(call, intent="slow_computer", faq_config=_FAQ)
    # WAITING_FOR_QUESTION -> PROCESSING_QUESTION (via _asr_complete)
    call._handle_satisfaction_flow()
    # PROCESSING_QUESTION -> PLAYING_ANSWER (records a Turn)
    call._handle_satisfaction_flow()
    # Answer is now "playing"; mark it finished, then tick to advance to
    # PLAYING_SATISFACTION_PROMPT, then again to AWAITING_SATISFACTION.
    _supply_answer_finished(call)
    call._handle_satisfaction_flow()  # PLAYING_ANSWER -> PLAYING_SATISFACTION_PROMPT
    call._handle_satisfaction_flow()  # PLAYING_SATISFACTION_PROMPT -> AWAITING_SATISFACTION
    assert call._flow_state.current_state == ConversationState.AWAITING_SATISFACTION


# --------------------------------------------------------------------------- #
# 7.2 - YES on first satisfaction check
# --------------------------------------------------------------------------- #


class TestYesOnFirstSatisfaction:
    def test_resolved_with_zero_retries(self) -> None:
        call = MockCall(MockAccount(max_satisfaction_retries=2))
        _start_first_turn(call)

        _supply_satisfaction_reply(call, response=UserResponse.YES)
        call._handle_satisfaction_flow()  # AWAITING_SATISFACTION -> PLAYING_THANK_YOU
        call._handle_satisfaction_flow()  # PLAYING_THANK_YOU -> ENDING_CALL

        assert call._flow_state.resolution == "resolved"
        assert call._flow_state.retry_count == 0
        assert len(call._flow_state.turns) == 1
        assert call._flow_state.turns[0].satisfaction == "yes"
        assert call._flow_state.turns[0].intent == "slow_computer"
        assert "thank_you" in call.prompts_played
        assert call.goodbye_played is False  # thank-you replaces goodbye audio
        assert call._goodbye_playback_finished is True


# --------------------------------------------------------------------------- #
# 7.3 - 2x NO with max_satisfaction_retries=2 -> escalated, 3 turns
# --------------------------------------------------------------------------- #


class TestEscalationAfterMaxNo:
    def test_two_no_with_max_two_escalates(self) -> None:
        call = MockCall(
            MockAccount(
                max_satisfaction_retries=2,
                support_transfer_extension="1099",
            )
        )

        # Turn 1: question, answer, NO
        _start_first_turn(call)
        _supply_satisfaction_reply(call, response=UserResponse.NO)
        call._handle_satisfaction_flow()  # -> PLAYING_RETRY_PROMPT
        call._handle_satisfaction_flow()  # PLAYING_RETRY_PROMPT -> WAITING_FOR_QUESTION
        assert call._flow_state.retry_count == 1
        assert (
            call._flow_state.current_state == ConversationState.WAITING_FOR_QUESTION
        )

        # Turn 2: question, answer, NO
        _supply_classified_intent(call, intent="slow_computer", faq_config=_FAQ)
        call._handle_satisfaction_flow()  # WAITING_FOR_QUESTION -> PROCESSING
        call._handle_satisfaction_flow()  # PROCESSING -> PLAYING_ANSWER
        _supply_answer_finished(call)
        call._handle_satisfaction_flow()  # PLAYING_ANSWER -> PLAYING_SAT_PROMPT
        call._handle_satisfaction_flow()  # PLAYING_SAT_PROMPT -> AWAITING_SATISFACTION

        _supply_satisfaction_reply(call, response=UserResponse.NO)
        call._handle_satisfaction_flow()  # -> PLAYING_RETRY_PROMPT (retry_count=2)
        call._handle_satisfaction_flow()  # PLAYING_RETRY_PROMPT -> WAITING_FOR_QUESTION
        assert call._flow_state.retry_count == 2

        # Turn 3 (the final allowed retry): question, answer, NO -> escalation.
        _supply_classified_intent(call, intent="slow_computer", faq_config=_FAQ)
        call._handle_satisfaction_flow()  # WAITING_FOR_QUESTION -> PROCESSING
        call._handle_satisfaction_flow()  # PROCESSING -> PLAYING_ANSWER
        _supply_answer_finished(call)
        call._handle_satisfaction_flow()  # PLAYING_ANSWER -> PLAYING_SAT_PROMPT
        call._handle_satisfaction_flow()  # PLAYING_SAT_PROMPT -> AWAITING_SATISFACTION

        _supply_satisfaction_reply(call, response=UserResponse.NO)
        call._handle_satisfaction_flow()  # -> PLAYING_ESCALATION
        call._handle_satisfaction_flow()  # PLAYING_ESCALATION -> ESCALATING
        call._handle_satisfaction_flow()  # ESCALATING -> ENDING_CALL (xfer initiated)

        assert call._flow_state.resolution == "escalated"
        assert call._flow_state.retry_count == 2
        assert call._flow_state.escalation_succeeded is True
        assert call.transfer_attempts == ["1099"]
        assert len(call._flow_state.turns) == 3
        for turn in call._flow_state.turns:
            assert turn.satisfaction == "no"


# --------------------------------------------------------------------------- #
# 7.4 - max_satisfaction_retries=3 allows one more retry before escalation
# --------------------------------------------------------------------------- #


class TestEscalationWithMaxThree:
    def test_three_retries_before_escalation(self) -> None:
        call = MockCall(
            MockAccount(
                max_satisfaction_retries=3,
                support_transfer_extension="1099",
            )
        )

        def _do_turn(no: bool, expected_retry: int) -> None:
            _supply_classified_intent(call, intent="slow_computer", faq_config=_FAQ)
            call._handle_satisfaction_flow()
            call._handle_satisfaction_flow()
            _supply_answer_finished(call)
            call._handle_satisfaction_flow()
            call._handle_satisfaction_flow()
            _supply_satisfaction_reply(
                call,
                response=UserResponse.NO if no else UserResponse.YES,
            )
            call._handle_satisfaction_flow()
            call._handle_satisfaction_flow()
            if no and expected_retry <= 3:
                assert call._flow_state.retry_count == expected_retry

        _do_turn(no=True, expected_retry=1)
        _do_turn(no=True, expected_retry=2)
        _do_turn(no=True, expected_retry=3)

        # Fourth turn: still NO, but budget is now exhausted -> escalation.
        _supply_classified_intent(call, intent="slow_computer", faq_config=_FAQ)
        call._handle_satisfaction_flow()
        call._handle_satisfaction_flow()
        _supply_answer_finished(call)
        call._handle_satisfaction_flow()
        call._handle_satisfaction_flow()
        _supply_satisfaction_reply(call, response=UserResponse.NO)
        call._handle_satisfaction_flow()  # -> PLAYING_ESCALATION
        call._handle_satisfaction_flow()  # -> ESCALATING
        call._handle_satisfaction_flow()  # -> ENDING_CALL

        assert call._flow_state.resolution == "escalated"
        assert call._flow_state.retry_count == 3
        assert len(call._flow_state.turns) == 4


# --------------------------------------------------------------------------- #
# 7.5 - ambiguous reply re-plays satisfaction prompt without consuming retries
# --------------------------------------------------------------------------- #


class TestAmbiguousReplyRePrompts:
    def test_first_ambiguous_then_yes(self) -> None:
        call = MockCall(MockAccount(max_satisfaction_retries=2))
        _start_first_turn(call)

        # First reply is ambiguous (UserResponse.UNKNOWN via empty transcription).
        # Provide an intent that the detector cannot classify as YES/NO.
        _supply_satisfaction_reply(call, response=UserResponse.UNKNOWN)
        call._handle_satisfaction_flow()  # -> PLAYING_SATISFACTION_PROMPT again
        assert (
            call._flow_state.current_state
            == ConversationState.PLAYING_SATISFACTION_PROMPT
        )
        assert call._flow_state.satisfaction_ambiguous_retries == 1
        assert call._flow_state.retry_count == 0  # NOT incremented
        # Count of satisfaction_prompt occurrences: initial play (during
        # _start_first_turn) + ambiguous re-prompt = 2.
        assert call.prompts_played.count("satisfaction_prompt") == 2

        # Re-prompt finishes; we re-enter AWAITING_SATISFACTION.
        call._handle_satisfaction_flow()
        assert (
            call._flow_state.current_state == ConversationState.AWAITING_SATISFACTION
        )

        # Now the caller answers YES.
        _supply_satisfaction_reply(call, response=UserResponse.YES)
        call._handle_satisfaction_flow()  # -> PLAYING_THANK_YOU
        call._handle_satisfaction_flow()  # -> ENDING_CALL

        assert call._flow_state.resolution == "resolved"
        assert call._flow_state.retry_count == 0
        assert call._flow_state.turns[0].satisfaction == "yes"

    def test_two_ambiguous_treated_as_no(self) -> None:
        call = MockCall(MockAccount(max_satisfaction_retries=2))
        _start_first_turn(call)

        _supply_satisfaction_reply(call, response=UserResponse.UNKNOWN)
        call._handle_satisfaction_flow()  # ambiguous #1 -> re-prompt
        assert (
            call._flow_state.current_state
            == ConversationState.PLAYING_SATISFACTION_PROMPT
        )
        call._handle_satisfaction_flow()  # PLAYING_SAT_PROMPT -> AWAITING

        _supply_satisfaction_reply(call, response=UserResponse.UNKNOWN)
        call._handle_satisfaction_flow()
        # Second ambiguous is treated as NO -> we move on. With budget=2 and
        # current retry_count=0, going NO consumes one retry and we play the
        # retry prompt.
        assert call._flow_state.current_state in (
            ConversationState.PLAYING_RETRY_PROMPT,
            ConversationState.WAITING_FOR_QUESTION,
        )
        assert call._flow_state.retry_count == 1


# --------------------------------------------------------------------------- #
# 7.6 - invalid --max-satisfaction-retries values rejected
# 7.7 - removed --max-followup-questions flag rejected
# --------------------------------------------------------------------------- #


class TestConfigValidation:
    def test_invalid_retries_zero_rejected(self) -> None:
        cfg = BotConfig(user="u", password="p", domain="d", max_satisfaction_retries=0)
        with pytest.raises(ValueError):
            cfg.validate()

    def test_invalid_retries_one_rejected(self) -> None:
        cfg = BotConfig(user="u", password="p", domain="d", max_satisfaction_retries=1)
        with pytest.raises(ValueError):
            cfg.validate()

    def test_invalid_retries_four_rejected(self) -> None:
        cfg = BotConfig(user="u", password="p", domain="d", max_satisfaction_retries=4)
        with pytest.raises(ValueError):
            cfg.validate()

    @pytest.mark.parametrize("v", [2, 3])
    def test_valid_retries_accepted(self, v: int) -> None:
        cfg = BotConfig(user="u", password="p", domain="d", max_satisfaction_retries=v)
        cfg.validate()  # should not raise

    def test_invalid_flow_mode_rejected(self) -> None:
        cfg = BotConfig(
            user="u", password="p", domain="d", flow_mode="weird"
        )  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            cfg.validate()

    def test_removed_followup_flag_exits(self) -> None:
        from pjsua_bot.register_bot import parse_arguments

        argv = [
            "prog",
            "--user",
            "u",
            "--password",
            "p",
            "--domain",
            "d",
            "--max-followup-questions",
            "2",
        ]
        with patch("sys.argv", argv):
            with pytest.raises(SystemExit) as excinfo:
                parse_arguments()
            assert excinfo.value.code != 0


# --------------------------------------------------------------------------- #
# 7.8 - escalation with no support_transfer_extension hangs up
# --------------------------------------------------------------------------- #


class TestEscalationWithoutExtension:
    def test_hangup_no_answer_when_extension_unset(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        call = MockCall(
            MockAccount(
                max_satisfaction_retries=2,
                support_transfer_extension=None,
            )
        )

        # Force the state machine into ESCALATING directly to keep the test
        # short. This skips the retry consumption loop, which is covered by
        # TestEscalationAfterMaxNo.
        call._flow_state.retry_count = 2
        call._transition_to(ConversationState.ESCALATING)

        with caplog.at_level(logging.WARNING):
            call._handle_satisfaction_flow()

        assert call._flow_state.resolution == "hangup_no_answer"
        assert call._flow_state.escalation_failed is True
        assert call._flow_state.escalation_succeeded is False
        assert call.transfer_attempts == []
        assert any(
            "support_transfer_extension is configured" in rec.message
            or "no support_transfer_extension" in rec.message
            or "no support transfer extension" in rec.message
            for rec in caplog.records
        )


# --------------------------------------------------------------------------- #
# 7.9 - caller hangs up mid-turn before satisfaction resolves
# --------------------------------------------------------------------------- #


class TestCallerHangupMidTurn:
    def test_resolution_inferred_as_hangup_no_answer(self) -> None:
        call = MockCall(MockAccount(max_satisfaction_retries=2))
        _start_first_turn(call)

        # Caller hangs up before answering the satisfaction prompt. The flow
        # state machine just stops being driven. The call-state-handler infers
        # `hangup_no_answer` when resolution is None but turns are non-empty.
        assert call._flow_state.resolution is None
        assert call._flow_state.turns[0].satisfaction is None

        # Simulate what `_collect_satisfaction_flow_data` would compute.
        from pjsua_bot.calls.mixins.call_state_handler import (
            CallStateHandlerMixin,
        )

        class _Collector(CallStateHandlerMixin):
            def __init__(self, c: MockCall) -> None:
                self._acc_ref = c._acc_ref
                self._flow_state = c._flow_state

        data = _Collector(call)._collect_satisfaction_flow_data()
        assert data is not None
        assert data["resolution"] == "hangup_no_answer"
        assert data["turns"][0]["satisfaction"] is None
        assert data["retry_count"] == 0


# --------------------------------------------------------------------------- #
# 7.10 - legacy follow-up flow remains intact when flow_mode == "legacy"
# (no existing dedicated legacy tests to rewrite; ensure dispatch is correct)
# --------------------------------------------------------------------------- #


class TestLegacyDispatchUnchanged:
    def test_legacy_mode_does_not_use_satisfaction_states(self) -> None:
        call = MockCall(
            MockAccount(flow_mode="legacy", max_followup_questions=2)
        )
        # Drive an ASR-complete + known-intent first turn in legacy mode.
        _supply_classified_intent(call, intent="slow_computer", faq_config=_FAQ)
        call._handle_conversation_flow()  # dispatch must hit legacy path
        # Legacy flow's _handle_processing_question uses PROCESSING_QUESTION ->
        # PLAYING_ANSWER for known intents (same as ours), but the legacy
        # post-answer transition is PLAYING_FOLLOWUP_PROMPT, not the new
        # satisfaction states.
        _supply_answer_finished(call)
        call._handle_conversation_flow()
        # In legacy mode the next state MUST NOT be any of the satisfaction-
        # specific states.
        sat_states = {
            ConversationState.PLAYING_SATISFACTION_PROMPT,
            ConversationState.AWAITING_SATISFACTION,
            ConversationState.PLAYING_RETRY_PROMPT,
            ConversationState.PLAYING_THANK_YOU,
            ConversationState.PLAYING_ESCALATION,
            ConversationState.ESCALATING,
        }
        assert call._flow_state.current_state not in sat_states


# --------------------------------------------------------------------------- #
# Smoke tests on Turn / classifier
# --------------------------------------------------------------------------- #


class TestSatisfactionReplyClassifier:
    @pytest.mark.parametrize(
        "response,expected",
        [
            (UserResponse.YES, "yes"),
            (UserResponse.NO, "no"),
            (UserResponse.REPEAT, "unclear"),
            (UserResponse.SUPPORT, "unclear"),
            (UserResponse.QUESTION, "unclear"),
            (UserResponse.UNKNOWN, "unclear"),
        ],
    )
    def test_outcome_mapping(self, response: UserResponse, expected: str) -> None:
        call = MockCall(MockAccount())
        assert call._classify_satisfaction_reply(response) == expected


class TestTurnDataclass:
    def test_turn_defaults(self) -> None:
        t = Turn(index=0)
        assert t.question is None
        assert t.intent is None
        assert t.satisfaction is None
        assert t.classification_failed is False
