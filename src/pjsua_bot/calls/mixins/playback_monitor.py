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
    def check_playback_status(self) -> None:
        """Check if playback has finished and set hangup time if needed."""
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

        # If VAD is available, process new audio and schedule hangup
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
                    if not self._hangup_time or self._hangup_time < target:
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

        If hangup time is reached and goodbye file exists, play it first.
        Returns True only when it's actually time to hang up
        (after goodbye if applicable).
        """
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
