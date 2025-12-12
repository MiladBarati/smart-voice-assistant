"""Playback monitoring and hangup logic extracted from `AnyCall`."""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Any, Callable

logger = logging.getLogger(__name__)


class PlaybackMonitorMixin:
    """Encapsulates playback completion, VAD-driven hangup, and ASR chunking."""

    # Attributes supplied by sibling mixins / host class (for type-checkers)
    _acc_ref: Any
    _player: Any | None
    _mixed_recorder: Any | None
    _call_media: Any | None
    _collect_event: Callable[..., None]
    _hangup_time: float | None
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

    _goodbye_playback_finished: bool
    _goodbye_requested: bool

    _asr_complete: bool
    _stop_player_time: float | None

    if TYPE_CHECKING:

        def check_goodbye_status(self) -> None: ...

        def _play_goodbye_message(self) -> None: ...

    def _init_playback_state(self) -> None:
        """Initialise playback-related attributes."""
        self._player = None
        self._mixed_recorder = None
        self._call_media = None
        self._playback_started = False
        self._playback_finished = False
        self._stop_player_time: float | None = None
        self._vad_called = False

    def _schedule_player_stop(self, delay_seconds: float) -> None:
        """Schedule player teardown after the specified delay."""
        self._stop_player_time = time.time() + delay_seconds

    # ------------------------------------------------------------------#
    # Playback + hangup lifecycle
    # ------------------------------------------------------------------#

    def _check_intent_response_transition(self) -> bool:
        """Check intent response status and trigger goodbye if needed.

        Returns:
            True if intent response finished and goodbye was triggered.
        """
        intent_finished = False
        if hasattr(self, "check_intent_response_status"):
            try:
                intent_finished = self.check_intent_response_status()
            except Exception as e:
                logger.warning(
                    "Intent: error in check_intent_response_status: %s", e, exc_info=True
                )

        # Check if intent response finished and we should play goodbye
        # Only trigger goodbye if:
        # 1. Intent response was played
        # 2. Intent response is actually finished (not just checked)
        # 3. Intent response player is destroyed (None)
        # 4. At least 0.1 seconds have passed since intent response finished
        #    (ensures player fully stopped)
        # 5. Goodbye hasn't been requested yet
        intent_finished_time = getattr(self, "_intent_response_finished_time", None)
        time_since_finished = (
            time.time() - intent_finished_time if intent_finished_time else float("inf")
        )

        if (
            hasattr(self, "_intent_response_played")
            and getattr(self, "_intent_response_played", False)
            and intent_finished
            and getattr(self, "_intent_response_finished", False)
            and getattr(self, "_intent_response_player", None) is None
            and time_since_finished >= 0.1  # Small delay to ensure player fully stopped
            and not getattr(self, "_goodbye_requested", False)
        ):
            try:
                # Intent response finished and player is destroyed, now play goodbye
                logger.info(
                    "Intent: response finished and player stopped, "
                    "triggering goodbye message"
                )
                self._play_goodbye_message()
                return True
            except Exception:
                pass  # If check fails, continue normally

        return intent_finished

    def _stop_player_and_cleanup(self, current_time: float) -> None:
        """Stop player transmission and perform cleanup when playback ends."""
        if self._player and self._call_media:
            try:
                # Stop the transmission from player to call media
                self._player.stopTransmit(self._call_media)
                logger.info("Stopped player transmission to prevent looping")

                # Stop the transmission from player to mixed recorder
                # to prevent the welcome message from being replayed
                if getattr(self, "_mixed_recorder", None):
                    try:
                        self._player.stopTransmit(self._mixed_recorder)
                        logger.info("Stopped player transmission to mixed recorder")
                    except Exception:
                        # Mixed recorder might already be stopped, ignore
                        pass

                # Also stop the call media to playback transmission
                # to break the audio path
                import pjsua2 as pj  # local import to avoid module-level dependency

                adm = pj.Endpoint.instance().audDevManager()
                playback = adm.getPlaybackDevMedia()
                self._call_media.stopTransmit(playback)
                logger.info("Stopped call media to playback transmission")

                # Destroy the player completely
                self._player = None
                logger.info("Destroyed player")

            except Exception as exc:
                logger.warning("Error stopping player transmission: %s", exc)

        # Mark playback finished; hangup will be controlled by VAD
        if not self._hangup_time:
            logger.info("Welcome message finished. Monitoring caller speech for hangup")

        # Stop tracking bot talk duration (always do this when welcome ends)
        if hasattr(self, "_stop_bot_playback_tracking"):
            try:
                self._stop_bot_playback_tracking()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Bot tracking: error stopping playback tracking: %s", exc)

        # Notify VAD that bot playback finished (always do this)
        if self._vad and self._vad.available:
            try:
                self._vad.set_bot_playback_state(False, time.time)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("VAD: error notifying bot playback stop: %s", exc)

        # Collect playback finished event
        self._collect_event(
            event_type="playback_finished",
            media_type="audio",
            file_played=getattr(self._acc_ref, "play_file", None),
        )

        # CRITICAL: Always mark playback as finished when the player stops
        # This is needed for ASR completion checks to work correctly
        self._playback_finished = True
        logger.info("Welcome message playback finished")
        # Clear stop time to prevent re-running this block
        self._stop_player_time = None

    def _process_vad_audio(self, current_time: float) -> list:
        """Process VAD audio and update hangup time based on speech detection.

        Returns:
            List of finalized audio chunks from VAD.
        """
        # Debug: confirm VAD is being called
        if not hasattr(self, "_vad_called"):
            logger.debug("VAD: processing audio from %s", self._recording_file)
            self._vad_called = True

        self._vad.process_new_audio(time.time)

        if self._vad.last_speech_time_monotonic is not None:
            target = (
                self._vad.last_speech_time_monotonic + self._silence_after_speech_sec
            )

            if not self._hangup_time or self._hangup_time < target:
                # Update hangup time if needed
                self._hangup_time = target
                logger.debug(
                    "VAD: last speech at %.3f; hangup at %.3f",
                    self._vad.last_speech_time_monotonic,
                    target,
                )
                # Finalize current chunk immediately when silence is confirmed
                # to ensure we capture the end of speech quickly for ASR
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

        return self._vad.get_chunks()

    def _submit_chunks_for_transcription(self, chunks: list) -> None:
        """Submit newly finalized chunks to the ASR worker thread."""
        for idx in range(self._last_transcribed_chunk_count, len(chunks)):
            ch = chunks[idx]
            if self._asr_enabled and ch.file_path and os.path.exists(ch.file_path):
                # Re-check ASR availability in case it came online
                if not self._asr_available:
                    self._asr = getattr(self._acc_ref, "_asr_service", None)
                    self._asr_available = bool(
                        getattr(self._acc_ref, "_asr_available", False)
                        and self._asr is not None
                        and self._asr.available
                    )
                    if self._asr_available:
                        logger.info(
                            "ASR: service became available, starting worker thread"
                        )
                        self._start_asr_thread()

                if self._asr_available:
                    # Submit chunk to worker thread.
                    self._submit_transcription_task(ch.file_path, idx)

        self._last_transcribed_chunk_count = len(chunks)

    def _is_asr_ready_to_complete(
        self, chunks: list, current_time: float
    ) -> bool:
        """Check if ASR is in a valid state to be marked as complete.

        Ensures chunks have actually been finalized before marking ASR complete.
        The issue is that VAD might detect brief speech, set hangup_time 3s later,
        but not finalize chunks until later.

        Logic:
        1. If we have chunks, wait for them to be processed
        2. If no chunks but hangup_time passed, wait a bit more
           (give VAD time to finalize any pending chunks)
        3. If no chunks and a long time has passed since welcome
           ended (10+ seconds), assume caller won't speak

        Returns:
            True if ASR is ready to be marked complete.
        """
        welcome_finished = getattr(self, "_playback_finished", False)
        has_chunks = len(chunks) > 0

        # Track when welcome finished (for timeout calculation)
        if welcome_finished and not hasattr(self, "_welcome_finished_time"):
            self._welcome_finished_time = current_time

        welcome_finished_time = getattr(self, "_welcome_finished_time", None)
        time_since_welcome = (
            current_time - welcome_finished_time if welcome_finished_time else 0.0
        )

        # Extra grace period after hangup_time for chunk finalization
        # If hangup_time passed but no chunks, wait 2 more seconds
        hangup_grace_passed = (
            self._hangup_time is not None
            and current_time >= self._hangup_time + 2.0
        )

        # Fallback timeout: if 10+ seconds since welcome and no speech
        # detected at all (no hangup_time set), proceed anyway
        no_speech_timeout = self._hangup_time is None and time_since_welcome > 10.0

        # We can only consider ASR complete if:
        # - Welcome message finished playing, AND one of:
        #   - We have chunks (speech was finalized), OR
        #   - Hangup time + grace period passed (chunks should be ready), OR
        #   - Long timeout with no speech at all
        return welcome_finished and (
            has_chunks or hangup_grace_passed or no_speech_timeout
        )

    def _handle_asr_completion(self, chunks: list, current_time: float) -> None:
        """Handle ASR completion: classify intent and trigger goodbye."""
        asr_queue = getattr(self, "_asr_queue", None)
        if asr_queue is None:
            return

        # Check if all chunks have been submitted and queue is empty
        if not (
            self._last_transcribed_chunk_count == len(chunks)
            and asr_queue.empty()
            and asr_queue.unfinished_tasks == 0
        ):
            return

        # ASR transcription is complete
        self._asr_complete = True
        logger.info("ASR: transcription complete")

        # Classify intent and play response
        if hasattr(self, "_classify_intent") and hasattr(self, "_play_intent_response"):
            try:
                # Check if intent classification is enabled
                if getattr(self, "_intent_enabled", False):
                    # Classify intent from transcription
                    classification = self._classify_intent()
                    if classification:
                        intent_name, confidence = classification
                        logger.info(
                            "Intent: classified intent '%s' with confidence %.2f",
                            intent_name,
                            confidence,
                        )

                        # Play intent response
                        # Goodbye will be triggered by check_playback_status
                        # once intent response finishes
                        self._play_intent_response()
            except Exception as exc:
                logger.warning("Intent: error in intent classification: %s", exc)

        # If no intent response is playing, trigger goodbye immediately.
        # Otherwise, goodbye will be triggered by check_playback_status
        # when intent response finishes
        if not getattr(self, "_intent_response_played", False):
            logger.info("ASR: no intent response, playing goodbye message")
            self._play_goodbye_message()

    def check_playback_status(self) -> None:
        """Check if playback has finished and set hangup time if needed.

        This method orchestrates the playback lifecycle by delegating to
        focused helper methods:
        - _check_intent_response_transition(): Handle intent response -> goodbye
        - _stop_player_and_cleanup(): Stop player when playback ends
        - _process_vad_audio(): Process VAD and update hangup time
        - _handle_asr_completion(): Handle ASR completion and intent classification
        """
        # Check intent response status and trigger goodbye if needed
        self._check_intent_response_transition()

        # Check goodbye message status
        self.check_goodbye_status()

        if not self._playback_started:
            return

        current_time = time.time()

        # Check if it's time to stop the player transmission
        if (
            self._stop_player_time
            and current_time >= self._stop_player_time
            and not self._playback_finished
        ):
            self._stop_player_and_cleanup(current_time)

        # Skip VAD processing if intent response finished
        # This prevents VAD from capturing audio after FAQ response and before hangup
        # Once FAQ response finishes, we transition directly to goodbye
        intent_finished = hasattr(self, "_intent_response_finished") and getattr(
            self, "_intent_response_finished", False
        )
        goodbye_requested_or_playing = getattr(
            self, "_goodbye_requested", False
        ) or getattr(self, "_goodbye_playback_started", False)

        # If VAD is available, process new audio and handle silence
        # But skip if intent response finished or goodbye is already playing
        if (
            self._vad
            and self._vad.available
            and self._recording_file
            and not intent_finished
            and not goodbye_requested_or_playing
        ):
            try:
                chunks = self._process_vad_audio(current_time)

                # Live transcription of newly finalized chunks (non-blocking)
                try:
                    self._submit_chunks_for_transcription(chunks)

                    # Check if ASR transcription is complete
                    if (
                        self._asr_enabled
                        and self._asr_available
                        and not self._asr_complete
                        and self._is_asr_ready_to_complete(chunks, current_time)
                    ):
                        self._handle_asr_completion(chunks, current_time)

                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("ASR: live transcription error: %s", exc)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("VAD processing error: %s", exc)

    def _set_hangup_time(self) -> None:
        """Set hangup time (2s after playback finishes)."""
        hangup_delay = getattr(self._acc_ref, "hangup_delay", 2)
        self._hangup_time = time.time() + hangup_delay
        logger.info("Welcome message finished. Will hang up in %s seconds", hangup_delay)

    def _check_intent_and_goodbye_for_hangup(self) -> bool | None:
        """Check intent response and goodbye status to determine hangup readiness.

        Returns:
            True: Ready to hang up (goodbye finished or no goodbye file).
            False: Not ready (intent/goodbye still playing).
            None: Intent response still playing, caller should wait.
        """
        # Check if intent response is playing - wait for it to finish
        if hasattr(self, "_intent_response_played") and getattr(
            self, "_intent_response_played", False
        ):
            if hasattr(self, "check_intent_response_status"):
                try:
                    intent_finished = self.check_intent_response_status()
                    if not intent_finished:
                        # Intent response is still playing, wait for it to finish
                        return None
                    # Additional check: ensure player is actually destroyed
                    # and enough time passed
                    intent_player = getattr(self, "_intent_response_player", None)
                    intent_finished_flag = getattr(
                        self, "_intent_response_finished", False
                    )
                    intent_finished_time = getattr(
                        self, "_intent_response_finished_time", None
                    )
                    time_since_finished = (
                        time.time() - intent_finished_time
                        if intent_finished_time
                        else 0.0
                    )
                    if (
                        intent_player is not None
                        or not intent_finished_flag
                        or time_since_finished < 0.1
                    ):
                        # Player still exists, not finished, or not enough
                        # time passed - wait
                        return None
                except Exception:
                    # If check fails, don't assume finished - be safe and wait
                    return None

        # Intent response finished (or not playing), now check goodbye
        # Don't trigger goodbye here - let check_playback_status() handle it
        # with proper timing
        goodbye_file = getattr(self._acc_ref, "goodbye_file", None)
        if (
            goodbye_file
            and not self._goodbye_playback_finished
            and not self._goodbye_requested
        ):
            # Goodbye needs to be played, but check_playback_status() will
            # handle the trigger
            # Just return False to indicate we're not ready to hang up yet
            return False
        if self._goodbye_playback_finished:
            # Goodbye finished, now we can hang up
            return True
        if not goodbye_file:
            # No goodbye file, hang up immediately after ASR and intent response
            return True
        # Goodbye is playing, wait for it to finish
        return False

    def should_hangup(self) -> bool:
        """Check if it's time to hang up the call.

        New flow:
        1. When VAD detects silence, play waiting voice
        2. Wait for ASR transcription to complete
        3. After ASR completes, play intent response (if classified)
        4. After intent response finishes, play goodbye message
        5. After goodbye finishes, hang up

        Returns True only when it's actually time to hang up
        (after goodbye if applicable).
        """

        # If ASR is complete (or not enabled) and goodbye needs to be played
        if self._asr_complete:
            result = self._check_intent_and_goodbye_for_hangup()
            if result is None:
                return False  # Intent still playing, wait
            return result

        # Fallback: original hangup logic for cases without ASR or waiting voice
        if self._hangup_time and time.time() >= self._hangup_time:
            result = self._check_intent_and_goodbye_for_hangup()
            if result is None:
                return False  # Intent still playing, wait
            return result
        return False
