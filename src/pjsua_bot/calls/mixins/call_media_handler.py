"""`onCallMediaState` handler extracted from the monolithic `AnyCall`."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None

from ...utils import (
    convert_recording_path_to_url,
    ensure_recording_directory,
    parse_sip_user,
)
from ...vad import SileroVAD, VADConfig


class CallMediaHandlerMixin:
    """Implements the PJSUA `onCallMediaState` callback."""

    _acc_ref: Any
    _player: Any | None
    _mixed_recorder: Any | None
    _recorder: Any | None
    _recording_call_media: Any | None
    _outgoing_recorder: Any | None
    _outgoing_recording_call_media: Any | None
    _outgoing_recording_file: str
    _outgoing_recording_start_time: datetime | None
    _outgoing_recording_duration: float
    _mixed_recording_file: str
    _mixed_recording_duration: float
    _mixed_recording_start_time: datetime | None
    _call_media: Any | None
    _recording_file: str
    _call_recording_dir: str | None
    _caller_number: str | None
    _playback_started: bool
    _playback_finished: bool
    _asr_enabled: bool
    _asr_available: bool
    _asr: Any | None
    _recording_start_time: datetime | None
    _recording_duration: float
    _cleanup_done: bool
    _collect_event: Callable[..., None]
    _start_asr_thread: Callable[[], None]
    _submit_transcription_task: Callable[[str, int], None]
    _last_transcribed_chunk_count: int
    _vad: SileroVAD | None
    _vad_enabled: bool
    _hangup_time: float | None

    if TYPE_CHECKING:

        def getInfo(self) -> Any: ...  # noqa: N802

        def getAudioMedia(self, index: int) -> Any: ...  # noqa: N802

        def _cleanup_recording(self) -> None: ...

        def _schedule_player_stop(self, delay_seconds: float) -> None: ...

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
                                    except Exception as exc:
                                        print(
                                            (
                                                "***Recording: could not parse caller "
                                                f"info: {exc}"
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
                                with open(test_file, "w", encoding="utf-8") as handle:
                                    handle.write("test")
                                os.remove(test_file)
                                print("***Recording: directory permissions OK")
                            except Exception as exc:
                                print(
                                    (
                                        "***Recording: ERROR - directory permission "
                                        f"test failed: {exc}"
                                    )
                                )

                            self._recorder = pj.AudioMediaRecorder()
                            # Try different encoding options
                            try:
                                # Try with WAV format explicitly
                                self._recorder.createRecorder(
                                    self._recording_file, 0, 0
                                )
                                print(
                                    (
                                        "***Recording: createRecorder succeeded with "
                                        "WAV format"
                                    )
                                )
                            except Exception as exc:
                                print(f"***Recording: createRecorder failed: {exc}")
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
                                except Exception as exc_fallback:
                                    print(
                                        (
                                            "***Recording: createRecorder failed with "
                                            f"fallback: {exc_fallback}"
                                        )
                                    )
                                    raise exc_fallback
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
                                    # Keep WAV files if ASR is enabled
                                    # (ASR needs WAV format)
                                    keep_wav_for_asr = self._asr_enabled
                                    self._vad = SileroVAD(
                                        self._recording_file,
                                        VADConfig(
                                            threshold=vad_threshold,
                                            keep_wav_for_asr=keep_wav_for_asr,
                                        ),
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
                                except Exception as exc:
                                    print(f"***VAD init error: {exc}")

                            # ASR initialization is deferred until after playback setup
                            # to avoid blocking the media setup
                        except Exception as exc:
                            print(f"***Recording setup error: {exc}")
                            # Collect recording error event
                            self._collect_event(
                                event_type="recording_error",
                                media_type="audio",
                                error=str(exc),
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
                    play_file = getattr(self._acc_ref, "play_file", None)
                    if play_file:
                        try:
                            # Verify file exists before attempting to play
                            if not os.path.exists(play_file):
                                print(
                                    (
                                        "***Media player error: file not found: "
                                        f"{play_file}"
                                    )
                                )
                                self._collect_event(
                                    event_type="media_error",
                                    media_type="audio",
                                    error=f"File not found: {play_file}",
                                )
                            else:
                                player = pj.AudioMediaPlayer()
                                # Create player with PJMEDIA_FILE_NO_LOOP to
                                # play only once
                                try:
                                    player.createPlayer(
                                        play_file, pj.PJMEDIA_FILE_NO_LOOP
                                    )
                                    print(
                                        "***Media: player created successfully for:",
                                        play_file,
                                    )
                                except Exception as exc:
                                    print(
                                        (
                                            "***Media player error: failed to create "
                                            f"player: {exc}"
                                        )
                                    )
                                    self._collect_event(
                                        event_type="media_error",
                                        media_type="audio",
                                        error=f"createPlayer failed: {exc}",
                                    )
                                    raise  # Re-raise to skip startTransmit

                                # Start transmitting audio to remote
                                try:
                                    player.startTransmit(call_media)  # file -> remote
                                    call_media.startTransmit(
                                        playback
                                    )  # remote -> local speakers
                                    print(
                                        f"***Media: playing file to remote: {play_file}"
                                    )
                                    self._player = player

                                    # Only set up recording and mark playback
                                    # if player succeeded
                                    # Record outgoing audio (bot's welcome message)
                                    # if recording is enabled
                                    if getattr(
                                        self._acc_ref, "enable_recording", False
                                    ):
                                        try:
                                            # Use the same call-specific directory
                                            # created for incoming recording
                                            if not self._call_recording_dir:
                                                # Create directory if it wasn't created
                                                # yet (shouldn't happen)
                                                timestamp = datetime.now().strftime(
                                                    "%Y%m%d_%H%M%S"
                                                )
                                                caller_number = (
                                                    self._caller_number or "unknown"
                                                )
                                                call_dir_name = (
                                                    f"call_{timestamp}_{caller_number}"
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
                                            self._outgoing_recording_file = (
                                                os.path.join(
                                                    self._call_recording_dir,
                                                    "outgoing.wav",
                                                )
                                            )

                                            recorder = pj.AudioMediaRecorder()
                                            recorder.createRecorder(
                                                self._outgoing_recording_file, 0, 0
                                            )
                                            if self._player:
                                                # player -> outgoing recorder
                                                self._player.startTransmit(recorder)
                                            self._outgoing_recording_call_media = (
                                                self._player
                                            )
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

                                            # Set up mixed recording
                                            # (incoming + outgoing)
                                            try:
                                                # Use the same call-specific directory
                                                assert (
                                                    self._call_recording_dir is not None
                                                )
                                                self._mixed_recording_file = (
                                                    os.path.join(
                                                        self._call_recording_dir,
                                                        "mixed.wav",
                                                    )
                                                )

                                                mixed_recorder = pj.AudioMediaRecorder()
                                                mixed_recorder.createRecorder(
                                                    self._mixed_recording_file, 0, 0
                                                )

                                                # Transmit both incoming and outgoing to
                                                # the mixed recorder
                                                # Incoming audio:
                                                # call_media -> mixed_recorder
                                                # Records audio from the remote caller
                                                call_media.startTransmit(mixed_recorder)
                                                # Outgoing audio:
                                                # player -> mixed_recorder
                                                # Records audio sent to caller.
                                                # Record player directly. Avoid
                                                # using call_media; prevents duplicates.
                                                if self._player:
                                                    self._player.startTransmit(
                                                        mixed_recorder
                                                    )

                                                self._mixed_recorder = mixed_recorder
                                                # Track mixed recording start time
                                                self._mixed_recording_start_time = (
                                                    datetime.utcnow()
                                                )
                                                print(
                                                    "***Recording: started capturing "
                                                    "mixed audio to",
                                                    self._mixed_recording_file,
                                                    "(incoming + outgoing)",
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
                                            except Exception as exc:
                                                print(
                                                    "***Mixed recording setup error:",
                                                    exc,
                                                )
                                                self._collect_event(
                                                    event_type="mixed_recording_error",
                                                    media_type="audio",
                                                    error=str(exc),
                                                )
                                        except Exception as exc:
                                            print(
                                                "***Outgoing recording setup error:",
                                                exc,
                                            )
                                            self._collect_event(
                                                event_type="outgoing_recording_error",
                                                media_type="audio",
                                                error=str(exc),
                                            )

                                    # Mark playback as started and set a timer
                                    # to stop transmission
                                    if not self._playback_started:
                                        self._playback_started = True
                                        print("***Welcome message playback started")

                                        # Start tracking bot talk duration
                                        if hasattr(
                                            self, "_start_bot_playback_tracking"
                                        ):
                                            try:
                                                self._start_bot_playback_tracking()
                                            except Exception as exc:
                                                print(
                                                    "***Bot tracking: error starting "
                                                    f"playback tracking: {exc}"
                                                )

                                        # Notify VAD that bot playback started
                                        if self._vad and self._vad.available:
                                            try:
                                                self._vad.set_bot_playback_state(
                                                    True,
                                                    time.time,
                                                )
                                            except Exception as exc:
                                                print(
                                                    (
                                                        "***VAD: error notifying bot "
                                                        f"playback start: {exc}"
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
                                        self._schedule_player_stop(message_duration)
                                        print(
                                            (
                                                "***Will stop player after "
                                                f"{message_duration:.2f} seconds"
                                            )
                                        )
                                        # Store the call media for later use
                                        self._call_media = call_media

                                        # Start ASR worker thread if enabled.
                                        # Account-level ASR may still be loading.
                                        # Check availability again before use.
                                        if self._asr_enabled:
                                            # Re-check if ASR service is now available
                                            self._asr = getattr(
                                                self._acc_ref, "_asr_service", None
                                            )
                                            self._asr_available = bool(
                                                getattr(
                                                    self._acc_ref,
                                                    "_asr_available",
                                                    False,
                                                )
                                                and self._asr is not None
                                                and self._asr.available
                                            )
                                            if self._asr_available:
                                                print("***ASR: using account service")
                                                print("***ASR: already loaded")
                                                # Start worker thread for
                                                # non-blocking transcription
                                                self._start_asr_thread()
                                            else:
                                                print("***ASR: service not available")
                                                print("***ASR: still loading or failed")
                                except Exception as exc:
                                    print(
                                        "***Media player error: failed to start "
                                        "transmission:",
                                        exc,
                                    )
                                    self._collect_event(
                                        event_type="media_error",
                                        media_type="audio",
                                        error=f"startTransmit failed: {exc}",
                                    )
                        except Exception as exc:
                            print(f"***Media player error: {exc}")
                            self._collect_event(
                                event_type="media_error",
                                media_type="audio",
                                error=str(exc),
                            )
                    else:
                        capture = adm.getCaptureDevMedia()
                        call_media.startTransmit(playback)
                        capture.startTransmit(call_media)
                        print("***Media: audio bridged to sound device")

                        # Start ASR worker thread if enabled.
                        # Account-level ASR may still be loading.
                        # Check availability again before use.
                        if self._asr_enabled:
                            # Re-check if ASR service is now available
                            self._asr = getattr(self._acc_ref, "_asr_service", None)
                            self._asr_available = bool(
                                getattr(self._acc_ref, "_asr_available", False)
                                and self._asr is not None
                                and self._asr.available
                            )
                            if self._asr_available:
                                print(
                                    "***ASR: using account-level service",
                                    "(already loaded)",
                                )
                                # Start worker thread for non-blocking transcription
                                self._start_asr_thread()
                            else:
                                print(
                                    "***ASR: enabled but service not available "
                                    "(still loading or failed)"
                                )
                except Exception as exc:
                    print(f"***Media error: {exc}")
