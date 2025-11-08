"""Generic call handler with recording, playback, VAD and ASR capabilities."""

import os
import socket
import time
from datetime import datetime
from typing import Any

import pjsua2 as pj

from ..asr import ASRService
from ..elasticsearch_client import es_logger
from ..utils import (
    convert_recording_path_to_url,
    ensure_recording_directory,
    generate_unique_id,
    parse_sip_user,
)
from ..vad import SileroVAD, VADConfig
from .goodbye import GoodbyePlaybackMixin
from .recording_cleanup import RecordingCleanupMixin


class AnyCall(GoodbyePlaybackMixin, RecordingCleanupMixin, pj.Call):
    """Generic call handler with recording and playback capabilities."""

    def __init__(self, acc: pj.Account, call_id: int):
        super().__init__(acc, call_id)
        self._acc_ref = acc  # keep backref for settings
        self.unique_call_id = generate_unique_id()
        self._player: pj.AudioMediaPlayer | None = None
        self._playback_started = False
        self._playback_finished = False
        self._hangup_time: float | None = None
        self._stop_player_time: float | None = None
        self._call_media = None
        # Initialize goodbye playback state via mixin
        self.init_goodbye_state()
        # Call record tracking
        self._start_time_utc: datetime | None = None
        self._end_time_utc: datetime | None = None
        self._direction: str | None = None  # inbound/outbound
        self._caller_number: str | None = None
        self._callee_ext: str | None = None
        # Voice recording infrastructure
        self._recorder: pj.AudioMediaRecorder | None = None
        self._recording_file: str = ""
        self._recording_enabled = False
        self._recording_call_media = None
        self._recording_start_time: datetime | None = (
            None  # Track when recording started
        )
        self._recording_duration: float = 0.0  # Track recording duration in seconds
        self._call_recording_dir: str | None = None  # Call-specific recording directory
        self._cleanup_done = False  # Flag to prevent double cleanup
        # Outgoing audio recording infrastructure
        self._outgoing_recorder: pj.AudioMediaRecorder | None = None
        self._outgoing_recording_file: str = ""
        self._outgoing_recording_call_media: pj.AudioMediaPlayer | None = None
        self._outgoing_recording_start_time: datetime | None = (
            None  # Track when outgoing recording started
        )
        self._outgoing_recording_duration: float = (
            0.0  # Track outgoing recording duration in seconds
        )
        # Mixed audio recording infrastructure (incoming + outgoing combined)
        self._mixed_recorder: pj.AudioMediaRecorder | None = None
        self._mixed_recording_file: str = ""
        self._mixed_recording_start_time: datetime | None = (
            None  # Track when mixed recording started
        )
        self._mixed_recording_duration: float = (
            0.0  # Track mixed recording duration in seconds
        )
        # Batch logging - collect events during call
        self._collected_events: list[dict[str, Any]] = []
        # VAD related
        self._vad: SileroVAD | None = None
        self._silence_after_speech_sec: float = float(
            getattr(self._acc_ref, "silence_after_speech_sec", 3)
        )
        self._vad_enabled: bool = bool(getattr(self._acc_ref, "enable_vad", True))
        # ASR enable flag from account
        self._asr_enabled: bool = bool(getattr(self._acc_ref, "enable_asr", False))

        # ASR integration state
        self._asr: ASRService | None = None
        self._asr_available: bool = False
        self._asr_chunk_texts: list[str] = []
        self._last_transcribed_chunk_count: int = 0

    def _collect_event(self, event_type: str, **kwargs: Any) -> None:
        """Collect an event for batch logging at the end of the call."""
        event = {
            "event_type": event_type,
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "call_id": str(self.getId()) if hasattr(self, "getId") else "unknown",
            **kwargs,
        }
        self._collected_events.append(event)

    def onCallState(self, prm: Any) -> None:  # noqa: N802 - PJSUA2 callback name
        """Handle call state changes."""
        ci = self.getInfo()
        print(f"***CallState: state={ci.stateText} code={ci.lastStatusCode}")

        # Collect call state change event
        self._collect_event(
            event_type="call_state_change",
            call_state=ci.stateText,
            call_code=ci.lastStatusCode,
            state=ci.state,
            state_text=ci.stateText,
            last_status_code=ci.lastStatusCode,
        )

        # Mark start when early state observed
        if self._start_time_utc is None and ci.connectDuration.sec == 0:
            self._start_time_utc = datetime.utcnow()

        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED and self._start_time_utc is None:
            self._start_time_utc = datetime.utcnow()

        # Fill caller/callee and direction from call info
        try:
            remote_uri = ci.remoteUri
            local_uri = ci.localUri
            self._caller_number = parse_sip_user(remote_uri)
            self._callee_ext = parse_sip_user(local_uri)
            # If this account auto-answers incoming -> inbound
            self._direction = "inbound"
        except Exception:
            pass

        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            # Clean up recording early to avoid media disconnect issues
            self._cleanup_recording()

            # Build recording metadata FIRST, before sending call record
            recording_metadata = {}

            # Add incoming recording metadata
            if self._recording_file and os.path.exists(self._recording_file):
                incoming_file_size = os.path.getsize(self._recording_file)
                # Convert local path to URL for logs
                incoming_file_url = convert_recording_path_to_url(self._recording_file)
                recording_metadata["incoming"] = {
                    "file_path": incoming_file_url,
                    "file_size_bytes": incoming_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "capture_duration": (
                        round(self._recording_duration, 2)
                        if self._recording_duration
                        else 0
                    ),
                }

                # Collect incoming recording finished event
                self._collect_event(
                    event_type="recording_finished",
                    media_type="audio",
                    recording_file=incoming_file_url,
                    file_size_bytes=incoming_file_size,
                    direction="incoming",
                    capture_duration=(
                        round(self._recording_duration, 2)
                        if self._recording_duration
                        else 0
                    ),
                )

            # Add outgoing recording metadata
            if self._outgoing_recording_file and os.path.exists(
                self._outgoing_recording_file
            ):
                outgoing_file_size = os.path.getsize(self._outgoing_recording_file)
                # Convert local path to URL for logs
                outgoing_file_url = convert_recording_path_to_url(
                    self._outgoing_recording_file
                )
                recording_metadata["outgoing"] = {
                    "file_path": outgoing_file_url,
                    "file_size_bytes": outgoing_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "capture_duration": (
                        round(self._outgoing_recording_duration, 2)
                        if self._outgoing_recording_duration
                        else 0
                    ),
                }

                # Collect outgoing recording finished event
                self._collect_event(
                    event_type="outgoing_recording_finished",
                    media_type="audio",
                    recording_file=outgoing_file_url,
                    file_size_bytes=outgoing_file_size,
                    direction="outgoing",
                    capture_duration=(
                        round(self._outgoing_recording_duration, 2)
                        if self._outgoing_recording_duration
                        else 0
                    ),
                )

            # Add mixed recording metadata (incoming + outgoing combined)
            if self._mixed_recording_file and os.path.exists(
                self._mixed_recording_file
            ):
                mixed_file_size = os.path.getsize(self._mixed_recording_file)
                # Convert local path to URL for logs
                mixed_file_url = convert_recording_path_to_url(
                    self._mixed_recording_file
                )
                recording_metadata["mixed"] = {
                    "file_path": mixed_file_url,
                    "file_size_bytes": mixed_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "capture_duration": (
                        round(self._mixed_recording_duration, 2)
                        if self._mixed_recording_duration
                        else 0
                    ),
                }

                # Collect mixed recording finished event
                self._collect_event(
                    event_type="mixed_recording_finished",
                    media_type="audio",
                    recording_file=mixed_file_url,
                    file_size_bytes=mixed_file_size,
                    direction="mixed",
                    capture_duration=(
                        round(self._mixed_recording_duration, 2)
                        if self._mixed_recording_duration
                        else 0
                    ),
                )

            # Store recording metadata for call record
            if recording_metadata:
                self._recording_metadata = recording_metadata

            # Log what file formats are being sent to Elasticsearch
            if recording_metadata:
                for direction, metadata in recording_metadata.items():
                    file_path = str(metadata.get("file_path", ""))
                    file_ext = os.path.splitext(file_path)[1]
                    print(
                        (
                            f"***Elasticsearch: sending {direction} recording as "
                            f"{file_ext.upper()} format: {file_path}"
                        )
                    )

            # Build call record and send as a single log
            try:
                self._end_time_utc = datetime.utcnow()
                start_iso = (
                    self._start_time_utc.isoformat() + "Z"
                    if self._start_time_utc
                    else None
                )
                end = self._end_time_utc
                assert end is not None
                end_iso = end.isoformat() + "Z"
                duration_sec = None
                if self._start_time_utc:
                    duration_sec = int(
                        (self._end_time_utc - self._start_time_utc).total_seconds()
                    )

                # Determine voice capture status and details
                has_incoming_recording = self._recording_file and os.path.exists(
                    self._recording_file
                )
                has_outgoing_recording = (
                    self._outgoing_recording_file
                    and os.path.exists(self._outgoing_recording_file)
                )
                voice_captured = has_incoming_recording or has_outgoing_recording

                # Get primary audio file path (prefer incoming, fallback to outgoing)
                # Convert local paths to URLs for logs
                primary_local_path = (
                    self._recording_file
                    if has_incoming_recording
                    else (
                        self._outgoing_recording_file
                        if has_outgoing_recording
                        else None
                    )
                )
                audio_file_path = (
                    convert_recording_path_to_url(primary_local_path)
                    if primary_local_path
                    else None
                )

                # Calculate total capture duration
                total_capture_duration = 0.0
                if has_incoming_recording and self._recording_duration:
                    total_capture_duration += self._recording_duration
                if has_outgoing_recording and self._outgoing_recording_duration:
                    total_capture_duration += self._outgoing_recording_duration

                # Cap capture duration to not exceed call duration
                if duration_sec and total_capture_duration > duration_sec:
                    total_capture_duration = duration_sec

                # Collect VAD metrics if VAD was enabled and available
                vad_metrics = None
                if self._vad and self._vad.available:
                    try:
                        # Finalize silence tracking at call end
                        self._vad.finalize_silence_tracking(time.time)

                        speech_duration = self._vad.get_speech_duration()
                        chunk_count = self._vad.get_chunk_count()
                        vad_confidence = self._vad.get_vad_confidence()
                        silence_duration = self._vad.get_silence_duration(time.time)

                        vad_metrics = {
                            "speech_duration": speech_duration,
                            "chunk_count": chunk_count,
                            "vad_confidence": vad_confidence,
                            "silence_duration": silence_duration,
                        }
                    except Exception as e:
                        print(f"***Error calculating VAD metrics: {e}")

                call_record = {
                    "event_type": "call_record",
                    "call_id": generate_unique_id(),
                    "caller_number": self._caller_number,
                    "callee_ext": self._callee_ext,
                    "start_time": start_iso,
                    "end_time": end_iso,
                    "duration_sec": duration_sec,
                    "status": "disconnected",
                    "direction": self._direction or "inbound",
                    "media": {
                        "file_played": getattr(self._acc_ref, "play_file", None),
                        "playback_started": self._playback_started,
                        "playback_finished": self._playback_finished,
                    },
                    "recording": (
                        self._recording_metadata if recording_metadata else None
                    ),
                    "voice_captured": voice_captured,
                    "audio_file_path": audio_file_path,
                    "capture_duration": (
                        round(total_capture_duration, 2)
                        if total_capture_duration > 0
                        else 0
                    ),
                    "vad": vad_metrics,  # Add VAD metrics to call record
                    "bot": {
                        "auto_answer": getattr(self._acc_ref, "auto_answer", False),
                        "domain": getattr(self._acc_ref, "domain", None),
                        "user": getattr(self._acc_ref, "username", None),
                    },
                    "host": socket.gethostname(),
                    "ingest_ts": datetime.utcnow().isoformat() + "Z",
                }
                es_logger.log_call_record(call_record)

            except Exception as e:
                print(f"***Error sending single call record: {e}")

            # cleanup: drop strong reference so GC can collect safely now
            try:
                del self._acc_ref.calls[ci.id]  # id is the call-id index in pjsua2
            except Exception:
                # some bindings use self.getId() or store the key from onIncomingCall
                # safe fallback: clear everything if unknown
                self._acc_ref.calls = {
                    k: v for k, v in self._acc_ref.calls.items() if v is not self
                }
            # also release any active player
            self._player = None

    def onCallMediaState(self, prm: Any) -> None:  # noqa: N802 - PJSUA2 callback name
        """Handle call media state changes."""
        ci = self.getInfo()
        for mi in ci.media:
            if (
                mi.type == pj.PJMEDIA_TYPE_AUDIO
                and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE
            ):
                try:
                    call_media = self.getAudioMedia(mi.index)
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()

                    # Voice recording setup (if enabled)
                    if getattr(self._acc_ref, "enable_recording", False):
                        try:
                            # Create call-specific directory if not already created
                            if not self._call_recording_dir:
                                # Try to get caller number if still unknown
                                caller_id = self._caller_number or "unknown"
                                if caller_id == "unknown":
                                    try:
                                        call_info = self.getInfo()
                                        remote_uri = call_info.remoteUri
                                        caller_id = (
                                            parse_sip_user(remote_uri) or "unknown"
                                        )
                                        self._caller_number = caller_id
                                        print(
                                            (
                                                "***Recording: caller identified as "
                                                f"{caller_id}"
                                            )
                                        )
                                    except Exception as e:
                                        print(
                                            (
                                                "***Recording: could not parse caller "
                                                f"info: {e}"
                                            )
                                        )

                                # Create call-specific directory using timestamp
                                # and caller ID
                                call_dir_name = (
                                    f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                    f"_{caller_id}"
                                )
                                self._call_recording_dir = ensure_recording_directory(
                                    getattr(
                                        self._acc_ref, "recording_path", "./recordings"
                                    ),
                                    call_id=call_dir_name,
                                )

                            # Use simple filename since files are in separate
                            # directories
                            assert self._call_recording_dir is not None
                            self._recording_file = os.path.join(
                                self._call_recording_dir, "incoming.wav"
                            )

                            # Debug: Check directory and permissions
                            print(
                                (
                                    "***Recording: directory exists: "
                                    f"{os.path.exists(self._call_recording_dir)}"
                                )
                            )
                            print(
                                (
                                    "***Recording: directory writable: "
                                    f"{os.access(self._call_recording_dir, os.W_OK)}"
                                )
                            )
                            print(
                                f"***Recording: full file path: {self._recording_file}"
                            )

                            # Test: Create a simple test file to verify permissions
                            test_file = os.path.join(
                                self._call_recording_dir, "test_permissions.tmp"
                            )
                            try:
                                with open(test_file, "w") as f:
                                    f.write("test")
                                os.remove(test_file)
                                print("***Recording: directory permissions OK")
                            except Exception as e:
                                print(
                                    (
                                        "***Recording: ERROR - directory permission "
                                        f"test failed: {e}"
                                    )
                                )

                            self._recorder = pj.AudioMediaRecorder()
                            # Try different encoding options
                            try:
                                # Try with WAV format explicitly
                                self._recorder.createRecorder(
                                    self._recording_file, 0, 0
                                )  # 0 = WAV, 0 = no size limit
                                print(
                                    (
                                        "***Recording: createRecorder succeeded with "
                                        "WAV format"
                                    )
                                )
                            except Exception as e:
                                print(f"***Recording: createRecorder failed: {e}")
                                # Try fallback approach
                                try:
                                    self._recorder.createRecorder(
                                        self._recording_file, 0, ""
                                    )  # Original approach
                                    print(
                                        (
                                            "***Recording: createRecorder succeeded "
                                            "with fallback"
                                        )
                                    )
                                except Exception as e2:
                                    print(
                                        (
                                            "***Recording: createRecorder failed with "
                                            f"fallback: {e2}"
                                        )
                                    )
                                    raise e2
                            call_media.startTransmit(
                                self._recorder
                            )  # remote → recorder
                            self._recording_call_media = (
                                call_media  # Store reference for cleanup
                            )
                            self._recording_start_time = (
                                datetime.utcnow()
                            )  # Track recording start time
                            print(
                                (
                                    "***Recording: started capturing to "
                                    f"{self._recording_file}"
                                )
                            )

                            # Initialize VAD when recording starts
                            if self._vad_enabled and not self._vad:
                                try:
                                    vad_threshold = float(
                                        getattr(self._acc_ref, "vad_threshold", 0.5)
                                    )
                                    # Use the same directory as recording for chunks
                                    chunks_output_dir = self._call_recording_dir
                                    self._vad = SileroVAD(
                                        self._recording_file,
                                        VADConfig(threshold=vad_threshold),
                                        chunks_output_dir=chunks_output_dir,
                                    )
                                    if self._vad.available:
                                        print(
                                            (
                                                "***VAD: Silero initialized "
                                                f"(threshold={vad_threshold})"
                                            )
                                        )
                                    else:
                                        error_msg = getattr(
                                            self._vad, "_load_error", "unknown error"
                                        )
                                        print(f"***VAD: unavailable - {error_msg}")
                                except Exception as e:
                                    print(f"***VAD init error: {e}")

                            # Initialize ASR service once recording/VAD is set up
                            # (only if enabled)
                            if self._asr_enabled and self._asr is None:
                                try:
                                    self._asr = ASRService()
                                    self._asr_available = bool(
                                        self._asr and self._asr.available
                                    )
                                    if self._asr_available:
                                        print("***ASR: service initialized")
                                    else:
                                        load_err = getattr(
                                            self._asr, "_load_error", "unknown error"
                                        )
                                        print(("***ASR: unavailable - " f"{load_err}"))
                                except Exception as e:
                                    print(f"***ASR init error: {e}")
                                    self._asr_available = False
                        except Exception as e:
                            print(f"***Recording setup error: {e}")
                            # Collect recording error event
                            self._collect_event(
                                event_type="recording_error",
                                media_type="audio",
                                error=str(e),
                            )

                        # Verify recorder was created successfully
                        if self._recorder:
                            print(
                                "***Recording: AudioMediaRecorder created successfully"
                            )
                            # Check if file was created immediately
                            if self._recording_file and os.path.exists(
                                self._recording_file
                            ):
                                print(
                                    f"***Recording: file created immediately: "
                                    f"{self._recording_file}"
                                )
                            else:
                                print(
                                    (
                                        "***Recording: file not created yet "
                                        "(normal for PJSUA2)"
                                    )
                                )
                        else:
                            print(
                                (
                                    "***Recording: ERROR - AudioMediaRecorder "
                                    "creation failed"
                                )
                            )

                        # Collect recording started event
                        self._collect_event(
                            event_type="recording_started",
                            media_type="audio",
                            recording_file=(
                                convert_recording_path_to_url(self._recording_file)
                                if self._recording_file
                                else ""
                            ),
                        )

                    # If a play file is configured, play it to the remote side
                    if getattr(self._acc_ref, "play_file", None):
                        try:
                            player = pj.AudioMediaPlayer()
                            # Create player with loop=False to play only once
                            player.createPlayer(self._acc_ref.play_file, False)
                            player.startTransmit(call_media)  # file -> remote
                            call_media.startTransmit(
                                playback
                            )  # remote -> local speakers
                            print(
                                f"***Media: playing file to remote: "
                                f"{self._acc_ref.play_file}"
                            )
                            self._player = player

                            # Record outgoing audio (bot's welcome message)
                            # if recording is enabled
                            if getattr(self._acc_ref, "enable_recording", False):
                                try:
                                    # Use the same call-specific directory
                                    # created for incoming recording
                                    if not self._call_recording_dir:
                                        # Create directory if it wasn't created yet
                                        # (shouldn't happen)
                                        call_dir_name = (
                                            f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                                            f"{self._caller_number or 'unknown'}"
                                        )
                                        self._call_recording_dir = (
                                            ensure_recording_directory(
                                                getattr(
                                                    self._acc_ref,
                                                    "recording_path",
                                                    "./recordings",
                                                ),
                                                call_id=call_dir_name,
                                            )
                                        )

                                    # Use simple filename since files are in
                                    # separate directories
                                    assert self._call_recording_dir is not None
                                    self._outgoing_recording_file = os.path.join(
                                        self._call_recording_dir,
                                        "outgoing.wav",
                                    )

                                    recorder = pj.AudioMediaRecorder()
                                    recorder.createRecorder(
                                        self._outgoing_recording_file, 0, 0
                                    )
                                    if self._player:
                                        # player -> outgoing recorder
                                        self._player.startTransmit(recorder)
                                    self._outgoing_recording_call_media = self._player
                                    self._outgoing_recorder = recorder
                                    # Track outgoing recording start time
                                    self._outgoing_recording_start_time = (
                                        datetime.utcnow()
                                    )
                                    print(
                                        (
                                            "***Recording: started capturing "
                                            "outgoing audio to "
                                            f"{self._outgoing_recording_file}"
                                        )
                                    )

                                    # Collect outgoing recording started event
                                    self._collect_event(
                                        event_type="outgoing_recording_started",
                                        media_type="audio",
                                        recording_file=(
                                            convert_recording_path_to_url(
                                                self._outgoing_recording_file
                                            )
                                            if self._outgoing_recording_file
                                            else ""
                                        ),
                                    )

                                    # Set up mixed recording (incoming + outgoing)
                                    try:
                                        # Use the same call-specific directory
                                        assert self._call_recording_dir is not None
                                        self._mixed_recording_file = os.path.join(
                                            self._call_recording_dir,
                                            "mixed.wav",
                                        )

                                        mixed_recorder = pj.AudioMediaRecorder()
                                        mixed_recorder.createRecorder(
                                            self._mixed_recording_file, 0, 0
                                        )

                                        # Transmit both incoming and outgoing to mixed
                                        # Incoming audio: call_media -> mixed_recorder
                                        # (Records what comes FROM the remote caller)
                                        call_media.startTransmit(mixed_recorder)
                                        # Outgoing audio: player -> mixed_recorder
                                        # (This records what goes TO the remote caller)
                                        # Note: Record player directly, not through
                                        # call_media, to avoid capturing audio twice
                                        if self._player:
                                            self._player.startTransmit(mixed_recorder)

                                        self._mixed_recorder = mixed_recorder
                                        # Track mixed recording start time
                                        self._mixed_recording_start_time = (
                                            datetime.utcnow()
                                        )
                                        print(
                                            (
                                                "***Recording: started capturing "
                                                "mixed audio (incoming + outgoing) to "
                                                f"{self._mixed_recording_file}"
                                            )
                                        )

                                        # Collect mixed recording started event
                                        self._collect_event(
                                            event_type="mixed_recording_started",
                                            media_type="audio",
                                            recording_file=(
                                                convert_recording_path_to_url(
                                                    self._mixed_recording_file
                                                )
                                                if self._mixed_recording_file
                                                else ""
                                            ),
                                        )
                                    except Exception as e:
                                        print(f"***Mixed recording setup error: {e}")
                                        self._collect_event(
                                            event_type="mixed_recording_error",
                                            media_type="audio",
                                            error=str(e),
                                        )
                                except Exception as e:
                                    print(f"***Outgoing recording setup error: {e}")
                                    self._collect_event(
                                        event_type="outgoing_recording_error",
                                        media_type="audio",
                                        error=str(e),
                                    )

                            # Mark playback as started and set a timer
                            # to stop transmission
                            if not self._playback_started:
                                self._playback_started = True
                                print("***Welcome message playback started")

                                # Notify VAD that bot playback started
                                if self._vad and self._vad.available:
                                    try:
                                        self._vad.set_bot_playback_state(
                                            True,
                                            time.time,
                                        )
                                    except Exception as e:
                                        print(
                                            (
                                                "***VAD: error notifying bot "
                                                f"playback start: {e}"
                                            )
                                        )

                                # Collect playback started event
                                self._collect_event(
                                    event_type="playback_started",
                                    media_type="audio",
                                    file_played=self._acc_ref.play_file,
                                )

                                # Set a timer to stop the player transmission
                                # after actual duration
                                message_duration = getattr(
                                    self._acc_ref,
                                    "message_duration",
                                    5,
                                )
                                self._stop_player_time = time.time() + message_duration
                                print(
                                    (
                                        "***Will stop player after "
                                        f"{message_duration:.2f} seconds"
                                    )
                                )
                                # Store the call media for later use
                                self._call_media = call_media
                        except Exception as e:
                            print(f"***Media player error: {e}")
                    else:
                        capture = adm.getCaptureDevMedia()
                        call_media.startTransmit(playback)
                        capture.startTransmit(call_media)
                        print("***Media: audio bridged to sound device")
                except Exception as e:
                    print(f"***Media error: {e}")

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
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    self._call_media.stopTransmit(playback)
                    print("***Stopped call media to playback transmission")

                    # Destroy the player completely
                    self._player = None
                    print("***Destroyed player")

                except Exception as e:
                    print(f"***Error stopping player transmission: {e}")

            # Mark playback finished; hangup will be controlled by VAD
            if not self._hangup_time:
                print(
                    "***Welcome message finished. Monitoring caller speech for hangup"
                )

                # Notify VAD that bot playback finished
                if self._vad and self._vad.available:
                    try:
                        self._vad.set_bot_playback_state(False, time.time)
                    except Exception as e:
                        print(f"***VAD: error notifying bot playback stop: {e}")

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

                # Live transcription of newly finalized chunks
                try:
                    chunks = self._vad.get_chunks()
                    for idx in range(self._last_transcribed_chunk_count, len(chunks)):
                        ch = chunks[idx]
                        if (
                            self._asr_enabled
                            and self._asr_available
                            and ch.file_path
                            and os.path.exists(ch.file_path)
                        ):
                            res = (
                                self._asr.transcribe(ch.file_path)
                                if self._asr
                                else None
                            )
                            if res and getattr(res, "text", None):
                                text = res.text.strip()
                                if text:
                                    self._asr_chunk_texts.append(text)
                                    print(f"***ASR: chunk {idx+1} -> {text}")
                    self._last_transcribed_chunk_count = len(chunks)
                except Exception as e:
                    print(f"***ASR: live transcription error: {e}")
            except Exception as e:
                print(f"***VAD processing error: {e}")

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
            elif self._goodbye_playback_finished:
                # Goodbye finished, now we can hang up
                return True
            elif not goodbye_file:
                # No goodbye file, hang up immediately
                return True
            else:
                # Goodbye is playing, wait for it to finish
                return False
        return False

    # goodbye playback handled by GoodbyePlaybackMixin

    # recording cleanup handled by RecordingCleanupMixin
