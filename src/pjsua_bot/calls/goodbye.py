"""Goodbye playback mixin for call handlers.

Provides `_play_goodbye_message` and `check_goodbye_status` and a small
initializer `init_goodbye_state` to set up internal state used by these
methods. Intended to be used as a mixin alongside a `pj.Call` subclass.
"""

from __future__ import annotations

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

    def _is_call_active(self: Any) -> bool:
        """Check if the call is still active, handling exceptions gracefully."""
        try:
            if hasattr(self, "isActive"):
                return bool(self.isActive())
        except Exception:
            # Call might be destroyed, assume inactive
            pass
        return False

    def _mark_goodbye_finished(self: Any) -> None:
        """Mark goodbye playback as finished and schedule hangup."""
        if self._goodbye_playback_finished:
            return

        self._goodbye_playback_finished = True
        # Small delay to ensure audio finishes
        self._hangup_time = time.time() + 0.5
        self._goodbye_stop_time = None

    def _notify_bot_playback_started(self: Any) -> None:
        """Notify VAD and start tracking when bot playback begins."""
        # Start tracking bot talk duration
        if hasattr(self, "_start_bot_playback_tracking"):
            try:
                self._start_bot_playback_tracking()
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(
                    "Bot tracking: error starting goodbye playback tracking: %s", e
                )

        # Notify VAD that bot playback started
        vad = getattr(self, "_vad", None)
        if vad and getattr(vad, "available", False):
            try:
                vad.set_bot_playback_state(True, time.time)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("VAD: error notifying goodbye playback start: %s", e)

    def _notify_bot_playback_finished(self: Any) -> None:
        """Notify VAD and stop tracking when bot playback ends."""
        # Stop tracking bot talk duration
        if hasattr(self, "_stop_bot_playback_tracking"):
            try:
                self._stop_bot_playback_tracking()
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(
                    "Bot tracking: error stopping goodbye playback tracking: %s", e
                )

        # Notify VAD that bot playback finished
        vad = getattr(self, "_vad", None)
        if vad and getattr(vad, "available", False):
            try:
                vad.set_bot_playback_state(False, time.time)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("VAD: error notifying goodbye playback stop: %s", e)

    def _collect_goodbye_event(self: Any, event_type: str, **kwargs: Any) -> None:
        """Collect goodbye-related events, handling errors gracefully."""
        try:
            self._collect_event(event_type=event_type, media_type="audio", **kwargs)
        except Exception:
            pass

    def _stop_player_transmissions(self: Any) -> None:
        """Stop all transmissions from the goodbye player."""
        if not self._goodbye_player or not self._call_media:
            return

        call_active = self._is_call_active()
        if not call_active:
            return

        # Stop transmission to call media
        try:
            self._goodbye_player.stopTransmit(self._call_media)
            logger.debug("Goodbye: stopped player transmission")
        except Exception:
            # Ports already disconnected, ignore silently
            pass

        # Stop transmission to mixed recorder if it exists
        mixed_recorder = getattr(self, "_mixed_recorder", None)
        if mixed_recorder:
            try:
                self._goodbye_player.stopTransmit(mixed_recorder)
                logger.debug("Goodbye: stopped transmission to mixed recorder")
            except Exception:
                # Mixed recorder might already be stopped, ignore
                pass

    def _setup_goodbye_playback(self: Any, goodbye_file: str) -> float:
        """Set up the goodbye player and return the duration."""
        import pjsua2 as pj  # local import to avoid module-level dependency

        # Get WAV file duration
        from ..utils import get_wav_duration

        goodbye_duration = get_wav_duration(goodbye_file)
        if goodbye_duration is None:
            goodbye_duration = getattr(self._acc_ref, "message_duration", 3)
            logger.debug("Goodbye: using fallback duration %ds", goodbye_duration)

        # Create player for goodbye message
        self._goodbye_player = pj.AudioMediaPlayer()
        # PJMEDIA_FILE_NO_LOOP = 1 prevents looping (False=0 would allow looping)
        self._goodbye_player.createPlayer(goodbye_file, pj.PJMEDIA_FILE_NO_LOOP)
        self._goodbye_player.startTransmit(self._call_media)  # goodbye -> remote

        # Also transmit goodbye message to mixed recorder if it exists
        mixed_recorder = getattr(self, "_mixed_recorder", None)
        if mixed_recorder:
            try:
                self._goodbye_player.startTransmit(mixed_recorder)
                logger.debug("Goodbye: transmitting to mixed recorder")
            except Exception as e:
                logger.warning("Goodbye: error transmitting to mixed recorder: %s", e)

        # Monitor on local speakers
        adm = pj.Endpoint.instance().audDevManager()
        playback = adm.getPlaybackDevMedia()
        # remote -> local speakers (monitor goodbye)
        self._call_media.startTransmit(playback)

        return goodbye_duration

    def _play_goodbye_message(self: Any) -> None:
        """Play the goodbye message before hanging up."""
        goodbye_file = getattr(self._acc_ref, "goodbye_file", None)
        if not goodbye_file or self._goodbye_requested:
            return

        # Early validation checks
        if not self._is_call_active():
            logger.debug("Goodbye: call inactive, skipping goodbye message")
            self._mark_goodbye_finished()
            return

        if not os.path.exists(goodbye_file):
            logger.warning("Goodbye: file not found: %s", goodbye_file)
            self._mark_goodbye_finished()
            return

        if not self._call_media:
            logger.warning("Goodbye: no call media available")
            self._mark_goodbye_finished()
            return

        try:
            self._goodbye_requested = True
            logger.info("Goodbye: playing goodbye message: %s", goodbye_file)

            goodbye_duration = self._setup_goodbye_playback(goodbye_file)

            self._goodbye_playback_started = True
            self._goodbye_stop_time = time.time() + goodbye_duration

            self._notify_bot_playback_started()
            self._collect_goodbye_event(
                event_type="goodbye_playback_started", file_played=goodbye_file
            )

            logger.info(
                "Goodbye: started playing, will stop after %.2f seconds",
                goodbye_duration,
            )

        except Exception as e:
            logger.error("Goodbye: error playing goodbye message: %s", e, exc_info=True)
            self._mark_goodbye_finished()
            self._collect_goodbye_event(
                event_type="goodbye_playback_error", error=str(e)
            )

    def check_goodbye_status(self: Any) -> None:
        """Check if goodbye playback has finished."""
        if not self._goodbye_playback_started:
            return

        if self._goodbye_playback_finished:
            return

        current_time = time.time()
        if not self._goodbye_stop_time or current_time < self._goodbye_stop_time:
            return

        # Time to stop the goodbye player
        try:
            self._stop_player_transmissions()
            self._goodbye_player = None
            logger.debug("Goodbye: destroyed player")
        except Exception as e:
            logger.warning("Goodbye: error stopping player transmission: %s", e)

        # Mark goodbye playback finished
        logger.info("Goodbye: finished. Will hang up now.")
        self._notify_bot_playback_finished()
        self._collect_goodbye_event(
            event_type="goodbye_playback_finished",
            file_played=getattr(self._acc_ref, "goodbye_file", None),
        )
        self._mark_goodbye_finished()
