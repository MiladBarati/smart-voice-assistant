"""Conversation flow state machine for multi-turn dialogues."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """States in the conversation flow state machine."""

    # Initial state - waiting for user's first question
    WAITING_FOR_QUESTION = "waiting_for_question"

    # Processing user's question (ASR/intent classification)
    PROCESSING_QUESTION = "processing_question"

    # Playing FAQ response (bot knows the answer)
    PLAYING_ANSWER = "playing_answer"

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

    # Playing goodbye and ending call
    ENDING_CALL = "ending_call"

    # Max follow-up questions reached
    MAX_RETRIES_REACHED = "max_retries_reached"


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
    max_questions: int = 3  # 1 initial + 2 follow-ups
    last_intent: Optional[str] = None
    last_confidence: float = 0.0
    prompt_player: Any = None
    prompt_start_time: Optional[float] = None
    prompt_stop_time: Optional[float] = None
    prompt_finished: bool = False
    waiting_for_user_since: Optional[float] = None


# Audio file paths (relative to project root)
AUDIO_FILES = {
    "any_other_questions": "assets/audio/any_other_questions.wav",
    "ask_next_question": "assets/audio/ask_next_question.wav",
    "repeat_or_support": "assets/audio/repeat_or_support.wav",
    "transferring_to_support": "assets/audio/transferring_to_support.wav",
    "max_retries_reached": "assets/audio/max_retries_reached.wav",
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

    if TYPE_CHECKING:
        def _play_goodbye_message(self) -> None: ...
        def _start_bot_playback_tracking(self) -> None: ...
        def _stop_bot_playback_tracking(self) -> None: ...
        def isActive(self) -> bool: ...

    # ------------------------------------------------------------------#
    # Initialization
    # ------------------------------------------------------------------#

    def _init_conversation_flow_state(self) -> None:
        """Initialize conversation flow state."""
        self._flow_state = ConversationFlowState()
        self._flow_state.max_questions = getattr(
            self._acc_ref, "max_followup_questions", 2
        ) + 1  # +1 for initial question

        # Get project root for audio file paths
        self._project_root = self._get_project_root()

        logger.info(
            "ConversationFlow: initialized with max_questions=%d",
            self._flow_state.max_questions,
        )

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
        return intent != "default"

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
            "بله", "آره", "آری", "بلی", "yes", "yeah", "yep", "sure", "ok", "okay",
            "درسته", "صحیح", "موافقم",
        ]

        # Persian and English NO patterns
        no_patterns = [
            "نه", "خیر", "نخیر", "no", "nope", "نمیخوام", "نمی‌خوام",
            "نمیخواهم", "نمی‌خواهم", "بی‌خیال",
        ]

        # Persian and English REPEAT patterns
        repeat_patterns = [
            "تکرار", "دوباره", "مجدد", "repeat", "again", "سوالم رو تکرار",
            "یکبار دیگه", "یک‌بار دیگه",
        ]

        # Persian and English SUPPORT patterns
        support_patterns = [
            "پشتیبانی", "پشتیبان", "کمک", "اپراتور", "نیروی انسانی",
            "support", "help", "operator", "human", "agent", "انتقال",
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
        if len(text) > 10:
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
            logger.debug("ConversationFlow: prompt player already active, skipping playback of %s", audio_key)
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

        Returns:
            True if conversation is still ongoing, False if call should end.
        """
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
        can_continue = self._increment_question_count()

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
        if hasattr(self, "_is_conversation_flow_enabled") and self._is_conversation_flow_enabled():
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

        # NOTE: Do NOT reset intent classification here. Intent classification is historical
        # call data that must be preserved for the call record. It should only be reset
        # at the start of a new call, not when resetting ASR for new input within the same call.
        # The intent classification represents what the user asked during this call and should
        # be included in the final call record even if we're preparing for additional input.

        # Reset VAD chunks if available
        if self._vad and hasattr(self._vad, "reset_chunks"):
            try:
                self._vad.reset_chunks()
            except Exception:
                pass

        logger.debug("ConversationFlow: ASR state reset for new input")

    def _perform_support_transfer(self) -> None:
        """Perform the actual transfer to human support."""
        transfer_extension = getattr(self._acc_ref, "support_transfer_extension", None)

        if not transfer_extension:
            logger.warning(
                "ConversationFlow: no support transfer extension configured"
            )
            return

        logger.info(
            "ConversationFlow: transferring call to support extension: %s",
            transfer_extension,
        )

        self._collect_event(
            event_type="call_transferred",
            transfer_type="human_support",
            target_extension=transfer_extension,
        )

        # Perform blind transfer
        try:
            import pjsua2 as pj

            # Build transfer destination URI
            domain = getattr(self._acc_ref, "domain", "localhost")
            dest_uri = f"sip:{transfer_extension}@{domain}"

            # Create transfer parameters
            prm = pj.CallOpParam()
            prm.options = pj.PJSUA_XFER_NO_REQUIRE_REPLACES

            # Perform the transfer (assumes self is a pj.Call)
            if hasattr(self, "xfer"):
                self.xfer(dest_uri, prm)
                logger.info("ConversationFlow: blind transfer initiated to %s", dest_uri)
            else:
                logger.warning("ConversationFlow: xfer method not available")

        except Exception as e:
            logger.error(
                "ConversationFlow: error performing transfer: %s", e, exc_info=True
            )

    def _is_conversation_flow_enabled(self) -> bool:
        """Check if conversation flow is enabled."""
        return getattr(self._acc_ref, "enable_conversation_flow", True)
