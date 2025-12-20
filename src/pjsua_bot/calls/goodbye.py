"""Goodbye playback mixin for call handlers.

Provides `_play_goodbye_message` and `check_goodbye_status` and a small
initializer `init_goodbye_state` to set up internal state used by these
methods. Intended to be used as a mixin alongside a `pj.Call` subclass.
"""

import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GoodbyePlaybackMixin:
    """Mixin providing goodbye playback behavior before hangup."""

    def init_goodbye_state(self) -> None:
        # Goodbye message playback state
        self._goodbye_player: Any = None
        self._goodbye_playback_started: bool = False
        self._goodbye_playback_finished: bool = False
        self._goodbye_stop_time: Optional[float] = None
        self._goodbye_requested: bool = False

        # ASR completion tracking
        self._asr_complete: bool = False
        # Host-provided hangup scheduling timestamp
        self._hangup_time: Optional[float] = None

    # The following methods expect the host class to define:
    #   - _acc_ref, _call_media, _vad, _collect_event, _hangup_time
    #   - and to have pjsua2 imported as pj in its module scope

    def _play_goodbye_message(self: Any) -> None:
        """Play the goodbye message before hanging up."""
        goodbye_file = getattr(self._acc_ref, "goodbye_file", None)
        if not goodbye_file or self._goodbye_requested:
            return

        # Check if call is still active
        call_active = False
        try:
            if hasattr(self, "isActive"):
                call_active = self.isActive()
        except Exception:
            call_active = False

        # If call is inactive, mark goodbye as finished and return
        # This handles the case where user hung up before goodbye could play
        if not call_active:
            logger.debug("Goodbye: call inactive, skipping goodbye message")
            self._goodbye_playback_finished = True
            return

        if not os.path.exists(goodbye_file):
            logger.warning("Goodbye: file not found: %s", goodbye_file)
            # Mark goodbye as finished so we can hang up
            self._goodbye_playback_finished = True
            return

        if not self._call_media:
            logger.warning("Goodbye: no call media available")
            self._goodbye_playback_finished = True
            return

        try:
            self._goodbye_requested = True
            logger.info("Goodbye: playing goodbye message: %s", goodbye_file)

            # Get WAV file duration
            from ..utils import get_wav_duration

            goodbye_duration = get_wav_duration(goodbye_file)
            if goodbye_duration is None:
                goodbye_duration = getattr(self._acc_ref, "message_duration", 3)
                logger.debug("Goodbye: using fallback duration %ds", goodbye_duration)

            # Create player for goodbye message
            import pjsua2 as pj  # local import to avoid module-level dependency

            self._goodbye_player = pj.AudioMediaPlayer()
            # PJMEDIA_FILE_NO_LOOP = 1 prevents looping (False=0 would allow looping)
            self._goodbye_player.createPlayer(goodbye_file, pj.PJMEDIA_FILE_NO_LOOP)
            self._goodbye_player.startTransmit(self._call_media)  # goodbye -> remote

            # Also transmit goodbye message to mixed recorder if it exists
            if getattr(self, "_mixed_recorder", None):
                try:
                    self._goodbye_player.startTransmit(self._mixed_recorder)
                    logger.debug("Goodbye: transmitting to mixed recorder")
                except Exception as e:
                    logger.warning(
                        "Goodbye: error transmitting to mixed recorder: %s", e
                    )

            # Monitor on local speakers
            adm = pj.Endpoint.instance().audDevManager()
            playback = adm.getPlaybackDevMedia()
            # remote -> local speakers (monitor goodbye)
            self._call_media.startTransmit(playback)

            self._goodbye_playback_started = True
            self._goodbye_stop_time = time.time() + goodbye_duration

            # Start tracking bot talk duration
            if hasattr(self, "_start_bot_playback_tracking"):
                try:
                    self._start_bot_playback_tracking()
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning(
                        "Bot tracking: error starting goodbye playback tracking: %s", e
                    )

            # Notify VAD that bot playback started (goodbye message)
            if getattr(self, "_vad", None) and getattr(self._vad, "available", False):
                try:
                    self._vad.set_bot_playback_state(True, time.time)
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning("VAD: error notifying goodbye playback start: %s", e)

            # Collect goodbye playback started event
            try:
                self._collect_event(
                    event_type="goodbye_playback_started",
                    media_type="audio",
                    file_played=goodbye_file,
                )
            except Exception:
                pass

            logger.info(
                "Goodbye: started playing, will stop after %.2f seconds",
                goodbye_duration,
            )

        except Exception as e:
            logger.error("Goodbye: error playing goodbye message: %s", e, exc_info=True)
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
                    # Check if call is still active before attempting port disconnection
                    # If call is disconnected, PJSUA2 has already disconnected ports
                    call_active = False
                    try:
                        if hasattr(self, "isActive"):
                            call_active = self.isActive()
                    except Exception:
                        # Call might be destroyed, assume inactive
                        call_active = False

                    if call_active:
                        # Stop the transmission from goodbye player to call media
                        try:
                            self._goodbye_player.stopTransmit(self._call_media)
                            logger.debug("Goodbye: stopped player transmission")
                        except Exception:
                            # Ports already disconnected, ignore silently
                            pass

                        # Stop the transmission from goodbye player to mixed recorder
                        if getattr(self, "_mixed_recorder", None):
                            try:
                                self._goodbye_player.stopTransmit(self._mixed_recorder)
                                logger.debug(
                                    "Goodbye: stopped transmission to mixed recorder"
                                )
                            except Exception:
                                # Mixed recorder might already be stopped, ignore
                                pass

                    # Check if call is still active before attempting port disconnection
                    # If call is disconnected, PJSUA2 has already disconnected ports
                    call_active = False
                    try:
                        if hasattr(self, "isActive"):
                            call_active = self.isActive()
                    except Exception:
                        # Call might be destroyed, assume inactive
                        call_active = False

                    # FIX: Skip stopping call_media->playback transmission to
                    # avoid PJSUA2 internal "Remove port failed" error
                    # (same fix as in playback_monitor.py)
                    # Also stop the call media to playback transmission
                    # if call_active:
                    #     adm = pj.Endpoint.instance().audDevManager()
                    #     playback = adm.getPlaybackDevMedia()
                    #     try:
                    #         self._call_media.stopTransmit(playback)
                    #     except Exception:
                    #         pass

                    # Destroy the goodbye player
                    self._goodbye_player = None
                    logger.debug("Goodbye: destroyed player")

                except Exception as e:
                    logger.warning("Goodbye: error stopping player transmission: %s", e)

            # Mark goodbye playback finished
            if not self._goodbye_playback_finished:
                logger.info("Goodbye: finished. Will hang up now.")

                # Stop tracking bot talk duration
                if hasattr(self, "_stop_bot_playback_tracking"):
                    try:
                        self._stop_bot_playback_tracking()
                    except Exception as e:  # pragma: no cover - defensive
                        logger.warning(
                            "Bot tracking: error stopping goodbye playback "
                            "tracking: %s",
                            e,
                        )

                # Notify VAD that bot playback finished (goodbye message)
                if getattr(self, "_vad", None) and getattr(
                    self._vad, "available", False
                ):
                    try:
                        self._vad.set_bot_playback_state(False, time.time)
                    except Exception as e:  # pragma: no cover - defensive
                        logger.warning(
                            "VAD: error notifying goodbye playback stop: %s", e
                        )

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
