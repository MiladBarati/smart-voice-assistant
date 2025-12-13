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
                    "Intent: error in check_intent_response_status: %s",
                    e,
                    exc_info=True,
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
            and time_since_finished
            >= 0.5  # Delay to ensure audio pipeline fully drains
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
                # Check if call is still active before attempting port disconnection
                call_active = False
                try:
                    if hasattr(self, "isActive"):
                        call_active = self.isActive()
                except Exception:
                    # Call might be destroyed, assume inactive
                    call_active = False

                # Import pjsua2 here (before using it) - local import to avoid module-level dependency
                import pjsua2 as pj

                if call_active:
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()

                    # FIX: Skip stopping call_media->playback transmission to prevent PJSUA2
                    # internal "Remove port failed" error. When we stop the player transmission
                    # and destroy the player, PJSUA2 starts cleaning up the conference bridge.
                    # Stopping call_media->playback at this point causes a race condition where
                    # PJSUA2 tries to remove a port that's already being cleaned up.
                    # The call_media->playback transmission will be cleaned up automatically
                    # when the call ends or when PJSUA2's cleanup completes.
                    logger.debug(
                        "Skipped stopping call_media->playback to avoid PJSUA2 internal error"
                    )
                    # Original code (commented out):
                    # self._call_media.stopTransmit(playback)
                    # logger.info("Stopped call media to playback transmission")

                # Destroy the player completely
                # Try to stop the player explicitly before destroying to ensure
                # it's fully disconnected from the conference bridge. This may
                # help prevent the PJSUA2 "Remove port failed" error.
                try:
                    # Try to stop the player explicitly before destroying
                    if hasattr(self._player, "stop"):
                        self._player.stop()
                        logger.debug("Called player.stop() before destruction")
                except (RuntimeError, AttributeError):
                    pass  # stop() might not be available, that's OK

                # Small delay to let PJSUA2 finish cleanup from stopTransmit calls
                # This may help prevent the race condition in PJSUA2's destructor
                ep = pj.Endpoint.instance()
                ep.libHandleEvents(10)  # Process any pending events

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
                logger.warning(
                    "Bot tracking: error stopping playback tracking: %s", exc
                )

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
                old_hangup_time = self._hangup_time
                self._hangup_time = target
                # Only log if hangup time changed significantly (avoid spam during continuous speech)
                if old_hangup_time is None or (target - old_hangup_time) > 0.5:
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

    def _submit_chunks_for_transcription(
        self, chunks: list, current_time: float
    ) -> None:
        """Submit newly finalized chunks to the ASR worker thread.

        Only submits chunks after the silence period has passed (hangup_time reached)
        to confirm that speech has ended before transcribing.
        """
        # Only submit chunks if silence period has passed (hangup_time reached)
        # This ensures we wait 3 seconds to confirm speech has ended before transcribing
        has_new_chunks = len(chunks) > self._last_transcribed_chunk_count

        if has_new_chunks:
            # If we have chunks (speech was detected), wait for hangup_time to be set and reached
            if self._hangup_time is None:
                # VAD hasn't set hangup_time yet, wait for it
                logger.debug(
                    "ASR: waiting for VAD to set hangup_time before transcribing"
                )
                return  # Don't submit chunks yet

            if current_time < self._hangup_time:
                # Silence period hasn't passed yet, wait for it
                time_until_hangup = self._hangup_time - current_time
                # Throttle logging to avoid spam (only log every 0.5 seconds)
                last_log_time = getattr(self, "_last_asr_wait_log_time", 0.0)
                time_since_last_log = current_time - last_log_time
                should_log = time_since_last_log >= 0.5 or last_log_time == 0.0
                if should_log:
                    self._last_asr_wait_log_time = current_time
                    logger.debug(
                        "ASR: waiting for silence period before transcribing "
                        "(%.2fs remaining until hangup_time)",
                        time_until_hangup,
                    )
                return  # Don't submit chunks yet

        # Silence period has passed (or no hangup_time set, meaning no speech detected)
        # Now submit chunks for transcription
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

    def _is_asr_ready_to_complete(self, chunks: list, current_time: float) -> bool:
        """Check if ASR is in a valid state to be marked as complete.

        Ensures chunks have actually been finalized AND submitted for transcription
        before marking ASR complete. The issue is that VAD might detect brief speech,
        set hangup_time 3s later, but chunks need to be submitted before ASR can complete.

        Logic:
        1. If we have chunks, wait for them to be submitted (last_transcribed_count == len(chunks))
        2. If no chunks but hangup_time passed, wait a bit more
           (give VAD time to finalize any pending chunks)
        3. If no chunks and a long time has passed since welcome
           ended (10+ seconds), assume caller won't speak

        Returns:
            True if ASR is ready to be marked complete.
        """
        welcome_finished = getattr(self, "_playback_finished", False)
        has_chunks = len(chunks) > 0
        chunks_submitted = self._last_transcribed_chunk_count == len(chunks)

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
            self._hangup_time is not None and current_time >= self._hangup_time + 2.0
        )

        # Fallback timeout: if 10+ seconds since welcome and no speech
        # detected at all (no hangup_time set), proceed anyway
        no_speech_timeout = self._hangup_time is None and time_since_welcome > 10.0

        # We can only consider ASR complete if:
        # - Welcome message finished playing, AND one of:
        #   - We have chunks AND they've been submitted for transcription, OR
        #   - Hangup time + grace period passed (chunks should be ready), OR
        #   - Long timeout with no speech at all
        result = welcome_finished and (
            (has_chunks and chunks_submitted) or hangup_grace_passed or no_speech_timeout
        )
        return result

    def _handle_asr_completion(self, chunks: list, current_time: float) -> None:
        """Handle ASR completion: classify intent and trigger goodbye."""
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

        # ASR transcription is complete
        self._asr_complete = True
        logger.info("ASR: transcription complete")

        # Check if we have transcription before attempting classification
        asr_chunk_texts = getattr(self, "_asr_chunk_texts", [])
        asr_lock = getattr(self, "_asr_lock", None)
        transcription_text = None
        try:
            if asr_lock is not None:
                with asr_lock:
                    if asr_chunk_texts:
                        transcription_text = " ".join(
                            t for t in asr_chunk_texts if t
                        ).strip()
            else:
                if asr_chunk_texts:
                    transcription_text = " ".join(
                        t for t in asr_chunk_texts if t
                    ).strip()
        except Exception:
            pass

        # Classify intent and play response
        if hasattr(self, "_classify_intent") and hasattr(self, "_play_intent_response"):
            try:
                # Check if intent classification is enabled
                if getattr(self, "_intent_enabled", False):
                    # Only classify if we have transcription text
                    if transcription_text:
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
                    else:
                        # No transcription available, skip intent classification
                        logger.debug(
                            "Intent: skipping classification - no transcription available"
                        )
            except Exception as exc:
                logger.warning("Intent: error in intent classification: %s", exc)

        # If no intent response is playing, check if we should trigger goodbye.
        # Only trigger goodbye if:
        # 1. No intent response is playing, AND
        # 2. The silence period has passed:
        #    - If we have chunks (speech was detected), wait for hangup_time to be set and reached
        #    - If we have no chunks (no speech detected), hangup_time is None means timeout, trigger goodbye
        intent_response_played = getattr(self, "_intent_response_played", False)
        has_chunks = len(chunks) > 0
        if not intent_response_played:
            # Only trigger goodbye if silence period has passed
            if has_chunks:
                # Speech was detected - must wait for hangup_time to be set and reached
                # VAD will set hangup_time based on last_speech_time + silence_after_speech_sec
                hangup_time_reached = (
                    self._hangup_time is not None and current_time >= self._hangup_time
                )
            else:
                # No speech detected - hangup_time is None means timeout (no speech for 10+ seconds)
                # Trigger goodbye immediately in this case
                hangup_time_reached = (
                    self._hangup_time is None or current_time >= self._hangup_time
                )
            if hangup_time_reached:
                logger.info("ASR: no intent response, playing goodbye message")
                self._play_goodbye_message()
            else:
                # Silence period hasn't passed yet, wait for it
                time_until_hangup = (
                    self._hangup_time - current_time if self._hangup_time else None
                )
                logger.debug(
                    "ASR: transcription complete but waiting for silence period "
                    "(%.2fs remaining until hangup_time)",
                    time_until_hangup if time_until_hangup else 0.0,
                )

    def check_playback_status(self) -> None:
        """Check if playback has finished and set hangup time if needed.

        This method orchestrates the playback lifecycle by delegating to
        focused helper methods:
        - _check_intent_response_transition(): Handle intent response -> goodbye
        - _stop_player_and_cleanup(): Stop player when playback ends
        - _process_vad_audio(): Process VAD and update hangup time
        - _handle_asr_completion(): Handle ASR completion and intent classification
        """
        # Check if call is still active
        call_active = False
        try:
            if hasattr(self, "isActive"):
                call_active = self.isActive()
        except Exception:
            call_active = False

        # Check intent response status and trigger goodbye if needed
        # This must be called even if call is inactive to ensure cleanup happens
        self._check_intent_response_transition()

        # Check goodbye message status
        self.check_goodbye_status()

        # If call is inactive and goodbye is finished, skip further processing
        # This prevents infinite loops when user hangs up before goodbye
        if not call_active:
            goodbye_finished = getattr(self, "_goodbye_playback_finished", False)
            intent_finished = hasattr(self, "_intent_response_finished") and getattr(
                self, "_intent_response_finished", False
            )
            # If goodbye is finished and intent is finished, skip further processing
            # This prevents infinite loops after cleanup is complete
            if goodbye_finished and intent_finished:
                return

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
                # Only submit after silence period has passed to confirm speech has ended
                try:
                    self._submit_chunks_for_transcription(chunks, current_time)

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

        # If ASR is complete but goodbye wasn't triggered yet (because hangup_time
        # hadn't been reached), check if we should trigger it now
        # Only check if we have chunks (speech was detected) - if no chunks,
        # goodbye should have been triggered already in _handle_asr_completion
        chunks = self._vad.get_chunks() if (self._vad and self._vad.available) else []
        has_chunks = len(chunks) > 0
        if (
            self._asr_complete
            and not getattr(self, "_intent_response_played", False)
            and not goodbye_requested_or_playing
            and has_chunks  # Only wait for hangup_time if we have chunks
            and self._hangup_time is not None
            and current_time >= self._hangup_time
        ):
            # ASR completed earlier, but hangup_time wasn't reached yet.
            # Now hangup_time has been reached, so trigger goodbye
            logger.info(
                "ASR: hangup_time reached after ASR completion, triggering goodbye message"
            )
            self._play_goodbye_message()

    def _set_hangup_time(self) -> None:
        """Set hangup time (2s after playback finishes)."""
        hangup_delay = getattr(self._acc_ref, "hangup_delay", 2)
        self._hangup_time = time.time() + hangup_delay
        logger.info(
            "Welcome message finished. Will hang up in %s seconds", hangup_delay
        )

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
        current_time = time.time()

        # If ASR is complete (or not enabled) and goodbye needs to be played
        if self._asr_complete:
            result = self._check_intent_and_goodbye_for_hangup()
            if result is None:
                return False  # Intent still playing, wait
            return result

        # Fallback: original hangup logic for cases without ASR or waiting voice
        if self._hangup_time and current_time >= self._hangup_time:
            result = self._check_intent_and_goodbye_for_hangup()
            if result is None:
                return False  # Intent still playing, wait
            return result
        return False
