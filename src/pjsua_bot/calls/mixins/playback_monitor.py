"""Playback monitoring and hangup logic extracted from `AnyCall`."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, cast

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """Playback lifecycle states."""

    NOT_STARTED = "not_started"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass
class IntentState:
    """Intent response playback state."""

    played: bool = False
    finished: bool = False
    player: Any | None = None
    enabled: bool = False


@dataclass
class GoodbyeState:
    """Goodbye message state."""

    requested: bool = False
    playback_started: bool = False
    playback_finished: bool = False
    file: str | None = None


@dataclass
class TimeState:
    """Time-based state tracking."""

    hangup_time: float | None = None
    stop_player_time: float | None = None
    welcome_finished_time: float | None = None
    last_asr_wait_log_time: float = 0.0


class PlaybackMonitorMixin:
    """Encapsulates playback completion, VAD-driven hangup, and ASR chunking."""

    # Attributes supplied by sibling mixins / host class (for type-checkers)
    _acc_ref: Any
    _player: Any | None
    _mixed_recorder: Any | None
    _call_media: Any | None
    _collect_event: Callable[..., None]
    _recording_file: str
    _silence_after_speech_sec: float
    _vad: Any | None
    _vad_called: bool

    _asr_enabled: bool
    _asr_available: bool
    _asr: Any | None
    _last_transcribed_chunk_count: int
    _start_asr_thread: Callable[[], None]
    _submit_transcription_task: Callable[[str, int], None]

    _asr_complete: bool

    if TYPE_CHECKING:

        def check_goodbye_status(self) -> None: ...

        def _play_goodbye_message(self) -> None: ...

        def check_intent_response_status(self) -> bool: ...

        def _classify_intent(self) -> tuple[str, float] | None: ...

        def _play_intent_response(self) -> None: ...

    # ------------------------------------------------------------------#
    # Initialization
    # ------------------------------------------------------------------#

    def _init_playback_state(self) -> None:
        """Initialise playback-related attributes."""
        self._player = None
        self._mixed_recorder = None
        self._call_media = None
        self._playback_state = PlaybackState.NOT_STARTED
        self._vad_called = False

        # Backward compatibility: maintain individual attributes
        self._playback_started = False
        self._playback_finished = False

        # Initialize state objects
        self._intent_state = IntentState()
        self._goodbye_state = GoodbyeState()
        self._time_state = TimeState()
        
        # ASR State
        self._asr_chunk_offset = 0

        # Sync state objects with individual attributes for backward compatibility
        self._sync_state_to_attributes()

    def _schedule_player_stop(self, delay_seconds: float) -> None:
        """Schedule player teardown after the specified delay."""
        time_state = self._get_time_state()
        time_state.stop_player_time = time.time() + delay_seconds
        # Sync to attribute for backward compatibility
        self._stop_player_time = time_state.stop_player_time

    # ------------------------------------------------------------------#
    # State access helpers
    # ------------------------------------------------------------------#

    def _is_call_active(self) -> bool:
        """Check if call is still active."""
        try:
            if hasattr(self, "isActive"):
                return bool(self.isActive())
        except Exception:
            pass
        return False

    def _get_intent_state(self) -> IntentState:
        """Get intent state, initializing from attributes if needed."""
        if not hasattr(self, "_intent_state"):
            # Fallback: build from individual attributes
            self._intent_state = IntentState(
                played=getattr(self, "_intent_response_played", False),
                finished=getattr(self, "_intent_response_finished", False),
                player=getattr(self, "_intent_response_player", None),
                enabled=getattr(self, "_intent_enabled", False),
            )
        else:
            # Sync from attributes in case they were updated externally
            self._intent_state.played = getattr(self, "_intent_response_played", False)
            self._intent_state.finished = getattr(
                self, "_intent_response_finished", False
            )
            self._intent_state.player = getattr(self, "_intent_response_player", None)
            self._intent_state.enabled = getattr(self, "_intent_enabled", False)
        return self._intent_state

    def _get_goodbye_state(self) -> GoodbyeState:
        """Get goodbye state, initializing from attributes if needed."""
        if not hasattr(self, "_goodbye_state"):
            # Fallback: build from individual attributes
            self._goodbye_state = GoodbyeState(
                requested=getattr(self, "_goodbye_requested", False),
                playback_started=getattr(self, "_goodbye_playback_started", False),
                playback_finished=getattr(self, "_goodbye_playback_finished", False),
                file=getattr(self._acc_ref, "goodbye_file", None),
            )
        else:
            # Sync from attributes in case they were updated externally
            self._goodbye_state.requested = getattr(self, "_goodbye_requested", False)
            self._goodbye_state.playback_started = getattr(
                self, "_goodbye_playback_started", False
            )
            self._goodbye_state.playback_finished = getattr(
                self, "_goodbye_playback_finished", False
            )
            self._goodbye_state.file = getattr(self._acc_ref, "goodbye_file", None)
        return self._goodbye_state

    def _get_time_state(self) -> TimeState:
        """Get time state, initializing if needed."""
        if not hasattr(self, "_time_state"):
            self._time_state = TimeState(
                hangup_time=getattr(self, "_hangup_time", None),
                stop_player_time=getattr(self, "_stop_player_time", None),
                welcome_finished_time=getattr(self, "_welcome_finished_time", None),
                last_asr_wait_log_time=getattr(self, "_last_asr_wait_log_time", 0.0),
            )
        else:
            # Sync from attributes in case they were updated externally
            # Only sync if attribute exists and state object value is None (to avoid overwriting state object values)
            if hasattr(self, "_hangup_time") and self._time_state.hangup_time is None:
                self._time_state.hangup_time = self._hangup_time
            if hasattr(self, "_stop_player_time") and self._time_state.stop_player_time is None:
                self._time_state.stop_player_time = self._stop_player_time
            if hasattr(self, "_welcome_finished_time") and self._time_state.welcome_finished_time is None:
                self._time_state.welcome_finished_time = self._welcome_finished_time
            if hasattr(self, "_last_asr_wait_log_time"):
                self._time_state.last_asr_wait_log_time = getattr(
                    self, "_last_asr_wait_log_time", 0.0
                )
        return self._time_state

    def _has_intent_methods(self) -> bool:
        """Check if intent classification methods are available."""
        return hasattr(self, "_classify_intent") and hasattr(
            self, "_play_intent_response"
        )

    def _has_check_intent_response_status(self) -> bool:
        """Check if intent response status check method exists."""
        return hasattr(self, "check_intent_response_status")

    def _sync_state_to_attributes(self) -> None:
        """Sync state objects to individual attributes for backward compatibility."""
        # Sync playback state
        self._playback_started = self._playback_state != PlaybackState.NOT_STARTED
        self._playback_finished = self._playback_state == PlaybackState.FINISHED

        # Sync intent state
        intent = self._get_intent_state()
        self._intent_response_played = intent.played
        self._intent_response_finished = intent.finished
        self._intent_response_player = intent.player
        self._intent_enabled = intent.enabled

        # Sync goodbye state
        goodbye = self._get_goodbye_state()
        self._goodbye_requested = goodbye.requested
        self._goodbye_playback_started = goodbye.playback_started
        self._goodbye_playback_finished = goodbye.playback_finished

        # Sync time state
        time_state = self._get_time_state()
        self._hangup_time = time_state.hangup_time
        self._stop_player_time = time_state.stop_player_time
        self._welcome_finished_time = time_state.welcome_finished_time
        self._last_asr_wait_log_time = time_state.last_asr_wait_log_time

    # ------------------------------------------------------------------#
    # Intent response transition logic
    # ------------------------------------------------------------------#

    def _should_trigger_goodbye_after_intent(self) -> bool:
        """Check if goodbye should be triggered after intent response finishes."""
        intent = self._get_intent_state()
        goodbye = self._get_goodbye_state()

        return (
            intent.played
            and intent.finished
            and intent.player is None
            and not goodbye.requested
        )

    def _check_intent_response_transition(self) -> bool:
        """Check intent response status and trigger goodbye if needed.

        Returns:
            True if intent response finished and goodbye was triggered.
        """
        intent_finished = False
        if self._has_check_intent_response_status():
            try:
                intent_finished = self.check_intent_response_status()
            except Exception as e:
                logger.warning(
                    "Intent: error in check_intent_response_status: %s",
                    e,
                    exc_info=True,
                )

        # Skip goodbye trigger if conversation flow is enabled - the state machine
        # will handle playing follow-up prompts or goodbye as appropriate
        conversation_flow_enabled = (
            hasattr(self, "_is_conversation_flow_enabled")
            and self._is_conversation_flow_enabled()
        )
        if conversation_flow_enabled:
            return intent_finished

        if intent_finished and self._should_trigger_goodbye_after_intent():
            try:
                logger.info(
                    "Intent: response finished and player stopped, "
                    "triggering goodbye message"
                )
                self._play_goodbye_message()
                return True
            except Exception:
                pass

        return intent_finished

    # ------------------------------------------------------------------#
    # Player cleanup logic
    # ------------------------------------------------------------------#

    def _stop_player_transmissions(self) -> None:
        """Stop all player transmissions."""
        if not self._player:
            return

        # Stop transmission to call media
        if self._call_media:
            try:
                self._player.stopTransmit(self._call_media)
                logger.info("Stopped player transmission to prevent looping")
            except Exception as exc:
                logger.warning("Error stopping player->call_media: %s", exc)

        # Stop transmission to mixed recorder
        if self._mixed_recorder:
            try:
                self._player.stopTransmit(self._mixed_recorder)
                logger.info("Stopped player transmission to mixed recorder")
            except Exception:
                pass  # Mixed recorder might already be stopped

    def _destroy_player_safely(self) -> None:
        """Destroy player with proper cleanup to avoid PJSUA2 race conditions."""
        if not self._player:
            return

        # Try to stop player explicitly before destroying
        try:
            if hasattr(self._player, "stop"):
                self._player.stop()
                logger.debug("Called player.stop() before destruction")
        except (RuntimeError, AttributeError):
            pass

        # Process pending events to let PJSUA2 finish cleanup
        try:
            import pjsua2 as pj

            ep = pj.Endpoint.instance()
            ep.libHandleEvents(10)
        except Exception:
            pass

        self._player = None
        logger.info("Destroyed player")

    def _notify_playback_finished(self) -> None:
        """Notify subsystems that playback has finished."""
        # Stop bot playback tracking
        if hasattr(self, "_stop_bot_playback_tracking"):
            try:
                self._stop_bot_playback_tracking()
            except Exception as exc:
                logger.warning(
                    "Bot tracking: error stopping playback tracking: %s", exc
                )

        # Notify VAD
        if self._vad and self._vad.available:
            try:
                self._vad.set_bot_playback_state(False, time.time)
            except Exception as exc:
                logger.warning("VAD: error notifying bot playback stop: %s", exc)

        # Collect event
        self._collect_event(
            event_type="playback_finished",
            media_type="audio",
            file_played=getattr(self._acc_ref, "play_file", None),
        )

    def _stop_player_and_cleanup(self, current_time: float) -> None:
        """Stop player transmission and perform cleanup when playback ends."""
        if self._player and self._call_media:
            try:
                self._stop_player_transmissions()
                self._destroy_player_safely()
            except Exception as exc:
                logger.warning("Error stopping player transmission: %s", exc)

        # Mark playback finished
        time_state = self._get_time_state()
        if not time_state.hangup_time:
            logger.info("Welcome message finished. Monitoring caller speech for hangup")

        self._notify_playback_finished()

        # CRITICAL: Always mark playback as finished
        self._playback_state = PlaybackState.FINISHED
        logger.info("Welcome message playback finished")
        time_state.stop_player_time = None
        time_state.welcome_finished_time = current_time
        self._sync_state_to_attributes()

    # ------------------------------------------------------------------#
    # VAD processing logic
    # ------------------------------------------------------------------#

    def _update_hangup_time_from_vad(self, current_time: float) -> None:
        """Update hangup time based on VAD speech detection."""
        if self._vad is None or self._vad.last_speech_time_monotonic is None:
            return

        target = self._vad.last_speech_time_monotonic + self._silence_after_speech_sec
        time_state = self._get_time_state()

        # CRITICAL: Ignore stale speech events from previous turns
        # If we have a known start time for the current listening period (welcome_finished_time),
        # make sure the speech occurred AFTER that time.
        if (
            time_state.welcome_finished_time is not None
            and self._vad.last_speech_time_monotonic < time_state.welcome_finished_time
        ):
            # Speech is from before the current prompt finished - ignore it
            return

        if not time_state.hangup_time or time_state.hangup_time < target:
            old_hangup_time = time_state.hangup_time
            time_state.hangup_time = target

            # Log only if hangup time changed significantly
            if old_hangup_time is None or (target - old_hangup_time) > 0.5:
                logger.debug(
                    "VAD: last speech at %.3f; hangup at %.3f",
                    self._vad.last_speech_time_monotonic,
                    target,
                )
        
        # Ensure hangup_time is relevant for the current turn
        # If the hangup_time is BEFORE the welcome/prompt finished, it means it belongs
        # to a previous turn or interrupted speech, so we should essentially ignore it
        # for the purpose of "post-prompt silence".
        if (
            time_state.hangup_time
            and time_state.welcome_finished_time
            and time_state.hangup_time < time_state.welcome_finished_time
        ):
            # If the calculated hangup_time is in the past relative to when the bot finished speaking,
            # it means the speech ended before the bot finished.
            # We might want to keep it if we support barge-in, but if we are strict about "listening after prompt",
            # we should update it or treat it carefully.
            # For now, let's just log it.
            # logger.debug("VAD: hangup_time %.3f is before prompt finish %.3f", time_state.hangup_time, time_state.welcome_finished_time)
            pass

    def _finalize_chunks_on_silence(self, current_time: float) -> None:
        """Finalize VAD chunks when silence is confirmed."""
        if self._vad is None or self._vad.last_speech_time_monotonic is None:
            return

        target = self._vad.last_speech_time_monotonic + self._silence_after_speech_sec

        if (
            current_time >= target
            and self._asr_enabled
            and self._asr_available
            and not self._asr_complete
        ):
            try:
                current_chunk = self._vad.get_current_chunk()
                if current_chunk is not None:
                    self._vad.finalize_all_chunks(time.time)
                    logger.debug("VAD: finalized current chunk due to silence")
            except Exception as e:
                logger.warning("VAD: error finalizing chunk: %s", e)

    def _process_vad_audio(self, current_time: float) -> list[Any]:
        """Process VAD audio and update hangup time based on speech detection.

        Returns:
            List of finalized audio chunks from VAD.
        """
        if self._vad is None:
            return []

        # Debug: confirm VAD is being called
        if not hasattr(self, "_vad_called"):
            logger.debug("VAD: processing audio from %s", self._recording_file)
            self._vad_called = True

        self._vad.process_new_audio(time.time)
        self._update_hangup_time_from_vad(current_time)
        self._finalize_chunks_on_silence(current_time)

        chunks = self._vad.get_chunks()
        if chunks is None:
            return []
        return cast(list[Any], chunks) if isinstance(chunks, list) else []

    # ------------------------------------------------------------------#
    # ASR chunk submission logic
    # ------------------------------------------------------------------#

    def _should_wait_for_silence_period(self, current_time: float) -> bool:
        """Check if we should wait for silence period before transcribing."""
        time_state = self._get_time_state()

        if time_state.hangup_time is None:
            logger.debug("ASR: waiting for VAD to set hangup_time before transcribing")
            return True

        if current_time < time_state.hangup_time:
            # Throttle logging to avoid spam
            time_since_last_log = current_time - time_state.last_asr_wait_log_time
            should_log = (
                time_since_last_log >= 0.5 or time_state.last_asr_wait_log_time == 0.0
            )

            if should_log:
                time_state.last_asr_wait_log_time = current_time
                time_until_hangup = time_state.hangup_time - current_time
                logger.debug(
                    "ASR: waiting for silence period before transcribing "
                    "(%.2fs remaining until hangup_time)",
                    time_until_hangup,
                )
            return True

        return False

    def _ensure_asr_available(self) -> None:
        """Ensure ASR service is available and worker thread is started."""
        if self._asr_available:
            return

        self._asr = getattr(self._acc_ref, "_asr_service", None)
        self._asr_available = bool(
            getattr(self._acc_ref, "_asr_available", False)
            and self._asr is not None
            and self._asr.available
        )

        if self._asr_available:
            logger.info("ASR: service became available, starting worker thread")
            self._start_asr_thread()

    def _submit_chunks_for_transcription(
        self, chunks: list, current_time: float
    ) -> None:
        """Submit newly finalized chunks to the ASR worker thread.

        Only submits chunks after the silence period has passed (hangup_time reached)
        to confirm that speech has ended before transcribing.
        """
        has_new_chunks = len(chunks) > self._last_transcribed_chunk_count

        if has_new_chunks and self._should_wait_for_silence_period(current_time):
            return

        # Submit chunks for transcription
        for idx in range(self._last_transcribed_chunk_count, len(chunks)):
            ch = chunks[idx]
            if not (
                self._asr_enabled and ch.file_path and os.path.exists(ch.file_path)
            ):
                continue

            self._ensure_asr_available()

            if self._asr_available:
                self._submit_transcription_task(ch.file_path, idx)

        self._last_transcribed_chunk_count = len(chunks)

    # ------------------------------------------------------------------#
    # ASR completion logic
    # ------------------------------------------------------------------#

    def _is_asr_ready_to_complete(self, chunks: list, current_time: float) -> bool:
        """Check if ASR is in a valid state to be marked as complete.

        Ensures chunks have actually been finalized AND submitted for
        transcription before marking ASR complete.

        Returns:
            True if ASR is ready to be marked complete.
        """
        if self._playback_state != PlaybackState.FINISHED:
            return False

        has_chunks = len(chunks) > self._asr_chunk_offset
        chunks_submitted = self._last_transcribed_chunk_count == len(chunks)

        time_state = self._get_time_state()
        if time_state.welcome_finished_time is None:
            time_state.welcome_finished_time = current_time

        time_since_welcome = (
            current_time - time_state.welcome_finished_time
            if time_state.welcome_finished_time
            else 0.0
        )

        # Extra grace period after hangup_time for chunk finalization
        # Make sure hangup_time is valid for this turn (must be AFTER welcome_finished_time)
        hangup_valid_for_turn = (
            time_state.hangup_time is not None
            and time_state.welcome_finished_time is not None
            and time_state.hangup_time >= time_state.welcome_finished_time
        )
        
        hangup_grace_passed = (
            hangup_valid_for_turn
            and current_time >= time_state.hangup_time + 2.0
        )

        # Fallback timeout: if 10+ seconds since welcome and no speech detected
        no_speech_timeout = time_state.hangup_time is None and time_since_welcome > 10.0

        # ASR can complete if:
        # - We have chunks AND they've been submitted, OR
        # - Hangup time + grace period passed, OR
        # - Long timeout with no speech at all
        return (
            (has_chunks and chunks_submitted)
            or hangup_grace_passed
            or no_speech_timeout
        )

    def _get_transcription_text(self) -> str | None:
        """Get transcription text from ASR chunks."""
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

    def _classify_and_play_intent(self) -> None:
        """Classify intent from transcription and play response if available."""
        if not self._has_intent_methods():
            return

        intent = self._get_intent_state()
        if not intent.enabled:
            return

        transcription_text = self._get_transcription_text()
        if not transcription_text:
            logger.debug("Intent: skipping classification - no transcription available")
            return

        try:
            classification = self._classify_intent()
            if classification:
                intent_name, confidence = classification
                logger.info(
                    "Intent: classified intent '%s' with confidence %.2f",
                    intent_name,
                    confidence,
                )
                self._play_intent_response()
        except Exception as exc:
            logger.warning("Intent: error in intent classification: %s", exc)

    def _should_trigger_goodbye_after_asr(
        self, chunks: list, current_time: float
    ) -> bool:
        """Check if goodbye should be triggered after ASR completion."""
        intent = self._get_intent_state()
        if intent.played:
            return False

        has_chunks = len(chunks) > 0
        time_state = self._get_time_state()

        if has_chunks:
            # Speech was detected - wait for hangup_time
            return (
                time_state.hangup_time is not None
                and current_time >= time_state.hangup_time
            )
        else:
            # No speech detected - hangup_time None means timeout
            return (
                time_state.hangup_time is None or current_time >= time_state.hangup_time
            )

    def _handle_asr_completion(self, chunks: list, current_time: float) -> None:
        """Handle ASR completion: classify intent and trigger conversation flow."""
        asr_queue = getattr(self, "_asr_queue", None)
        if asr_queue is None:
            return

        # Check if all chunks have been submitted and queue is empty
        queue_ready = (
            self._last_transcribed_chunk_count == len(chunks)
            and asr_queue.empty()
            and asr_queue.unfinished_tasks == 0
        )
        if not queue_ready:
            return

        # Mark ASR as complete
        self._asr_complete = True
        logger.info("ASR: transcription complete")

        # Check if conversation flow is enabled
        conversation_flow_enabled = (
            hasattr(self, "_is_conversation_flow_enabled")
            and self._is_conversation_flow_enabled()
        )

        if conversation_flow_enabled:
            # Let conversation flow handle the rest
            logger.debug("ASR: delegating to conversation flow state machine")
            # Classify intent (conversation flow will use this)
            self._classify_and_play_intent()
            # Conversation flow will be processed in check_playback_status
            return

        # Legacy behavior: classify intent and play response directly
        self._classify_and_play_intent()

        # Trigger goodbye if no intent response is playing
        if self._should_trigger_goodbye_after_asr(chunks, current_time):
            logger.info("ASR: no intent response, playing goodbye message")
            self._play_goodbye_message()
        else:
            time_state = self._get_time_state()
            time_until_hangup = (
                time_state.hangup_time - current_time
                if time_state.hangup_time
                else None
            )
            logger.debug(
                "ASR: transcription complete but waiting for silence period "
                "(%.2fs remaining until hangup_time)",
                time_until_hangup if time_until_hangup else 0.0,
            )

    # ------------------------------------------------------------------#
    # Main playback status check
    # ------------------------------------------------------------------#

    def _should_skip_vad_processing(self) -> bool:
        """Check if VAD processing should be skipped.

        NOTE: When conversation flow is enabled, we must continue running VAD/ASR
        even after an intent response has finished so that follow-up prompts
        (e.g. \"Any other questions?\", YES/NO replies) can be recognised.
        """
        intent = self._get_intent_state()
        goodbye = self._get_goodbye_state()

        # If conversation flow is enabled, only skip VAD once goodbye has started
        # or been explicitly requested. Intent completion alone is not enough,
        # because the state machine may still be waiting for follow-up input.
        conversation_flow_enabled = (
            hasattr(self, "_is_conversation_flow_enabled")
            and self._is_conversation_flow_enabled()
        )
        if conversation_flow_enabled:
            return goodbye.requested or goodbye.playback_started

        # Legacy behaviour when conversation flow is disabled
        return intent.finished or goodbye.requested or goodbye.playback_started

    def _should_skip_further_processing(self) -> bool:
        """Check if further processing should be skipped."""
        if not self._is_call_active():
            goodbye = self._get_goodbye_state()
            intent = self._get_intent_state()
            return goodbye.playback_finished and intent.finished
        return False

    def _process_vad_and_asr(self, current_time: float) -> None:
        """Process VAD audio and handle ASR transcription."""
        if not (
            self._vad
            and self._vad.available
            and self._recording_file
            and not self._should_skip_vad_processing()
        ):
            return

        try:
            chunks = self._process_vad_audio(current_time)

            try:
                self._submit_chunks_for_transcription(chunks, current_time)

                if (
                    self._asr_enabled
                    and self._asr_available
                    and not self._asr_complete
                    and self._is_asr_ready_to_complete(chunks, current_time)
                ):
                    self._handle_asr_completion(chunks, current_time)

            except Exception as exc:
                logger.warning("ASR: live transcription error: %s", exc)
        except Exception as exc:
            logger.warning("VAD processing error: %s", exc)

    def _check_late_goodbye_trigger(self, current_time: float) -> None:
        """Check if goodbye should be triggered after ASR completion."""
        if not self._asr_complete:
            return

        intent = self._get_intent_state()
        if intent.played:
            return

        if self._should_skip_vad_processing():
            return

        chunks = self._vad.get_chunks() if (self._vad and self._vad.available) else []
        has_chunks = len(chunks) > 0

        time_state = self._get_time_state()
        if (
            has_chunks
            and time_state.hangup_time is not None
            and current_time >= time_state.hangup_time
        ):
            logger.info(
                "ASR: hangup_time reached after ASR completion, triggering "
                "goodbye message"
            )
            self._play_goodbye_message()

    def check_playback_status(self) -> None:
        """Check if playback has finished and set hangup time if needed.

        This method orchestrates the playback lifecycle by delegating to
        focused helper methods.
        """
        # Always check intent response transition and goodbye status
        self._check_intent_response_transition()
        self.check_goodbye_status()

        # Skip further processing if call is inactive and cleanup is done
        if self._should_skip_further_processing():
            return

        # Sync state from attributes before checking (for backward compatibility)
        if hasattr(self, "_playback_started") and self._playback_started:
            if self._playback_state == PlaybackState.NOT_STARTED:
                self._playback_state = PlaybackState.PLAYING
        if hasattr(self, "_playback_finished") and self._playback_finished:
            self._playback_state = PlaybackState.FINISHED

        if self._playback_state == PlaybackState.NOT_STARTED:
            return

        current_time = time.time()
        time_state = self._get_time_state()

        # Stop player if scheduled time has been reached
        if (
            time_state.stop_player_time
            and current_time >= time_state.stop_player_time
            and self._playback_state != PlaybackState.FINISHED
        ):
            self._stop_player_and_cleanup(current_time)

        # Process VAD and ASR
        self._process_vad_and_asr(current_time)

        # Process conversation flow if enabled
        if hasattr(self, "_handle_conversation_flow"):
            try:
                conversation_flow_enabled = (
                    hasattr(self, "_is_conversation_flow_enabled")
                    and self._is_conversation_flow_enabled()
                )
                if conversation_flow_enabled:
                    self._handle_conversation_flow()
            except Exception as e:
                logger.warning("ConversationFlow: error in state machine: %s", e)

        # Check for late goodbye trigger (legacy fallback)
        if not (
            hasattr(self, "_is_conversation_flow_enabled")
            and self._is_conversation_flow_enabled()
        ):
            self._check_late_goodbye_trigger(current_time)

        # Sync state back to attributes for backward compatibility
        self._sync_state_to_attributes()

    # ------------------------------------------------------------------#
    # Hangup logic
    # ------------------------------------------------------------------#

    def _set_hangup_time(self) -> None:
        """Set hangup time (2s after playback finishes)."""
        hangup_delay = getattr(self._acc_ref, "hangup_delay", 2)
        time_state = self._get_time_state()
        time_state.hangup_time = time.time() + hangup_delay
        logger.info(
            "Welcome message finished. Will hang up in %s seconds", hangup_delay
        )

    def _is_intent_response_still_playing(self) -> bool:
        """Check if intent response is still playing."""
        intent = self._get_intent_state()

        if not intent.played:
            return False

        if not self._has_check_intent_response_status():
            return True  # Assume playing if we can't check

        try:
            intent_finished = self.check_intent_response_status()
            if not intent_finished:
                return True

            # Additional checks: ensure player is destroyed and enough time passed
            intent_finished_time = getattr(self, "_intent_response_finished_time", None)
            time_since_finished = (
                time.time() - intent_finished_time if intent_finished_time else 0.0
            )

            if (
                intent.player is not None
                or not intent.finished
                or time_since_finished < 0.1
            ):
                return True
        except Exception:
            return True  # If check fails, assume still playing

        return False

    def _check_intent_and_goodbye_for_hangup(self) -> bool | None:
        """Check intent response and goodbye status to determine hangup readiness.

        Returns:
            True: Ready to hang up (goodbye finished or no goodbye file).
            False: Not ready (intent/goodbye still playing).
            None: Intent response still playing, caller should wait.
        """
        if self._is_intent_response_still_playing():
            return None

        # Check goodbye status
        goodbye = self._get_goodbye_state()
        if goodbye.file and not goodbye.playback_finished and not goodbye.requested:
            return False

        if goodbye.playback_finished:
            return True

        if not goodbye.file:
            return True

        return False  # Goodbye is playing

    def should_hangup(self) -> bool:
        """Check if it's time to hang up the call.

        Flow:
        1. When VAD detects silence, play waiting voice
        2. Wait for ASR transcription to complete
        3. After ASR completes, play intent response (if classified)
        4. After intent response finishes, play goodbye message
        5. After goodbye finishes, hang up

        Returns True only when it's actually time to hang up
        (after goodbye if applicable).
        """
        if not self._asr_complete:
            # Fallback: original hangup logic for cases without ASR
            time_state = self._get_time_state()
            if time_state.hangup_time and time.time() >= time_state.hangup_time:
                result = self._check_intent_and_goodbye_for_hangup()
                return result is True
            return False

        result = self._check_intent_and_goodbye_for_hangup()
        if result is None:
            return False  # Intent still playing, wait
        return result
