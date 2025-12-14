"""Generic call handler with recording, playback, VAD and ASR capabilities."""

from __future__ import annotations

import time
import json

import pjsua2 as pj

from ..utils import generate_unique_id
from .goodbye import GoodbyePlaybackMixin
from .mixins import (
    ASRSupportMixin,
    CallMediaHandlerMixin,
    CallStateHandlerMixin,
    EventLoggerMixin,
    IntentHandlerMixin,
    PlaybackMonitorMixin,
)
from .recording_cleanup import RecordingCleanupMixin

# #region agent log
_DEBUG_LOG_PATH = "/home/milad/projects/pjsua-installation/.cursor/debug.log"
def _dbg_log(hypothesis: str, location: str, message: str, **data):
    try:
        with open(_DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({"hypothesisId": hypothesis, "location": location, "message": message, "data": data, "timestamp": time.time(), "sessionId": "debug-session"}) + "\n")
    except: pass
# #endregion


class AnyCall(
    EventLoggerMixin,
    ASRSupportMixin,
    IntentHandlerMixin,
    PlaybackMonitorMixin,
    GoodbyePlaybackMixin,
    RecordingCleanupMixin,
    CallStateHandlerMixin,
    CallMediaHandlerMixin,
    pj.Call,
):
    """Generic call handler with recording and playback capabilities."""

    def __init__(self, acc: pj.Account, call_id: int):
        # #region agent log
        _before_super = time.time()
        _dbg_log("B", "any_call.py:before_super_init", "Before pj.Call.__init__", call_id=call_id)
        # #endregion
        super().__init__(acc, call_id)
        # #region agent log
        _after_super = time.time()
        try:
            _info = self.getInfo()
            _state_after_super = _info.stateText
            _status_after_super = _info.lastStatusCode
        except Exception as _e:
            _state_after_super = f"error:{_e}"
            _status_after_super = -1
        _dbg_log("B", "any_call.py:after_super_init", "After pj.Call.__init__", call_id=call_id, state=_state_after_super, status=_status_after_super, super_init_time_ms=(_after_super-_before_super)*1000)
        # #endregion
        self._acc_ref = acc  # keep backref for settings
        self._pjsua_call_id = call_id  # Store call ID early for safe cleanup
        self.unique_call_id = generate_unique_id()

        self._init_event_logger()
        self._init_playback_state()
        self.init_goodbye_state()
        self._init_call_metadata()
        self._init_recording_state()
        self._init_vad_state()
        self._init_asr_support()
        self._init_intent_state()

    # ------------------------------------------------------------------#
    # Internal state initialisation helpers
    # ------------------------------------------------------------------#
    def _init_call_metadata(self) -> None:
        self._start_time_utc = None
        self._end_time_utc = None
        self._direction = None  # inbound/outbound
        self._caller_number = None
        self._callee_ext = None
        self._recording_metadata = None
        # Bot talk duration tracking (fallback when VAD unavailable)
        self._bot_playback_start_time: float | None = None
        self._total_bot_talk_duration: float = 0.0

    def _start_bot_playback_tracking(self) -> None:
        """Start tracking bot playback duration."""
        if self._bot_playback_start_time is None:
            self._bot_playback_start_time = time.time()

    def _stop_bot_playback_tracking(self) -> None:
        """Stop tracking bot playback duration and accumulate total."""
        if self._bot_playback_start_time is not None:
            current_time = time.time()
            duration = current_time - self._bot_playback_start_time
            if duration > 0:
                self._total_bot_talk_duration += duration
            self._bot_playback_start_time = None

    def _get_total_bot_talk_duration(self) -> float:
        """Get total bot talk duration including any ongoing session."""
        total = self._total_bot_talk_duration
        if self._bot_playback_start_time is not None:
            current_time = time.time()
            current_session = current_time - self._bot_playback_start_time
            if current_session > 0:
                total += current_session
        return total

    def _init_recording_state(self) -> None:
        self._recorder = None
        self._recording_file = ""
        self._recording_call_media = None
        self._recording_start_time = None
        self._recording_duration: float = 0.0
        self._call_recording_dir = None
        self._cleanup_done = False

        self._outgoing_recorder = None
        self._outgoing_recording_file = ""
        self._outgoing_recording_call_media = None
        self._outgoing_recording_start_time = None
        self._outgoing_recording_duration: float = 0.0

        self._mixed_recorder = None
        self._mixed_recording_file = ""
        self._mixed_recording_start_time = None
        self._mixed_recording_duration: float = 0.0

    def _init_vad_state(self) -> None:
        self._vad = None
        self._vad_available = False
        self._silence_after_speech_sec = float(
            getattr(self._acc_ref, "silence_after_speech_sec", 3)
        )
        self._vad_enabled = bool(getattr(self._acc_ref, "enable_vad", True))

    # goodbye playback handled by GoodbyePlaybackMixin

    # recording cleanup handled by RecordingCleanupMixin
