"""Conversation flow state machine for multi-turn dialogues."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, List, Literal, Optional

logger = logging.getLogger(__name__)

Resolution = Literal["resolved", "escalated", "hangup_no_answer"]


class ConversationState(Enum):
    """States in the conversation flow state machine.

    The first block of states is shared by both the legacy and satisfaction
    flows. States with the `SAT_` prefix in their value belong to the new
    satisfaction flow only.
    """

    # ---- Shared states ----

    # Initial state - waiting for user's first question
    WAITING_FOR_QUESTION = "waiting_for_question"

    # Processing user's question (ASR/intent classification)
    PROCESSING_QUESTION = "processing_question"

    # Playing FAQ response (bot knows the answer)
    PLAYING_ANSWER = "playing_answer"

    # ---- Legacy-flow states ----

    # Playing "Did you have any other questions?" prompt
    PLAYING_FOLLOWUP_PROMPT = "playing_followup_prompt"

    # Waiting for YES/NO response to followup prompt
    WAITING_FOR_FOLLOWUP_RESPONSE = "waiting_for_followup_response"

    # Playing "Repeat or get human support?" prompt (bot doesn't know)
    PLAYING_FALLBACK_PROMPT = "playing_fallback_prompt"

    # Waiting for REPEAT/SUPPORT response
    WAITING_FOR_FALLBACK_RESPONSE = "waiting_for_fallback_response"

    # Playing "Please ask your next question" prompt
    PLAYING_ASK_NEXT_QUESTION = "playing_ask_next_question"

    # Transferring to human support
    TRANSFERRING_TO_SUPPORT = "transferring_to_support"

    # Max follow-up questions reached
    MAX_RETRIES_REACHED = "max_retries_reached"

    # ---- Satisfaction-flow states ----

    # Playing "Did this answer your question?" prompt
    PLAYING_SATISFACTION_PROMPT = "sat_playing_satisfaction_prompt"

    # Waiting for YES/NO satisfaction response
    AWAITING_SATISFACTION = "sat_awaiting_satisfaction"

    # Playing "Let's try again, please rephrase your question" prompt
    PLAYING_RETRY_PROMPT = "sat_playing_retry_prompt"

    # Playing "Thank you for calling" prompt before hangup
    PLAYING_THANK_YOU = "sat_playing_thank_you"

    # Playing "Transferring you to a human agent" announcement
    PLAYING_ESCALATION = "sat_playing_escalation"

    # Performing blind SIP transfer (or fallback hangup if no extension)
    ESCALATING = "sat_escalating"

    # ---- Common terminal state ----

    # Playing goodbye and ending call
    ENDING_CALL = "ending_call"


@dataclass
class Turn:
    """One question/answer/satisfaction triple in a satisfaction-flow call.

    Used purely for telemetry. Appended to the flow state when the bot starts
    playing an answer; updated with the caller's satisfaction reply (yes/no/
    null) once the satisfaction state resolves.
    """

    index: int
    question: Optional[str] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    answer_audio: Optional[str] = None
    satisfaction: Optional[Literal["yes", "no", "unclear"]] = None
    classification_failed: bool = False


class UserResponse(Enum):
    """Types of user responses detected."""

    YES = "yes"
    NO = "no"
    REPEAT = "repeat"
    SUPPORT = "support"
    QUESTION = "question"
    UNKNOWN = "unknown"


@dataclass
class ConversationFlowState:
    """State container for conversation flow."""

    current_state: ConversationState = ConversationState.WAITING_FOR_QUESTION
    question_count: int = 0
    max_questions: int = 3  # legacy flow: 1 initial + 2 follow-ups
    last_intent: Optional[str] = None
    last_confidence: float = 0.0
    prompt_player: Any = None
    prompt_start_time: Optional[float] = None
    prompt_stop_time: Optional[float] = None
    prompt_finished: bool = False
    waiting_for_user_since: Optional[float] = None

    # ---- Satisfaction-flow fields ----
    # Number of classified NO satisfaction answers seen so far (0..max).
    retry_count: int = 0
    # Max NO answers tolerated before escalation. Only used in satisfaction mode.
    max_satisfaction_retries: int = 2
    # Ambiguous-satisfaction sub-prompt counter, reset each turn.
    satisfaction_ambiguous_retries: int = 0
    # Per-turn telemetry for the satisfaction flow.
    turns: List[Turn] = field(default_factory=list)
    # Final resolution outcome recorded in the Elasticsearch call record.
    resolution: Optional[Resolution] = None
    # Set when escalation transfer succeeds / fails (only meaningful when
    # resolution == "escalated").
    escalation_succeeded: Optional[bool] = None
    escalation_failed: bool = False


# Audio file paths (relative to project root)
AUDIO_FILES = {
    # ---- Legacy flow prompts ----
    "any_other_questions": "assets/audio/any_other_questions.wav",
    "ask_next_question": "assets/audio/ask_next_question.wav",
    "repeat_or_support": "assets/audio/repeat_or_support.wav",
    "transferring_to_support": "assets/audio/transferring_to_support.wav",
    "max_retries_reached": "assets/audio/max_retries_reached.wav",
    # ---- Satisfaction flow prompts ----
    "satisfaction_prompt": "assets/audio/satisfaction_prompt.wav",
    "try_again_prompt": "assets/audio/try_again_prompt.wav",
    "thank_you": "assets/audio/thank_you.wav",
    "escalation_announcement": "assets/audio/escalation_announcement.wav",
}


class ConversationFlowMixin:
    """Mixin for managing multi-turn conversation flow.

    This mixin implements a state machine that manages:
    - Multiple question/answer cycles (max 2 follow-ups)
    - Fallback to human support when bot doesn't know
    - YES/NO detection for follow-up prompts
    - REPEAT/SUPPORT detection for fallback prompts
    """

    # Attributes supplied by sibling mixins / host class
    _acc_ref: Any
    _call_media: Any
    _mixed_recorder: Any
    _vad: Any
    _collect_event: Callable[..., None]
    _asr_complete: bool
    _classified_intent: Optional[str]
    _intent_confidence: float
    _intent_response_finished: bool
    # Time tracking attributes - must be Optional[float] for mixin compatibility
    _hangup_time: Optional[float]
    _welcome_finished_time: Optional[float]
    _stop_player_time: Optional[float]

    if TYPE_CHECKING:

        def _play_goodbye_message(self) -> None: ...
        def _start_bot_playback_tracking(self) -> None: ...
        def _stop_bot_playback_tracking(self) -> None: ...
        def is_active(self) -> bool: ...
        def _play_intent_response(self) -> None: ...
        def _mark_goodbye_finished(self) -> None: ...

    # ------------------------------------------------------------------#
    # Initialization
    # ------------------------------------------------------------------#

    def _init_conversation_flow_state(self) -> None:
        """Initialize conversation flow state.

        Reads `flow_mode` and `max_satisfaction_retries` from the account so
        each call snapshots the mode at construction time.
        """
        self._flow_state = ConversationFlowState()
        self._flow_state.max_questions = (
            getattr(self._acc_ref, "max_followup_questions", 2) + 1
        )  # +1 for initial question (legacy flow only)
        self._flow_state.max_satisfaction_retries = int(
            getattr(self._acc_ref, "max_satisfaction_retries", 2)
        )

        self._project_root = self._get_project_root()

        if self._flow_mode() == "satisfaction":
            logger.info(
                "ConversationFlow: initialized in satisfaction mode "
                "(max_retries=%d, support_extension=%r)",
                self._flow_state.max_satisfaction_retries,
                getattr(self._acc_ref, "support_transfer_extension", None),
            )
        else:
            logger.info(
                "ConversationFlow: initialized in legacy mode (max_questions=%d)",
                self._flow_state.max_questions,
            )

    def _flow_mode(self) -> str:
        """Return the configured flow mode for this call ("legacy" | "satisfaction")."""
        return str(getattr(self._acc_ref, "flow_mode", "legacy"))

    def _get_project_root(self) -> str:
        """Get project root directory."""
        # Navigate up from mixins directory to project root
        current_file = os.path.abspath(__file__)
        # mixins -> calls -> pjsua_bot -> src -> project_root
        project_root = os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            )
        )
        return project_root

    def _get_audio_path(self, audio_key: str) -> Optional[str]:
        """Get full path to an audio file."""
        if audio_key not in AUDIO_FILES:
            logger.warning("ConversationFlow: unknown audio key: %s", audio_key)
            return None

        audio_path = os.path.join(self._project_root, AUDIO_FILES[audio_key])
        if not os.path.exists(audio_path):
            logger.warning("ConversationFlow: audio file not found: %s", audio_path)
            return None

        return audio_path

    # ------------------------------------------------------------------#
    # State Machine Core
    # ------------------------------------------------------------------#

    def _transition_to(self, new_state: ConversationState) -> None:
        """Transition to a new conversation state."""
        old_state = self._flow_state.current_state
        self._flow_state.current_state = new_state

        logger.info(
            "ConversationFlow: %s -> %s (questions: %d/%d)",
            old_state.value,
            new_state.value,
            self._flow_state.question_count,
            self._flow_state.max_questions,
        )

        self._collect_event(
            event_type="conversation_state_change",
            old_state=old_state.value,
            new_state=new_state.value,
            question_count=self._flow_state.question_count,
        )

    def _is_known_answer(self) -> bool:
        """Check if the last classified intent is a known answer (not default)."""
        intent = getattr(self, "_classified_intent", None)
        if not intent:
            return False
        return bool(intent != "default")

    def _increment_question_count(self) -> bool:
        """Increment question count and check if max reached.

        Returns:
            True if can continue, False if max questions reached.
        """
        self._flow_state.question_count += 1
        can_continue = self._flow_state.question_count < self._flow_state.max_questions

        logger.debug(
            "ConversationFlow: question count %d/%d, can_continue=%s",
            self._flow_state.question_count,
            self._flow_state.max_questions,
            can_continue,
        )

        return can_continue

    # ------------------------------------------------------------------#
    # User Response Detection
    # ------------------------------------------------------------------#

    def _detect_user_response(self) -> UserResponse:
        """Detect the type of user response from transcription.

        Returns:
            UserResponse enum indicating the detected response type.
        """
        intent = getattr(self, "_classified_intent", None)

        if not intent:
            # Try text detection even if intent is None
            return self._detect_response_from_text()

        # Check for YES/NO intents
        if intent in ("yes_response", "affirmative"):
            return UserResponse.YES
        if intent in ("no_response", "negative"):
            return UserResponse.NO
        if intent in ("repeat_question", "repeat"):
            return UserResponse.REPEAT
        if intent in ("human_support", "support", "transfer"):
            return UserResponse.SUPPORT

        # If it's a known FAQ intent, it's a question
        if intent != "default":
            return UserResponse.QUESTION

        # Try to detect from transcription text directly
        return self._detect_response_from_text()

    def _detect_response_from_text(self) -> UserResponse:
        """Detect response type from raw transcription text."""
        transcription = self._get_transcription_text()
        if not transcription:
            return UserResponse.UNKNOWN

        text = transcription.lower().strip()

        # Persian and English YES patterns
        yes_patterns = [
            "بله",
            "آره",
            "آری",
            "بلی",
            "yes",
            "yeah",
            "yep",
            "sure",
            "ok",
            "okay",
            "درسته",
            "صحیح",
            "موافقم",
        ]

        # Persian and English NO patterns
        no_patterns = [
            "نه",
            "خیر",
            "نخیر",
            "no",
            "nope",
            "نمیخوام",
            "نمی‌خوام",
            "نمیخواهم",
            "نمی‌خواهم",
            "بی‌خیال",
        ]

        # Persian and English REPEAT patterns
        repeat_patterns = [
            "تکرار",
            "دوباره",
            "مجدد",
            "repeat",
            "again",
            "سوالم رو تکرار",
            "یکبار دیگه",
            "یک‌بار دیگه",
        ]

        # Persian and English SUPPORT patterns
        support_patterns = [
            "پشتیبانی",
            "پشتیبان",
            "کمک",
            "اپراتور",
            "نیروی انسانی",
            "support",
            "help",
            "operator",
            "human",
            "agent",
            "انتقال",
        ]

        for pattern in yes_patterns:
            if pattern in text:
                return UserResponse.YES

        for pattern in no_patterns:
            if pattern in text:
                return UserResponse.NO

        for pattern in repeat_patterns:
            if pattern in text:
                return UserResponse.REPEAT

        for pattern in support_patterns:
            if pattern in text:
                return UserResponse.SUPPORT

        # Default to QUESTION if text is long enough (likely a new question)
        if len(text) > 20:
            return UserResponse.QUESTION

        return UserResponse.UNKNOWN

    def _get_transcription_text(self) -> Optional[str]:
        """Get the current transcription text."""
        asr_chunk_texts = getattr(self, "_asr_chunk_texts", [])
        asr_lock = getattr(self, "_asr_lock", None)

        try:
            if asr_lock is not None:
                with asr_lock:
                    if asr_chunk_texts:
                        return " ".join(t for t in asr_chunk_texts if t).strip()
            else:
                if asr_chunk_texts:
                    return " ".join(t for t in asr_chunk_texts if t).strip()
        except Exception:
            pass

        return None

    # ------------------------------------------------------------------#
    # Audio Playback
    # ------------------------------------------------------------------#

    def _play_prompt(self, audio_key: str) -> bool:
        """Play a prompt audio file.

        Args:
            audio_key: Key from AUDIO_FILES dict

        Returns:
            True if playback started successfully.
        """
        # Prevent duplicate playback if prompt is already playing
        if self._flow_state.prompt_player is not None:
            logger.debug(
                "ConversationFlow: prompt already active, skipping %s", audio_key
            )
            return False

        audio_path = self._get_audio_path(audio_key)
        if not audio_path:
            return False

        if not self._call_media:
            logger.warning("ConversationFlow: no call media available")
            return False

        try:
            import pjsua2 as pj

            from ...utils import get_wav_duration

            # Get duration
            duration = get_wav_duration(audio_path)
            if duration is None:
                duration = 3.0  # fallback

            # Create and start player
            self._flow_state.prompt_player = pj.AudioMediaPlayer()
            self._flow_state.prompt_player.createPlayer(
                audio_path, pj.PJMEDIA_FILE_NO_LOOP
            )
            self._flow_state.prompt_player.startTransmit(self._call_media)

            # Also transmit to mixed recorder
            if self._mixed_recorder:
                try:
                    self._flow_state.prompt_player.startTransmit(self._mixed_recorder)
                except Exception:
                    pass

            # Notify VAD
            if self._vad and getattr(self._vad, "available", False):
                try:
                    self._vad.set_bot_playback_state(True, time.time)
                except Exception:
                    pass

            # Start bot playback tracking
            if hasattr(self, "_start_bot_playback_tracking"):
                try:
                    self._start_bot_playback_tracking()
                except Exception:
                    pass

            self._flow_state.prompt_start_time = time.time()
            self._flow_state.prompt_stop_time = time.time() + duration
            self._flow_state.prompt_finished = False

            logger.info(
                "ConversationFlow: playing prompt '%s' (%.2fs)",
                audio_key,
                duration,
            )

            self._collect_event(
                event_type="prompt_playback_started",
                audio_key=audio_key,
                duration=duration,
            )

            return True

        except Exception as e:
            logger.error("ConversationFlow: error playing prompt: %s", e, exc_info=True)
            return False

    def _check_prompt_finished(self) -> bool:
        """Check if the current prompt has finished playing.

        Returns:
            True if prompt finished or not playing.
        """
        if self._flow_state.prompt_finished:
            return True

        if not self._flow_state.prompt_stop_time:
            return True

        if time.time() < self._flow_state.prompt_stop_time:
            return False

        # Prompt finished - clean up
        self._cleanup_prompt_player()
        return True

    def _cleanup_prompt_player(self) -> None:
        """Clean up the prompt player."""
        if not self._flow_state.prompt_player:
            return

        try:
            # Stop transmissions
            if self._call_media:
                try:
                    self._flow_state.prompt_player.stopTransmit(self._call_media)
                except Exception:
                    pass

            if self._mixed_recorder:
                try:
                    self._flow_state.prompt_player.stopTransmit(self._mixed_recorder)
                except Exception:
                    pass

        except Exception as e:
            logger.warning("ConversationFlow: error cleaning up player: %s", e)

        # Notify VAD
        if self._vad and getattr(self._vad, "available", False):
            try:
                self._vad.set_bot_playback_state(False, time.time)
            except Exception:
                pass

        # Stop bot playback tracking
        if hasattr(self, "_stop_bot_playback_tracking"):
            try:
                self._stop_bot_playback_tracking()
            except Exception:
                pass

        self._flow_state.prompt_player = None
        self._flow_state.prompt_finished = True
        self._flow_state.prompt_stop_time = None

        logger.debug("ConversationFlow: prompt player cleaned up")

    # ------------------------------------------------------------------#
    # State Machine Handlers
    # ------------------------------------------------------------------#

    def _handle_conversation_flow(self) -> bool:
        """Main state machine handler. Called from playback monitor.

        Dispatches to the satisfaction-flow handler when `flow_mode` is
        `"satisfaction"`, otherwise to the legacy handler.

        Returns:
            True if conversation is still ongoing, False if call should end.
        """
        if self._flow_mode() == "satisfaction":
            return self._handle_satisfaction_flow()
        return self._handle_legacy_flow()

    def _handle_legacy_flow(self) -> bool:
        """Original 'any other questions?' + repeat_or_support state machine."""
        state = self._flow_state.current_state

        if state == ConversationState.WAITING_FOR_QUESTION:
            return self._handle_waiting_for_question()

        elif state == ConversationState.PROCESSING_QUESTION:
            return self._handle_processing_question()

        elif state == ConversationState.PLAYING_ANSWER:
            return self._handle_playing_answer()

        elif state == ConversationState.PLAYING_FOLLOWUP_PROMPT:
            return self._handle_playing_followup_prompt()

        elif state == ConversationState.WAITING_FOR_FOLLOWUP_RESPONSE:
            return self._handle_waiting_for_followup_response()

        elif state == ConversationState.PLAYING_FALLBACK_PROMPT:
            return self._handle_playing_fallback_prompt()

        elif state == ConversationState.WAITING_FOR_FALLBACK_RESPONSE:
            return self._handle_waiting_for_fallback_response()

        elif state == ConversationState.PLAYING_ASK_NEXT_QUESTION:
            return self._handle_playing_ask_next_question()

        elif state == ConversationState.TRANSFERRING_TO_SUPPORT:
            return self._handle_transferring_to_support()

        elif state == ConversationState.MAX_RETRIES_REACHED:
            return self._handle_max_retries_reached()

        elif state == ConversationState.ENDING_CALL:
            return False  # Signal to end call

        return True

    def _handle_waiting_for_question(self) -> bool:
        """Handle WAITING_FOR_QUESTION state."""
        # This state waits for ASR to complete with a question
        if getattr(self, "_asr_complete", False):
            self._transition_to(ConversationState.PROCESSING_QUESTION)
        return True

    def _handle_processing_question(self) -> bool:
        """Handle PROCESSING_QUESTION state."""
        # Check if intent classification is complete
        if not getattr(self, "_intent_classified", False):
            return True

        # Increment question count
        self._increment_question_count()

        if self._is_known_answer():
            # Bot knows the answer - play it
            self._transition_to(ConversationState.PLAYING_ANSWER)
        else:
            # Bot doesn't know - ask if user wants to repeat or get support
            self._transition_to(ConversationState.PLAYING_FALLBACK_PROMPT)
            if not self._play_prompt("repeat_or_support"):
                # Audio failed, go to ending
                self._transition_to(ConversationState.ENDING_CALL)

        return True

    def _handle_playing_answer(self) -> bool:
        """Handle PLAYING_ANSWER state."""
        # Wait for intent response to finish playing
        if not getattr(self, "_intent_response_finished", False):
            return True

        # Check if we can ask more questions
        if self._flow_state.question_count >= self._flow_state.max_questions:
            # Max questions reached
            self._transition_to(ConversationState.ENDING_CALL)
            self._play_goodbye_message()
            return True

        # Play "Any other questions?" prompt
        self._transition_to(ConversationState.PLAYING_FOLLOWUP_PROMPT)
        if not self._play_prompt("any_other_questions"):
            self._transition_to(ConversationState.ENDING_CALL)

        return True

    def _handle_playing_followup_prompt(self) -> bool:
        """Handle PLAYING_FOLLOWUP_PROMPT state."""
        if not self._check_prompt_finished():
            return True

        # Prompt finished, wait for user response
        self._reset_asr_for_new_input()

        # Explicitly set the listening start time
        try:
            current_time = time.time()
            time_state = getattr(self, "_time_state", None)
            if time_state:
                time_state.welcome_finished_time = current_time
            self._welcome_finished_time = current_time
        except Exception:
            pass

        self._transition_to(ConversationState.WAITING_FOR_FOLLOWUP_RESPONSE)
        self._flow_state.waiting_for_user_since = time.time()
        return True

    def _handle_waiting_for_followup_response(self) -> bool:
        """Handle WAITING_FOR_FOLLOWUP_RESPONSE state."""
        if not getattr(self, "_asr_complete", False):
            return True

        response = self._detect_user_response()
        logger.info("ConversationFlow: detected response: %s", response.value)

        if response == UserResponse.YES:
            # User wants another question
            self._transition_to(ConversationState.PLAYING_ASK_NEXT_QUESTION)
            if not self._play_prompt("ask_next_question"):
                self._transition_to(ConversationState.ENDING_CALL)

        elif response == UserResponse.NO:
            # User is done
            self._transition_to(ConversationState.ENDING_CALL)
            self._play_goodbye_message()

        elif response == UserResponse.QUESTION:
            # User asked a new question directly
            # Check if it's the same question as before (likely ASR issue)
            current_intent = getattr(self, "_classified_intent", None)
            last_intent = getattr(self._flow_state, "last_intent", None)

            if current_intent and last_intent and current_intent == last_intent:
                # Same question detected - likely ASR didn't capture new speech
                # Treat as UNKNOWN/NO to end the call gracefully
                logger.info("ConversationFlow: same question detected, treating as NO")
                self._transition_to(ConversationState.ENDING_CALL)
                self._play_goodbye_message()
            else:
                # New question - process it
                self._transition_to(ConversationState.PROCESSING_QUESTION)

        elif response == UserResponse.REPEAT:
            # User wants to repeat/ask again - allow them to ask the next question
            self._transition_to(ConversationState.PLAYING_ASK_NEXT_QUESTION)
            if not self._play_prompt("ask_next_question"):
                self._transition_to(ConversationState.ENDING_CALL)

        elif response == UserResponse.SUPPORT:
            # User wants support
            self._transition_to(ConversationState.TRANSFERRING_TO_SUPPORT)
            self._play_prompt("transferring_to_support")

        else:
            # Unknown response - treat as NO
            logger.info("ConversationFlow: unknown response, treating as NO")
            self._transition_to(ConversationState.ENDING_CALL)
            self._play_goodbye_message()

        return True

    def _handle_playing_fallback_prompt(self) -> bool:
        """Handle PLAYING_FALLBACK_PROMPT state."""
        if not self._check_prompt_finished():
            return True

        # Prompt finished, wait for user response
        self._reset_asr_for_new_input()

        # Explicitly set the listening start time
        try:
            current_time = time.time()
            time_state = getattr(self, "_time_state", None)
            if time_state:
                time_state.welcome_finished_time = current_time
            self._welcome_finished_time = current_time
        except Exception:
            pass

        self._transition_to(ConversationState.WAITING_FOR_FALLBACK_RESPONSE)
        self._flow_state.waiting_for_user_since = time.time()
        return True

    def _handle_waiting_for_fallback_response(self) -> bool:
        """Handle WAITING_FOR_FALLBACK_RESPONSE state."""
        if not getattr(self, "_asr_complete", False):
            return True

        response = self._detect_user_response()
        logger.info("ConversationFlow: detected fallback response: %s", response.value)

        if response == UserResponse.REPEAT:
            # User wants to ask again
            if self._flow_state.question_count >= self._flow_state.max_questions:
                self._transition_to(ConversationState.MAX_RETRIES_REACHED)
                self._play_prompt("max_retries_reached")
            else:
                self._transition_to(ConversationState.PLAYING_ASK_NEXT_QUESTION)
                if not self._play_prompt("ask_next_question"):
                    self._transition_to(ConversationState.ENDING_CALL)

        elif response == UserResponse.SUPPORT:
            # User wants human support
            self._transition_to(ConversationState.TRANSFERRING_TO_SUPPORT)
            self._play_prompt("transferring_to_support")

        elif response == UserResponse.QUESTION:
            # User asked a new question directly
            self._transition_to(ConversationState.PROCESSING_QUESTION)

        else:
            # Unknown response - transfer to support as fallback
            logger.info("ConversationFlow: unknown fallback response, transferring")
            self._transition_to(ConversationState.TRANSFERRING_TO_SUPPORT)
            self._play_prompt("transferring_to_support")

        return True

    def _handle_playing_ask_next_question(self) -> bool:
        """Handle PLAYING_ASK_NEXT_QUESTION state."""
        if not self._check_prompt_finished():
            return True

        # Prompt finished, wait for next question
        self._reset_asr_for_new_input()

        # Explicitly set the listening start time
        try:
            current_time = time.time()
            time_state = getattr(self, "_time_state", None)
            if time_state:
                time_state.welcome_finished_time = current_time
            self._welcome_finished_time = current_time
        except Exception:
            pass

        self._transition_to(ConversationState.WAITING_FOR_QUESTION)
        return True

    def _handle_transferring_to_support(self) -> bool:
        """Handle TRANSFERRING_TO_SUPPORT state."""
        if not self._check_prompt_finished():
            return True

        # Transfer complete - perform the actual transfer
        self._perform_support_transfer()
        self._transition_to(ConversationState.ENDING_CALL)
        return False

    def _handle_max_retries_reached(self) -> bool:
        """Handle MAX_RETRIES_REACHED state."""
        if not self._check_prompt_finished():
            return True

        self._transition_to(ConversationState.ENDING_CALL)
        self._play_goodbye_message()
        return True

    # ------------------------------------------------------------------#
    # Support Methods
    # ------------------------------------------------------------------#

    def _reset_asr_for_new_input(self) -> None:
        """Reset ASR state for new user input."""
        # Clear ASR completion flag
        self._asr_complete = False

        # When conversation flow is enabled, we want intent classification to be
        # per user turn (question / follow‑up), not cached for the whole call.
        # Safely reset intent flags so that the next ASR completion can be
        # classified independently based on the new utterance.
        if (
            hasattr(self, "_is_conversation_flow_enabled")
            and self._is_conversation_flow_enabled()
        ):
            # Preserve last intent on the flow state for analytics if needed
            if hasattr(self, "_flow_state"):
                try:
                    self._flow_state.last_intent = getattr(
                        self, "_classified_intent", None
                    )
                    self._flow_state.last_confidence = getattr(
                        self, "_intent_confidence", 0.0
                    )
                except Exception:
                    pass

            try:
                self._intent_classified = False
                self._classified_intent = None
                self._intent_confidence = 0.0
                # Keep _classified_faq_config for call record if present

                # Reset intent response flags for next turn
                self._intent_response_played = False
                self._intent_response_finished = False
            except Exception:
                # If any attribute is missing, ignore – this is best‑effort
                pass

        # Clear transcription texts
        asr_chunk_texts = getattr(self, "_asr_chunk_texts", None)
        asr_lock = getattr(self, "_asr_lock", None)

        if asr_chunk_texts is not None:
            try:
                if asr_lock is not None:
                    with asr_lock:
                        asr_chunk_texts.clear()
                else:
                    asr_chunk_texts.clear()
            except Exception:
                pass

        # NOTE: Do NOT reset _last_transcribed_chunk_count here.
        # The VAD chunk list is cumulative during the call. If we reset the count to 0,
        # the PlaybackMonitor will think it needs to process all previous chunks again,
        # leading to re-transcription of old questions.
        # By keeping the count as-is, we ensure we only process NEW chunks that arrive
        # after this reset.
        if hasattr(self, "_asr_chunk_offset") and hasattr(
            self, "_last_transcribed_chunk_count"
        ):
            self._asr_chunk_offset = self._last_transcribed_chunk_count

        # Reset TimeState to ensure we don't accidentally use old hangup times
        # from the previous turn.
        # We also reset welcome_finished_time so that it gets re-initialized
        # to the current time (checking "silence after prompt" from NOW).
        try:
            # Clear attributes first to prevent resurrection during sync
            self._hangup_time = None
            self._welcome_finished_time = None
            self._stop_player_time = None

            time_state = getattr(self, "_time_state", None)
            if time_state:
                time_state.hangup_time = None
                time_state.welcome_finished_time = None
                time_state.stop_player_time = None
        except Exception:
            pass

        # NOTE: Do NOT reset intent classification here. It is historical
        # call data preserved for the call record. Only reset at new call
        # start, not when resetting ASR for new input within the same call.

        # Reset VAD chunks if available
        if self._vad and hasattr(self._vad, "reset_chunks"):
            try:
                self._vad.reset_chunks()
            except Exception:
                pass

        logger.debug("ConversationFlow: ASR state reset for new input")

    def _perform_support_transfer(self) -> bool:
        """Perform the actual transfer to human support.

        Returns:
            True if the blind transfer was successfully *initiated* with
            PJSUA. False otherwise (no extension configured, no `xfer` method,
            or `xfer()` raised). A True return does NOT guarantee that the SIP
            transfer actually completed at the carrier — that requires hooking
            `onCallTransferStatus`, which is out of scope here.
        """
        transfer_extension = getattr(self._acc_ref, "support_transfer_extension", None)

        if not transfer_extension:
            logger.warning(
                "ConversationFlow: no support transfer extension configured"
            )
            return False

        logger.info(
            "ConversationFlow: transferring call to support extension: %s",
            transfer_extension,
        )

        self._collect_event(
            event_type="call_transferred",
            transfer_type="human_support",
            target_extension=transfer_extension,
        )

        try:
            import pjsua2 as pj

            domain = getattr(self._acc_ref, "domain", "localhost")
            dest_uri = f"sip:{transfer_extension}@{domain}"

            prm = pj.CallOpParam()
            prm.options = pj.PJSUA_XFER_NO_REQUIRE_REPLACES

            if hasattr(self, "xfer"):
                self.xfer(dest_uri, prm)
                logger.info(
                    "ConversationFlow: blind transfer initiated to %s", dest_uri
                )
                return True

            logger.warning("ConversationFlow: xfer method not available")
            return False

        except Exception as e:
            logger.error(
                "ConversationFlow: error performing transfer: %s", e, exc_info=True
            )
            return False

    def _is_conversation_flow_enabled(self) -> bool:
        """Check if conversation flow is enabled."""
        return getattr(self._acc_ref, "enable_conversation_flow", True)

    def _should_play_intent_audio_now(self) -> bool:
        """Whether `_play_intent_response()` may run right now.

        In the legacy flow, intent-driven answer playback is always allowed.
        In the satisfaction flow, an FAQ answer is only expected while we are
        transitioning out of `PROCESSING_QUESTION` toward `PLAYING_ANSWER`.

        When the bot is awaiting / re-prompting a satisfaction reply (or any
        terminal state) the intent classifier may still be running in the
        background, but we MUST NOT play another FAQ answer on top of the
        satisfaction prompt — that produces audible audio collisions on the
        caller's line.
        """
        if not self._is_conversation_flow_enabled():
            return True

        if self._flow_mode() != "satisfaction":
            return True

        state = getattr(self._flow_state, "current_state", None)
        return state == ConversationState.PROCESSING_QUESTION

    # ------------------------------------------------------------------#
    # Satisfaction Flow State Machine
    # ------------------------------------------------------------------#

    def _handle_satisfaction_flow(self) -> bool:
        """Dispatcher for the new question → answer → satisfaction → retry flow.

        Returns:
            True if conversation is still ongoing, False if call should end.
        """
        # If the caller has already hung up, do not drive any further state
        # transitions or schedule prompt playback into a torn-down call. The
        # PJSUA call object is no longer usable for audio at this point, so
        # any `_play_prompt()` call would either fail silently or surface as
        # "Remove port failed" / "Not a valid WAVE file" diagnostics in the
        # log. Finalize the resolution as `hangup_no_answer` if we hadn't
        # already reached a terminal state.
        if hasattr(self, "_is_call_active") and not self._is_call_active():
            state = self._flow_state.current_state
            if state != ConversationState.ENDING_CALL:
                if self._flow_state.resolution is None:
                    self._sat_finalize_resolution("hangup_no_answer")
                self._transition_to(ConversationState.ENDING_CALL)
            return False

        state = self._flow_state.current_state

        if state == ConversationState.WAITING_FOR_QUESTION:
            return self._sat_handle_waiting_for_question()

        if state == ConversationState.PROCESSING_QUESTION:
            return self._sat_handle_processing_question()

        if state == ConversationState.PLAYING_ANSWER:
            return self._sat_handle_playing_answer()

        if state == ConversationState.PLAYING_SATISFACTION_PROMPT:
            return self._sat_handle_playing_satisfaction_prompt()

        if state == ConversationState.AWAITING_SATISFACTION:
            return self._sat_handle_awaiting_satisfaction()

        if state == ConversationState.PLAYING_RETRY_PROMPT:
            return self._sat_handle_playing_retry_prompt()

        if state == ConversationState.PLAYING_THANK_YOU:
            return self._sat_handle_playing_thank_you()

        if state == ConversationState.PLAYING_ESCALATION:
            return self._sat_handle_playing_escalation()

        if state == ConversationState.ESCALATING:
            return self._sat_handle_escalating()

        if state == ConversationState.ENDING_CALL:
            return False

        return True

    # ---- Helpers ------------------------------------------------------#

    def _sat_current_turn(self) -> Optional[Turn]:
        """Return the most recently appended turn, or None if no turns yet."""
        if not self._flow_state.turns:
            return None
        return self._flow_state.turns[-1]

    def _sat_finalize_resolution(
        self,
        resolution: Resolution,
        *,
        escalation_succeeded: Optional[bool] = None,
        escalation_failed: bool = False,
    ) -> None:
        """Record the call's final resolution on the flow state."""
        self._flow_state.resolution = resolution
        self._flow_state.escalation_succeeded = escalation_succeeded
        self._flow_state.escalation_failed = escalation_failed
        self._collect_event(
            event_type="satisfaction_flow_resolved",
            resolution=resolution,
            retry_count=self._flow_state.retry_count,
            escalation_succeeded=escalation_succeeded,
            escalation_failed=escalation_failed,
        )

    def _sat_reset_listening(self) -> None:
        """Reset ASR and time state at the entry to a listening state."""
        self._reset_asr_for_new_input()
        try:
            current_time = time.time()
            time_state = getattr(self, "_time_state", None)
            if time_state:
                time_state.welcome_finished_time = current_time
            self._welcome_finished_time = current_time
        except Exception:
            pass
        self._flow_state.waiting_for_user_since = time.time()

    def _classify_satisfaction_reply(
        self, response: "UserResponse"
    ) -> Literal["yes", "no", "unclear"]:
        """Map a generic `UserResponse` onto a satisfaction-specific outcome.

        Returns one of:
        - `"yes"`: caller affirmed the answer resolved their question
        - `"no"`: caller explicitly said the answer did not help (or the
          equivalent NO keywords)
        - `"unclear"`: anything else (silence, off-topic, support / repeat
          requests). The caller of this method is responsible for deciding
          whether an `"unclear"` outcome triggers a within-turn re-prompt or
          should be treated as `"no"` (e.g. after the ambiguous-reply budget
          is exhausted).
        """
        if response == UserResponse.YES:
            return "yes"
        if response == UserResponse.NO:
            return "no"
        return "unclear"

    # ---- Handlers -----------------------------------------------------#

    def _sat_handle_waiting_for_question(self) -> bool:
        """Listen for the caller's next question."""
        if getattr(self, "_asr_complete", False):
            self._transition_to(ConversationState.PROCESSING_QUESTION)
        return True

    def _sat_handle_processing_question(self) -> bool:
        """Wait for intent classification, then start playing the answer.

        Unlike the legacy flow, an unrecognised intent (`default`) is NOT
        diverted to a `repeat_or_support` branch — the bot simply plays the
        configured fallback answer audio (e.g. `faq_default.wav`) and then
        proceeds to the satisfaction check, where the caller can answer NO
        to trigger a retry.

        Control intents (`yes_response`, `no_response`, `repeat_question`,
        `human_support`) have no answer audio and would otherwise stall the
        state machine forever, so they are rerouted to the `default` answer
        as a safe fallback.
        """
        if not getattr(self, "_intent_classified", False):
            return True

        intent = getattr(self, "_classified_intent", None)
        confidence = getattr(self, "_intent_confidence", 0.0)
        question_text = self._get_transcription_text()
        faq_config = getattr(self, "_classified_faq_config", None) or {}

        is_control_intent = (
            isinstance(faq_config, dict)
            and bool(faq_config.get("is_control_intent", False))
        )
        if is_control_intent:
            logger.info(
                "ConversationFlow: control intent '%s' received as a question; "
                "falling back to default answer",
                intent,
            )
            from pjsua_bot.intent.faq_config import FAQS

            intent = "default"
            faq_config = FAQS.get("default", {})
            self._classified_intent = intent
            self._classified_faq_config = faq_config
            self._intent_response_played = False
            self._intent_response_finished = False
            try:
                self._play_intent_response()
            except Exception as exc:
                logger.warning(
                    "ConversationFlow: error invoking default answer playback: %s",
                    exc,
                )

        answer_audio = (
            faq_config.get("response_audio") if isinstance(faq_config, dict) else None
        )

        turn = Turn(
            index=len(self._flow_state.turns),
            question=question_text,
            intent=intent,
            intent_confidence=(
                round(float(confidence), 3) if confidence is not None else None
            ),
            answer_audio=answer_audio,
            classification_failed=intent is None,
        )
        self._flow_state.turns.append(turn)
        self._flow_state.last_intent = intent
        self._flow_state.last_confidence = float(confidence or 0.0)

        self._transition_to(ConversationState.PLAYING_ANSWER)
        return True

    def _sat_handle_playing_answer(self) -> bool:
        """Wait for the intent response audio to finish, then prompt for satisfaction.

        Entering the satisfaction prompt from a fresh per-turn answer resets
        the within-turn ambiguous-reply counter so the caller is granted one
        fresh re-prompt budget per question.
        """
        if not getattr(self, "_intent_response_finished", False):
            return True

        self._flow_state.satisfaction_ambiguous_retries = 0

        if not self._play_prompt("satisfaction_prompt"):
            logger.warning(
                "ConversationFlow: satisfaction prompt unavailable, "
                "skipping straight to thank-you"
            )
            self._sat_finalize_resolution("hangup_no_answer")
            self._transition_to(ConversationState.ENDING_CALL)
            self._mark_goodbye_finished_safely()
            return True

        self._transition_to(ConversationState.PLAYING_SATISFACTION_PROMPT)
        return True

    def _sat_handle_playing_satisfaction_prompt(self) -> bool:
        """Wait for the satisfaction prompt to finish, then listen for YES/NO.

        Note: this state is entered both on the first satisfaction prompt of
        a turn AND on the ambiguous-reply re-prompt within the same turn, so
        we must NOT reset `satisfaction_ambiguous_retries` here — that
        invariant is enforced by `_sat_handle_playing_answer` at fresh-turn
        boundaries instead.
        """
        if not self._check_prompt_finished():
            return True

        self._sat_reset_listening()
        self._transition_to(ConversationState.AWAITING_SATISFACTION)
        return True

    def _sat_handle_awaiting_satisfaction(self) -> bool:
        """Classify the caller's reply as YES / NO / unclear and branch."""
        if not getattr(self, "_asr_complete", False):
            return True

        response = self._detect_user_response()
        outcome = self._classify_satisfaction_reply(response)
        logger.info(
            "ConversationFlow: satisfaction outcome=%s (raw=%s, "
            "retry_count=%d/%d, ambiguous_retries=%d)",
            outcome,
            response.value,
            self._flow_state.retry_count,
            self._flow_state.max_satisfaction_retries,
            self._flow_state.satisfaction_ambiguous_retries,
        )

        if outcome == "yes":
            turn = self._sat_current_turn()
            if turn is not None:
                turn.satisfaction = "yes"
            self._sat_finalize_resolution("resolved")
            self._transition_to(ConversationState.PLAYING_THANK_YOU)
            if not self._play_prompt("thank_you"):
                self._transition_to(ConversationState.ENDING_CALL)
                self._mark_goodbye_finished_safely()
            return True

        # Unclear: re-play satisfaction prompt at most once, otherwise treat as NO.
        if (
            outcome == "unclear"
            and self._flow_state.satisfaction_ambiguous_retries == 0
        ):
            self._flow_state.satisfaction_ambiguous_retries += 1
            logger.info(
                "ConversationFlow: unclear satisfaction reply, "
                "re-playing satisfaction prompt"
            )
            if self._play_prompt("satisfaction_prompt"):
                self._transition_to(ConversationState.PLAYING_SATISFACTION_PROMPT)
                return True
            # Audio failed; fall through and treat as NO below.

        # Definitive NO (or second unclear reply): record dissatisfaction.
        turn = self._sat_current_turn()
        if turn is not None:
            turn.satisfaction = "no" if outcome == "no" else "unclear"

        if self._flow_state.retry_count >= self._flow_state.max_satisfaction_retries:
            # Retry budget exhausted -> escalate.
            self._transition_to(ConversationState.PLAYING_ESCALATION)
            if not self._play_prompt("escalation_announcement"):
                # Announcement unavailable: skip straight to ESCALATING so
                # the actual transfer / hangup still happens.
                self._transition_to(ConversationState.ESCALATING)
            return True

        # Budget remaining -> consume one retry and re-ask for a question.
        self._flow_state.retry_count += 1
        self._transition_to(ConversationState.PLAYING_RETRY_PROMPT)
        if not self._play_prompt("try_again_prompt"):
            # If the retry prompt is missing, still try to re-listen.
            self._sat_reset_listening()
            self._transition_to(ConversationState.WAITING_FOR_QUESTION)
        return True

    def _sat_handle_playing_retry_prompt(self) -> bool:
        """Wait for the 'let's try again' prompt to finish, then re-listen."""
        if not self._check_prompt_finished():
            return True
        self._sat_reset_listening()
        self._transition_to(ConversationState.WAITING_FOR_QUESTION)
        return True

    def _sat_handle_playing_thank_you(self) -> bool:
        """Wait for the thank-you prompt to finish, then hang up."""
        if not self._check_prompt_finished():
            return True
        self._transition_to(ConversationState.ENDING_CALL)
        self._mark_goodbye_finished_safely()
        return True

    def _sat_handle_playing_escalation(self) -> bool:
        """Wait for the escalation announcement to finish, then escalate."""
        if not self._check_prompt_finished():
            return True
        self._transition_to(ConversationState.ESCALATING)
        return True

    def _sat_handle_escalating(self) -> bool:
        """Perform the blind transfer, or play goodbye+hangup if not configured.

        The escalation announcement WAV has already been played by the time
        this state runs. In every branch the goodbye prompt (`goodbye_file`)
        is played before the call closes so the caller is not left in silence
        if anything goes wrong with the transfer.
        """
        transfer_extension = getattr(
            self._acc_ref, "support_transfer_extension", None
        )

        if not transfer_extension:
            logger.warning(
                "ConversationFlow: escalation requested but no "
                "support_transfer_extension is configured; playing goodbye "
                "and hanging up"
            )
            self._sat_finalize_resolution(
                "hangup_no_answer",
                escalation_succeeded=False,
                escalation_failed=True,
            )
            self._transition_to(ConversationState.ENDING_CALL)
            try:
                self._play_goodbye_message()
            except Exception as exc:
                logger.warning(
                    "ConversationFlow: error playing goodbye after escalation "
                    "fallback: %s",
                    exc,
                )
                self._mark_goodbye_finished_safely()
            return True

        try:
            transfer_initiated = self._perform_support_transfer()
        except Exception as exc:
            logger.error(
                "ConversationFlow: unexpected error initiating transfer: %s",
                exc,
                exc_info=True,
            )
            transfer_initiated = False

        if transfer_initiated:
            self._sat_finalize_resolution(
                "escalated",
                escalation_succeeded=True,
            )
            self._transition_to(ConversationState.ENDING_CALL)
            return False

        # Transfer failed to start — keep `resolution=escalated` (the
        # operator attempted escalation) but flag it as a failure and play
        # the goodbye before hanging up so the caller hears a clean closure.
        self._sat_finalize_resolution(
            "escalated",
            escalation_succeeded=False,
        )
        self._transition_to(ConversationState.ENDING_CALL)
        try:
            self._play_goodbye_message()
        except Exception as exc:
            logger.warning(
                "ConversationFlow: error playing goodbye after failed "
                "transfer: %s",
                exc,
            )
            self._mark_goodbye_finished_safely()
        return True

    # ---- Helpers ------------------------------------------------------#

    def _mark_goodbye_finished_safely(self) -> None:
        """Trigger hangup gating via the goodbye state without re-playing audio.

        The bot's hangup loop (`PlaybackMonitorMixin.should_hangup`) keys off
        `_goodbye_playback_finished` and `_hangup_time`. We have already
        played our own terminal prompt (thank-you, escalation announcement,
        or fall-through goodbye), so we directly mark the goodbye state as
        finished to schedule the hangup.
        """
        try:
            if hasattr(self, "_mark_goodbye_finished"):
                self._mark_goodbye_finished()
            else:
                self._goodbye_playback_finished = True
                self._hangup_time = time.time() + 0.5
        except Exception as exc:
            logger.warning(
                "ConversationFlow: error marking goodbye finished: %s", exc
            )
