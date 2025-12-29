"""`onCallMediaState` handler extracted from the monolithic `AnyCall`."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from ...utils import (
    DEFAULT_RECORDING_PATH,
    convert_recording_path_to_url,
    ensure_recording_directory,
    parse_sip_user,
)
from ...vad import SileroVAD, VADConfig

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None


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

    def _ensure_recording_directory(self) -> None:
        """Ensure call recording directory exists, creating it if needed."""
        if self._call_recording_dir:
            return

        # Try to get caller number if still unknown
        caller_id = self._caller_number or "unknown"
        if caller_id == "unknown":
            try:
                call_info = self.getInfo()
                remote_uri = call_info.remoteUri
                caller_id = parse_sip_user(remote_uri) or "unknown"
                self._caller_number = caller_id
                logger.info(f"Recording: caller identified as {caller_id}")
            except Exception as exc:
                logger.warning(f"Recording: could not parse caller info: {exc}")

        # Create call-specific directory using timestamp and caller ID
        call_dir_name = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{caller_id}"
        self._call_recording_dir = ensure_recording_directory(
            getattr(
                self._acc_ref,
                "recording_path",
                DEFAULT_RECORDING_PATH,
            ),
            call_id=call_dir_name,
        )

    def _create_recorder(self, file_path: str) -> Any:
        """Create an AudioMediaRecorder with fallback options."""
        recorder = pj.AudioMediaRecorder()
        try:
            # Try with WAV format explicitly
            recorder.createRecorder(file_path, 0, 0)
            logger.debug(f"Recording: createRecorder succeeded for {file_path}")
        except Exception as exc:
            logger.debug(f"Recording: createRecorder failed: {exc}")
            # Try fallback approach
            try:
                recorder.createRecorder(file_path, 0, "")
                logger.debug(
                    f"Recording: createRecorder succeeded with fallback "
                    f"for {file_path}"
                )
            except Exception as exc_fallback:
                logger.error(
                    f"Recording: createRecorder failed with fallback: {exc_fallback}"
                )
                raise exc_fallback
        return recorder

    def _setup_incoming_recording(self, call_media: Any) -> None:
        """Set up incoming audio recording."""
        try:
            self._ensure_recording_directory()
            assert self._call_recording_dir is not None

            self._recording_file = os.path.join(
                self._call_recording_dir, "incoming.wav"
            )
            logger.debug(f"Recording: full file path: {self._recording_file}")

            self._recorder = self._create_recorder(self._recording_file)
            call_media.startTransmit(self._recorder)  # remote → recorder
            self._recording_call_media = call_media
            self._recording_start_time = datetime.utcnow()

            logger.info(f"Recording: started capturing to {self._recording_file}")

            # Initialize VAD when recording starts
            self._initialize_vad()

            # Verify recorder was created successfully
            if self._recorder:
                logger.debug("Recording: AudioMediaRecorder created successfully")
            else:
                logger.error("Recording: ERROR - AudioMediaRecorder creation failed")

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
        except Exception as exc:
            logger.error(f"Recording setup error: {exc}")
            self._collect_event(
                event_type="recording_error",
                media_type="audio",
                error=str(exc),
            )

    def _setup_outgoing_recording(self) -> None:
        """Set up outgoing audio recording (bot's welcome message)."""
        try:
            self._ensure_recording_directory()
            assert self._call_recording_dir is not None

            self._outgoing_recording_file = os.path.join(
                self._call_recording_dir, "outgoing.wav"
            )

            recorder = self._create_recorder(self._outgoing_recording_file)
            if self._player:
                self._player.startTransmit(recorder)  # player → outgoing recorder

            self._outgoing_recording_call_media = self._player
            self._outgoing_recorder = recorder
            self._outgoing_recording_start_time = datetime.utcnow()

            logger.info(
                f"Recording: started capturing outgoing audio to "
                f"{self._outgoing_recording_file}"
            )

            # Collect outgoing recording started event
            self._collect_event(
                event_type="outgoing_recording_started",
                media_type="audio",
                recording_file=(
                    convert_recording_path_to_url(self._outgoing_recording_file)
                    if self._outgoing_recording_file
                    else ""
                ),
            )
        except Exception as exc:
            logger.error(f"Outgoing recording setup error: {exc}")
            self._collect_event(
                event_type="outgoing_recording_error",
                media_type="audio",
                error=str(exc),
            )

    def _setup_mixed_recording(self, call_media: Any) -> None:
        """Set up mixed recording (incoming + outgoing)."""
        try:
            assert self._call_recording_dir is not None
            self._mixed_recording_file = os.path.join(
                self._call_recording_dir, "mixed.wav"
            )

            mixed_recorder = self._create_recorder(self._mixed_recording_file)

            # Transmit both incoming and outgoing to the mixed recorder
            call_media.startTransmit(mixed_recorder)  # incoming → mixed_recorder
            if self._player:
                self._player.startTransmit(mixed_recorder)  # outgoing → mixed_recorder

            self._mixed_recorder = mixed_recorder
            self._mixed_recording_start_time = datetime.utcnow()

            logger.info(
                f"Recording: started capturing mixed audio to "
                f"{self._mixed_recording_file} (incoming + outgoing)"
            )

            # Collect mixed recording started event
            self._collect_event(
                event_type="mixed_recording_started",
                media_type="audio",
                recording_file=(
                    convert_recording_path_to_url(self._mixed_recording_file)
                    if self._mixed_recording_file
                    else ""
                ),
            )
        except Exception as exc:
            logger.error(f"Mixed recording setup error: {exc}")
            self._collect_event(
                event_type="mixed_recording_error",
                media_type="audio",
                error=str(exc),
            )

    def _initialize_vad(self) -> None:
        """Initialize VAD (Voice Activity Detection) if enabled."""
        if not (self._vad_enabled and not self._vad):
            return

        try:
            vad_threshold = float(getattr(self._acc_ref, "vad_threshold", 0.5))
            chunks_output_dir = self._call_recording_dir
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
                logger.info(f"VAD: Silero initialized (threshold={vad_threshold})")
            else:
                error_msg = getattr(self._vad, "_load_error", "unknown error")
                logger.warning(f"VAD: unavailable - {error_msg}")
        except Exception as exc:
            logger.error(f"VAD init error: {exc}")

    def _initialize_asr(self) -> None:
        """Initialize ASR (Automatic Speech Recognition) if enabled."""
        if not self._asr_enabled:
            return

        # Re-check if ASR service is now available
        self._asr = getattr(self._acc_ref, "_asr_service", None)
        self._asr_available = bool(
            getattr(self._acc_ref, "_asr_available", False)
            and self._asr is not None
            and self._asr.available
        )

        if self._asr_available:
            logger.info("ASR: using account service (already loaded)")
            self._start_asr_thread()
        else:
            logger.warning("ASR: service not available (still loading or failed)")

    def _setup_playback(self, call_media: Any, playback: Any) -> None:
        """Set up audio playback to remote side."""
        play_file = getattr(self._acc_ref, "play_file", None)
        if not play_file:
            return

        try:
            # Verify file exists before attempting to play
            if not os.path.exists(play_file):
                logger.error(f"Media player error: file not found: {play_file}")
                self._collect_event(
                    event_type="media_error",
                    media_type="audio",
                    error=f"File not found: {play_file}",
                )
                return

            player = pj.AudioMediaPlayer()
            try:
                player.createPlayer(play_file, pj.PJMEDIA_FILE_NO_LOOP)
                logger.debug(f"Media: player created successfully for: {play_file}")
            except Exception as exc:
                logger.error(f"Media player error: failed to create player: {exc}")
                self._collect_event(
                    event_type="media_error",
                    media_type="audio",
                    error=f"createPlayer failed: {exc}",
                )
                raise

            # Start transmitting audio to remote
            try:
                player.startTransmit(call_media)  # file → remote
                call_media.startTransmit(playback)  # remote → local speakers
                logger.info(f"Media: playing file to remote: {play_file}")
                self._player = player

                # Set up recordings if enabled
                if getattr(self._acc_ref, "enable_recording", False):
                    self._setup_outgoing_recording()
                    self._setup_mixed_recording(call_media)

                # Mark playback as started
                if not self._playback_started:
                    self._playback_started = True
                    logger.info("Welcome message playback started")

                    # Start tracking bot talk duration
                    if hasattr(self, "_start_bot_playback_tracking"):
                        try:
                            self._start_bot_playback_tracking()
                        except Exception as exc:
                            logger.error(
                                f"Bot tracking: error starting playback "
                                f"tracking: {exc}"
                            )

                    # Notify VAD that bot playback started
                    if self._vad and self._vad.available:
                        try:
                            self._vad.set_bot_playback_state(True, time.time)
                        except Exception as exc:
                            logger.error(
                                f"VAD: error notifying bot playback start: {exc}"
                            )

                    # Collect playback started event
                    self._collect_event(
                        event_type="playback_started",
                        media_type="audio",
                        file_played=self._acc_ref.play_file,
                    )

                    # Set a timer to stop the player transmission
                    message_duration = getattr(self._acc_ref, "message_duration", 5)
                    self._schedule_player_stop(message_duration)
                    logger.debug(
                        f"Will stop player after {message_duration:.2f} seconds"
                    )
                    self._call_media = call_media

                    # Start ASR worker thread if enabled
                    self._initialize_asr()

            except Exception as exc:
                logger.error(f"Media player error: failed to start transmission: {exc}")
                self._collect_event(
                    event_type="media_error",
                    media_type="audio",
                    error=f"startTransmit failed: {exc}",
                )
        except Exception as exc:
            logger.error(f"Media player error: {exc}")
            self._collect_event(
                event_type="media_error",
                media_type="audio",
                error=str(exc),
            )

    def onCallMediaState(self, prm: Any) -> None:  # noqa: N802 - PJSUA2 callback name
        """Handle call media state changes."""
        ci = self.getInfo()
        for mi in ci.media:
            if (
                mi.type != pj.PJMEDIA_TYPE_AUDIO
                or mi.status != pj.PJSUA_CALL_MEDIA_ACTIVE
            ):
                continue

            try:
                call_media = self.getAudioMedia(mi.index)
                adm = pj.Endpoint.instance().audDevManager()
                playback = adm.getPlaybackDevMedia()

                # Set up incoming recording if enabled
                if getattr(self._acc_ref, "enable_recording", False):
                    self._setup_incoming_recording(call_media)

                # Set up playback (if configured) or bridge to sound device
                play_file = getattr(self._acc_ref, "play_file", None)
                if play_file:
                    self._setup_playback(call_media, playback)
                else:
                    # Bridge audio to sound device
                    capture = adm.getCaptureDevMedia()
                    call_media.startTransmit(playback)
                    capture.startTransmit(call_media)
                    logger.info("Media: audio bridged to sound device")

                    # Start ASR worker thread if enabled
                    self._initialize_asr()

            except Exception as exc:
                logger.error(f"Media error: {exc}")
