"""Playback monitoring and hangup logic extracted from `AnyCall`."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any, Callable


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
    _waiting_playback_finished: bool
    _waiting_requested: bool
    _asr_complete: bool
    _stop_player_time: float | None

    if TYPE_CHECKING:

        def check_goodbye_status(self) -> None: ...

        def _play_goodbye_message(self) -> None: ...

        def check_waiting_status(self) -> None: ...

        def _play_waiting_message(self) -> None: ...

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
    def check_playback_status(self) -> None:
        """Check if playback has finished and set hangup time if needed."""
        # Check intent response status (must be checked before goodbye)
        if hasattr(self, "check_intent_response_status"):
            try:
                self.check_intent_response_status()
            except Exception:
                pass  # Ignore errors in intent status check

        # Check if intent response finished and we should play goodbye
        if (
            hasattr(self, "_intent_response_played")
            and getattr(self, "_intent_response_played", False)
            and hasattr(self, "check_intent_response_status")
            and not getattr(self, "_goodbye_requested", False)
        ):
            try:
                intent_finished = self.check_intent_response_status()
                if intent_finished:
                    # Intent response finished, now play goodbye
                    print("***Intent: response finished, triggering goodbye message")
                    self._play_goodbye_message()
            except Exception:
                pass  # If check fails, continue normally

        # Check goodbye message status
        self.check_goodbye_status()
        # Check waiting message status
        self.check_waiting_status()

        if not self._playback_started:
            return

        current_time = time.time()

        # Check if it's time to stop the player transmission
        if (
            self._stop_player_time
            and current_time >= self._stop_player_time
            and not self._playback_finished
        ):
            if self._player and self._call_media:
                try:
                    # Stop the transmission from player to call media
                    self._player.stopTransmit(self._call_media)
                    print("***Stopped player transmission to prevent looping")

                    # Stop the transmission from player to mixed recorder
                    # to prevent the welcome message from being replayed
                    if getattr(self, "_mixed_recorder", None):
                        try:
                            self._player.stopTransmit(self._mixed_recorder)
                            print("***Stopped player transmission to mixed recorder")
                        except Exception:
                            # Mixed recorder might already be stopped, ignore
                            pass

                    # Also stop the call media to playback transmission
                    # to break the audio path
                    import pjsua2 as pj  # local import to avoid module-level dependency

                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    self._call_media.stopTransmit(playback)
                    print("***Stopped call media to playback transmission")

                    # Destroy the player completely
                    self._player = None
                    print("***Destroyed player")

                except Exception as exc:
                    print(f"***Error stopping player transmission: {exc}")

            # Mark playback finished; hangup will be controlled by VAD
            if not self._hangup_time:
                print(
                    "***Welcome message finished. Monitoring caller speech for hangup"
                )

                # Stop tracking bot talk duration
                if hasattr(self, "_stop_bot_playback_tracking"):
                    try:
                        self._stop_bot_playback_tracking()
                    except Exception as exc:  # pragma: no cover - defensive
                        print(
                            (
                                "***Bot tracking: error stopping "
                                f"playback tracking: {exc}"
                            )
                        )

                # Notify VAD that bot playback finished
                if self._vad and self._vad.available:
                    try:
                        self._vad.set_bot_playback_state(False, time.time)
                    except Exception as exc:  # pragma: no cover - defensive
                        print(f"***VAD: error notifying bot playback stop: {exc}")

                # Collect playback finished event
                self._collect_event(
                    event_type="playback_finished",
                    media_type="audio",
                    file_played=getattr(self._acc_ref, "play_file", None),
                )

                self._playback_finished = True
                # Clear stop time to prevent re-running this block
                self._stop_player_time = None

        # If VAD is available, process new audio and handle silence
        if self._vad and self._vad.available and self._recording_file:
            try:
                # Debug: confirm VAD is being called
                if not hasattr(self, "_vad_called"):
                    print(f"***VAD: processing audio from {self._recording_file}")
                    self._vad_called = True

                self._vad.process_new_audio(time.time)
                if self._vad.last_speech_time_monotonic is not None:
                    target = (
                        self._vad.last_speech_time_monotonic
                        + self._silence_after_speech_sec
                    )
                    current_time = time.time()
                    # If silence detected and waiting voice not yet played, play it
                    if (
                        current_time >= target
                        and not self._waiting_requested
                        and not self._waiting_playback_finished
                        and not self._asr_complete
                    ):
                        # Finalize any current chunk before playing waiting voice
                        if self._asr_enabled and self._asr_available:
                            try:
                                # Finalize current chunk if it exists
                                current_chunk = self._vad.get_current_chunk()
                                if current_chunk is not None:
                                    # Force finalize the current chunk
                                    self._vad.finalize_all_chunks(time.time)
                                    print(
                                        "***VAD: finalized current chunk due to silence"
                                    )
                                    # Immediately submit the newly finalized chunk
                                    # for transcription
                                    chunks = self._vad.get_chunks()
                                    if (
                                        chunks
                                        and len(chunks)
                                        > self._last_transcribed_chunk_count
                                    ):
                                        last_chunk = chunks[-1]
                                        if last_chunk.file_path and os.path.exists(
                                            last_chunk.file_path
                                        ):
                                            self._submit_transcription_task(
                                                last_chunk.file_path, len(chunks) - 1
                                            )
                                            self._last_transcribed_chunk_count = len(
                                                chunks
                                            )
                            except Exception as e:
                                print(f"***VAD: error finalizing chunk: {e}")

                        # Play waiting voice instead of setting hangup time
                        self._play_waiting_message()
                        print(
                            "***VAD: silence detected, playing waiting voice. "
                            f"Last speech at {self._vad.last_speech_time_monotonic:.3f}"
                        )
                    elif not self._hangup_time or self._hangup_time < target:
                        # Update hangup time if needed (for cases without waiting voice)
                        self._hangup_time = target
                        print(
                            "***VAD: last speech at "
                            f"{self._vad.last_speech_time_monotonic:.3f}; "
                            f"hangup at {target:.3f}"
                        )

                # Live transcription of newly finalized chunks (non-blocking)
                try:
                    chunks = self._vad.get_chunks()
                    for idx in range(self._last_transcribed_chunk_count, len(chunks)):
                        ch = chunks[idx]
                        if (
                            self._asr_enabled
                            and ch.file_path
                            and os.path.exists(ch.file_path)
                        ):
                            # Re-check ASR availability in case it came online
                            if not self._asr_available:
                                self._asr = getattr(self._acc_ref, "_asr_service", None)
                                self._asr_available = bool(
                                    getattr(self._acc_ref, "_asr_available", False)
                                    and self._asr is not None
                                    and self._asr.available
                                )
                                if self._asr_available:
                                    print(
                                        "***ASR: service became available, starting "
                                        "worker thread"
                                    )
                                    self._start_asr_thread()

                            if self._asr_available:
                                # Submit chunk to worker thread.
                                self._submit_transcription_task(ch.file_path, idx)
                    self._last_transcribed_chunk_count = len(chunks)

                    # Check if ASR transcription is complete
                    # (all chunks submitted and queue is empty)
                    if (
                        self._asr_enabled
                        and self._asr_available
                        and not self._asr_complete
                        and self._waiting_playback_finished
                    ):
                        asr_queue = getattr(self, "_asr_queue", None)
                        if asr_queue is not None:
                            # Check if all chunks have been submitted and queue is empty
                            if (
                                self._last_transcribed_chunk_count == len(chunks)
                                and asr_queue.empty()
                                and asr_queue.unfinished_tasks == 0
                            ):
                                # ASR transcription is complete
                                self._asr_complete = True
                                print("***ASR: transcription complete")

                                # PHASE 1: Classify intent and play response
                                if hasattr(self, "_classify_intent") and hasattr(
                                    self, "_play_intent_response"
                                ):
                                    try:
                                        # Check if intent classification is enabled
                                        if getattr(self, "_intent_enabled", False):
                                            # Classify intent from transcription
                                            classification = self._classify_intent()
                                            if classification:
                                                intent_name, confidence = classification
                                                print(
                                                    f"***Intent: classified intent "
                                                    f"'{intent_name}' "
                                                    f"with confidence {confidence:.2f}"
                                                )

                                                # Play intent response
                                                # Goodbye will be triggered by
                                                # check_playback_status once intent
                                                # response finishes
                                                self._play_intent_response()
                                    except Exception as exc:
                                        print(
                                            f"***Intent: error in intent "
                                            f"classification: {exc}"
                                        )

                                # If no intent response is playing, trigger goodbye
                                # immediately. Otherwise, goodbye will be triggered by
                                # check_playback_status when intent response finishes
                                if not getattr(self, "_intent_response_played", False):
                                    print(
                                        "***ASR: no intent response, "
                                        "playing goodbye message"
                                    )
                                    self._play_goodbye_message()
                except Exception as exc:  # pragma: no cover - defensive
                    print(f"***ASR: live transcription error: {exc}")
            except Exception as exc:  # pragma: no cover - defensive
                print(f"***VAD processing error: {exc}")

    def _set_hangup_time(self) -> None:
        """Set hangup time (2s after playback finishes)."""
        hangup_delay = getattr(self._acc_ref, "hangup_delay", 2)
        self._hangup_time = time.time() + hangup_delay
        print(f"***Welcome message finished. Will hang up in {hangup_delay} seconds")

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
        # If ASR is enabled and we're waiting for it, check completion
        if (
            self._asr_enabled
            and self._asr_available
            and self._waiting_playback_finished
            and not self._asr_complete
        ):
            # Still waiting for ASR to complete, don't hang up yet
            return False

        # If waiting voice finished but ASR is not enabled, skip to goodbye
        if (
            self._waiting_playback_finished
            and not self._asr_enabled
            and not self._asr_complete
        ):
            # ASR not enabled, mark as complete to proceed to goodbye
            self._asr_complete = True

        # If ASR is complete (or not enabled) and goodbye needs to be played
        if self._asr_complete:
            # First check if intent response is playing - wait for it to finish
            if hasattr(self, "_intent_response_played") and getattr(
                self, "_intent_response_played", False
            ):
                if hasattr(self, "check_intent_response_status"):
                    try:
                        intent_finished = self.check_intent_response_status()
                        if not intent_finished:
                            # Intent response is still playing, wait for it to finish
                            return False
                    except Exception:
                        # If check fails, assume intent is finished and proceed
                        pass

            # Intent response finished (or not playing), now check goodbye
            goodbye_file = getattr(self._acc_ref, "goodbye_file", None)
            if (
                goodbye_file
                and not self._goodbye_playback_finished
                and not self._goodbye_requested
            ):
                # ASR complete and intent response finished, need to play goodbye first
                self._play_goodbye_message()
                return False  # Don't hang up yet, goodbye is playing
            if self._goodbye_playback_finished:
                # Goodbye finished, now we can hang up
                return True
            if not goodbye_file:
                # No goodbye file, hang up immediately after ASR and intent response
                return True
            # Goodbye is playing, wait for it to finish
            return False

        # Fallback: original hangup logic for cases without ASR or waiting voice
        if self._hangup_time and time.time() >= self._hangup_time:
            # Check if we need to play goodbye message first
            goodbye_file = getattr(self._acc_ref, "goodbye_file", None)
            if (
                goodbye_file
                and not self._goodbye_playback_finished
                and not self._goodbye_requested
            ):
                # Time to hang up, but need to play goodbye first
                self._play_goodbye_message()
                return False  # Don't hang up yet, goodbye is playing
            if self._goodbye_playback_finished:
                # Goodbye finished, now we can hang up
                return True
            if not goodbye_file:
                # No goodbye file, hang up immediately
                return True
            # Goodbye is playing, wait for it to finish
            return False
        return False
