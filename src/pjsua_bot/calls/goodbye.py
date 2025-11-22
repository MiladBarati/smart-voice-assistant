"""Goodbye playback mixin for call handlers.

Provides `_play_goodbye_message` and `check_goodbye_status` and a small
initializer `init_goodbye_state` to set up internal state used by these
methods. Intended to be used as a mixin alongside a `pj.Call` subclass.
"""

import os
import time
from typing import Any


class GoodbyePlaybackMixin:
    """Mixin providing goodbye playback behavior before hangup."""

    def init_goodbye_state(self) -> None:
        # Goodbye message playback state
        self._goodbye_player: Any = None
        self._goodbye_playback_started: bool = False
        self._goodbye_playback_finished: bool = False
        self._goodbye_stop_time: float | None = None
        self._goodbye_requested: bool = False
        # Waiting voice playback state
        self._waiting_player: Any = None
        self._waiting_playback_started: bool = False
        self._waiting_playback_finished: bool = False
        self._waiting_stop_time: float | None = None
        self._waiting_requested: bool = False
        # ASR completion tracking
        self._asr_complete: bool = False
        # Host-provided hangup scheduling timestamp
        self._hangup_time: float | None = None

    # The following methods expect the host class to define:
    #   - _acc_ref, _call_media, _vad, _collect_event, _hangup_time
    #   - and to have pjsua2 imported as pj in its module scope

    def _play_goodbye_message(self: Any) -> None:
        """Play the goodbye message before hanging up."""
        goodbye_file = getattr(self._acc_ref, "goodbye_file", None)
        if not goodbye_file or self._goodbye_requested:
            return

        if not os.path.exists(goodbye_file):
            print(f"***Goodbye: file not found: {goodbye_file}")
            # Mark goodbye as finished so we can hang up
            self._goodbye_playback_finished = True
            return

        if not self._call_media:
            print("***Goodbye: no call media available")
            self._goodbye_playback_finished = True
            return

        try:
            self._goodbye_requested = True
            print(f"***Goodbye: playing goodbye message: {goodbye_file}")

            # Get WAV file duration
            from ..utils import get_wav_duration

            goodbye_duration = get_wav_duration(goodbye_file)
            if goodbye_duration is None:
                goodbye_duration = getattr(self._acc_ref, "message_duration", 3)
                print(f"***Goodbye: using fallback duration {goodbye_duration}s")

            # Create player for goodbye message
            import pjsua2 as pj  # local import to avoid module-level dependency

            self._goodbye_player = pj.AudioMediaPlayer()
            self._goodbye_player.createPlayer(goodbye_file, False)  # No loop
            self._goodbye_player.startTransmit(self._call_media)  # goodbye -> remote

            # Also transmit goodbye message to mixed recorder if it exists
            if getattr(self, "_mixed_recorder", None):
                try:
                    self._goodbye_player.startTransmit(self._mixed_recorder)
                    print("***Goodbye: transmitting to mixed recorder")
                except Exception as e:
                    print(f"***Goodbye: error transmitting to mixed recorder: {e}")

            # Monitor on local speakers
            adm = pj.Endpoint.instance().audDevManager()
            playback = adm.getPlaybackDevMedia()
            # remote -> local speakers (monitor goodbye)
            self._call_media.startTransmit(playback)

            self._goodbye_playback_started = True
            self._goodbye_stop_time = time.time() + goodbye_duration

            # Notify VAD that bot playback started (goodbye message)
            if getattr(self, "_vad", None) and getattr(self._vad, "available", False):
                try:
                    self._vad.set_bot_playback_state(True, time.time)
                except Exception as e:  # pragma: no cover - defensive
                    print(f"***VAD: error notifying goodbye playback start: {e}")

            # Collect goodbye playback started event
            try:
                self._collect_event(
                    event_type="goodbye_playback_started",
                    media_type="audio",
                    file_played=goodbye_file,
                )
            except Exception:
                pass

            print(
                "***Goodbye: started playing, will stop after "
                f"{goodbye_duration:.2f} seconds"
            )

        except Exception as e:
            print(f"***Goodbye: error playing goodbye message: {e}")
            self._goodbye_playback_finished = True
            # Collect error event
            try:
                self._collect_event(
                    event_type="goodbye_playback_error",
                    media_type="audio",
                    error=str(e),
                )
            except Exception:
                pass

    def check_goodbye_status(self: Any) -> None:
        """Check if goodbye playback has finished."""
        if not self._goodbye_playback_started:
            return

        current_time = time.time()

        # Check if it's time to stop the goodbye player
        if (
            self._goodbye_stop_time
            and current_time >= self._goodbye_stop_time
            and not self._goodbye_playback_finished
        ):
            if self._goodbye_player and self._call_media:
                try:
                    import pjsua2 as pj  # local import

                    # Stop the transmission from goodbye player to call media
                    self._goodbye_player.stopTransmit(self._call_media)
                    print("***Goodbye: stopped player transmission")

                    # Stop the transmission from goodbye player to mixed recorder
                    if getattr(self, "_mixed_recorder", None):
                        try:
                            self._goodbye_player.stopTransmit(self._mixed_recorder)
                            print("***Goodbye: stopped transmission to mixed recorder")
                        except Exception:
                            # Mixed recorder might already be stopped, ignore
                            pass

                    # Also stop the call media to playback transmission
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    self._call_media.stopTransmit(playback)

                    # Destroy the goodbye player
                    self._goodbye_player = None
                    print("***Goodbye: destroyed player")

                except Exception as e:
                    print(f"***Goodbye: error stopping player transmission: {e}")

            # Mark goodbye playback finished
            if not self._goodbye_playback_finished:
                print("***Goodbye: finished. Will hang up now.")

                # Notify VAD that bot playback finished (goodbye message)
                if getattr(self, "_vad", None) and getattr(
                    self._vad, "available", False
                ):
                    try:
                        self._vad.set_bot_playback_state(False, time.time)
                    except Exception as e:  # pragma: no cover - defensive
                        print(f"***VAD: error notifying goodbye playback stop: {e}")

                # Collect goodbye playback finished event
                try:
                    self._collect_event(
                        event_type="goodbye_playback_finished",
                        media_type="audio",
                        file_played=getattr(self._acc_ref, "goodbye_file", None),
                    )
                except Exception:
                    pass

                self._goodbye_playback_finished = True
                # Set immediate hangup time now that goodbye is done
                # Small delay to ensure audio finishes
                self._hangup_time = time.time() + 0.5
                self._goodbye_stop_time = None

    def _play_waiting_message(self: Any) -> None:
        """Play the waiting message when VAD detects silence."""
        waiting_file = getattr(self._acc_ref, "waiting_file", None)
        if not waiting_file or self._waiting_requested:
            return

        if not os.path.exists(waiting_file):
            print(f"***Waiting: file not found: {waiting_file}")
            self._waiting_playback_finished = True
            return

        if not self._call_media:
            print("***Waiting: no call media available")
            self._waiting_playback_finished = True
            return

        try:
            self._waiting_requested = True
            print(f"***Waiting: playing waiting message: {waiting_file}")

            # Get WAV file duration
            from ..utils import get_wav_duration

            waiting_duration = get_wav_duration(waiting_file)
            if waiting_duration is None:
                waiting_duration = getattr(self._acc_ref, "message_duration", 3)
                print(f"***Waiting: using fallback duration {waiting_duration}s")

            # Create player for waiting message
            import pjsua2 as pj  # local import to avoid module-level dependency

            self._waiting_player = pj.AudioMediaPlayer()
            self._waiting_player.createPlayer(waiting_file, False)  # No loop
            self._waiting_player.startTransmit(self._call_media)  # waiting -> remote

            # Also transmit waiting message to mixed recorder if it exists
            if getattr(self, "_mixed_recorder", None):
                try:
                    self._waiting_player.startTransmit(self._mixed_recorder)
                    print("***Waiting: transmitting to mixed recorder")
                except Exception as e:
                    print(f"***Waiting: error transmitting to mixed recorder: {e}")

            # Monitor on local speakers
            adm = pj.Endpoint.instance().audDevManager()
            playback = adm.getPlaybackDevMedia()
            # remote -> local speakers (monitor waiting)
            self._call_media.startTransmit(playback)

            self._waiting_playback_started = True
            self._waiting_stop_time = time.time() + waiting_duration

            # Notify VAD that bot playback started (waiting message)
            if getattr(self, "_vad", None) and getattr(self._vad, "available", False):
                try:
                    self._vad.set_bot_playback_state(True, time.time)
                except Exception as e:  # pragma: no cover - defensive
                    print(f"***VAD: error notifying waiting playback start: {e}")

            # Collect waiting playback started event
            try:
                self._collect_event(
                    event_type="waiting_playback_started",
                    media_type="audio",
                    file_played=waiting_file,
                )
            except Exception:
                pass

            print(
                "***Waiting: started playing, will stop after "
                f"{waiting_duration:.2f} seconds"
            )

        except Exception as e:
            print(f"***Waiting: error playing waiting message: {e}")
            self._waiting_playback_finished = True
            # Collect error event
            try:
                self._collect_event(
                    event_type="waiting_playback_error",
                    media_type="audio",
                    error=str(e),
                )
            except Exception:
                pass

    def check_waiting_status(self: Any) -> None:
        """Check if waiting playback has finished."""
        if not self._waiting_playback_started:
            return

        current_time = time.time()

        # Check if it's time to stop the waiting player
        if (
            self._waiting_stop_time
            and current_time >= self._waiting_stop_time
            and not self._waiting_playback_finished
        ):
            if self._waiting_player and self._call_media:
                try:
                    import pjsua2 as pj  # local import

                    # Stop the transmission from waiting player to call media
                    self._waiting_player.stopTransmit(self._call_media)
                    print("***Waiting: stopped player transmission")

                    # Stop the transmission from waiting player to mixed recorder
                    if getattr(self, "_mixed_recorder", None):
                        try:
                            self._waiting_player.stopTransmit(self._mixed_recorder)
                            print("***Waiting: stopped transmission to mixed recorder")
                        except Exception:
                            # Mixed recorder might already be stopped, ignore
                            pass

                    # Also stop the call media to playback transmission
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    self._call_media.stopTransmit(playback)

                    # Destroy the waiting player
                    self._waiting_player = None
                    print("***Waiting: destroyed player")

                except Exception as e:
                    print(f"***Waiting: error stopping player transmission: {e}")

            # Mark waiting playback finished
            if not self._waiting_playback_finished:
                print("***Waiting: finished playback")

                # Notify VAD that bot playback finished (waiting message)
                if getattr(self, "_vad", None) and getattr(
                    self._vad, "available", False
                ):
                    try:
                        self._vad.set_bot_playback_state(False, time.time)
                    except Exception as e:  # pragma: no cover - defensive
                        print(f"***VAD: error notifying waiting playback stop: {e}")

                # Collect waiting playback finished event
                try:
                    self._collect_event(
                        event_type="waiting_playback_finished",
                        media_type="audio",
                        file_played=getattr(self._acc_ref, "waiting_file", None),
                    )
                except Exception:
                    pass

                self._waiting_playback_finished = True
                self._waiting_stop_time = None
