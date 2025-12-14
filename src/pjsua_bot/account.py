"""Account class for PJSUA2 SIP registration and call handling."""

import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional

import pjsua2 as pj

from .utils import generate_unique_id, parse_sip_user

logger = logging.getLogger(__name__)


class Account(pj.Account):
    """SIP Account with incoming call handling and event collection."""

    def __init__(self) -> None:
        super().__init__()
        self.auto_answer = False
        self.calls: Dict[int, Any] = {}  # keep strong refs to live calls
        self.play_file: Optional[str] = None  # WAV file to play on connect
        # WAV file to play before hanging up
        self.goodbye_file: Optional[str] = None

        # Batch logging - collect events during account lifetime
        self._collected_events: list[dict[str, Any]] = []
        # ASR service (shared across all calls for this account)
        self._asr_service: Optional[Any] = None
        self._asr_available: bool = False
        # Intent classification (shared across all calls for this account)
        self.enable_intent: bool = False
        self._intent_classifier: Optional[Any] = None
        # VAD preloader (dummy instance to preload model)
        self._vad_preloader: Optional[Any] = None

    def _preload_vad(self) -> None:
        """Preload VAD model before calls start to avoid blocking during calls.

        Creates a dummy SileroVAD instance to trigger model loading.
        The model will be cached by torch.hub, so subsequent VAD instances
        will load much faster.
        """
        if not getattr(self, "enable_vad", False):
            return

        logger.info("VAD: preloading model before registration...")
        try:
            from .vad import SileroVAD, VADConfig

            # Create a temporary dummy WAV file for preloading
            # The file doesn't need to contain real audio, just needs to exist
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_wav_path = tmp_file.name
                # Write minimal valid WAV header (44 bytes)
                # This is just a placeholder - the actual file content doesn't matter
                # for model loading
                import struct

                # RIFF header
                tmp_file.write(b"RIFF")
                tmp_file.write(struct.pack("<I", 36))  # File size - 8
                tmp_file.write(b"WAVE")
                # fmt chunk
                tmp_file.write(b"fmt ")
                tmp_file.write(struct.pack("<I", 16))  # fmt chunk size
                tmp_file.write(struct.pack("<H", 1))  # Audio format (PCM)
                tmp_file.write(struct.pack("<H", 1))  # Num channels
                tmp_file.write(struct.pack("<I", 16000))  # Sample rate
                tmp_file.write(struct.pack("<I", 32000))  # Byte rate
                tmp_file.write(struct.pack("<H", 2))  # Block align
                tmp_file.write(struct.pack("<H", 16))  # Bits per sample
                # data chunk
                tmp_file.write(b"data")
                tmp_file.write(struct.pack("<I", 0))  # Data size (empty)

            try:
                vad_threshold = float(getattr(self, "vad_threshold", 0.5))
                self._vad_preloader = SileroVAD(
                    tmp_wav_path,
                    VADConfig(threshold=vad_threshold),
                    chunks_output_dir=None,  # No chunks needed for preloader
                )
                if self._vad_preloader.available:
                    logger.info("VAD: model preloaded successfully")
                else:
                    error_msg = getattr(
                        self._vad_preloader, "_load_error", "unknown error"
                    )
                    logger.warning("VAD: preload failed - %s", error_msg)
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(tmp_wav_path):
                        os.unlink(tmp_wav_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error("VAD preload error: %s", e, exc_info=True)

    def _collect_event(self, event_type: str, **kwargs: Any) -> None:
        """Collect an event for batch logging."""
        event = {
            "event_type": event_type,
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "call_id": generate_unique_id(),
            **kwargs,
        }
        self._collected_events.append(event)

    def onRegState(self, prm: Any) -> None:  # noqa: N802 - pjsua2 callback name
        """Handle registration state changes."""
        logger.debug("OnRegState: %s", prm.reason)
        info = self.getInfo()
        logger.info("RegStatus: active=%s code=%s", info.regIsActive, info.regStatus)

        # Collect registration event
        # Accept any 2xx status code as success (200, 201, 202, etc.)
        is_success_2xx = info.regIsActive and 200 <= info.regStatus < 300
        event_type = "registration_success" if is_success_2xx else "registration_failed"
        self._collect_event(
            event_type=event_type,
            user=getattr(self, "username", "unknown"),
            domain=getattr(self, "domain", "unknown"),
            status=prm.reason,
            code=info.regStatus,
            active=info.regIsActive,
            reason=prm.reason,
        )

        # Accept any 2xx status code as success (200, 201, 202, etc.)
        is_success_2xx = info.regIsActive and 200 <= info.regStatus < 300
        if is_success_2xx:
            logger.info("Registered successfully")

    def _has_active_call(self) -> bool:
        """Check if there's an active call being handled.
        
        Returns True if any call in self.calls is still active (not disconnected).
        """
        active_calls = []
        for call_id, call in list(self.calls.items()):
            try:
                if call.isActive():
                    active_calls.append(call_id)
            except Exception:
                # Call object might be invalid, clean it up
                pass
        
        return len(active_calls) > 0

    def onIncomingCall(self, prm: Any) -> None:  # noqa: N802 - pjsua2 callback name
        """Handle incoming call."""
        logger.info("IncomingCall: ringing")
        try:
            # Check if we're already handling a call - reject if busy
            if self._has_active_call():
                logger.info("IncomingCall: BUSY - already handling a call, rejecting with 486")
                
                # Create a temporary call object just to reject it
                from .calls import AnyCall
                temp_call = AnyCall(self, prm.callId)
                op = pj.CallOpParam()
                op.statusCode = 486  # Busy Here
                op.reason = "Busy Here"
                temp_call.answer(op)
                
                # Collect busy rejection event
                self._collect_event(
                    event_type="incoming_call_rejected",
                    call_id=str(prm.callId),
                    call_state="rejected",
                    call_code=486,
                    reason="busy",
                )
                return

            # Import here to avoid circular dependency
            from .calls import AnyCall

            call = AnyCall(self, prm.callId)
            self.calls[prm.callId] = call  # <-- keep it!

            # Parse caller information early
            try:
                call_info = call.getInfo()
                remote_uri = call_info.remoteUri
                call._caller_number = parse_sip_user(remote_uri)
                logger.info("IncomingCall: caller identified as %s", call._caller_number)
            except Exception as e:
                logger.warning("IncomingCall: could not parse caller info: %s", e)
                call._caller_number = "unknown"

            # Collect incoming call event
            self._collect_event(
                event_type="incoming_call",
                call_id=str(prm.callId),
                call_state="ringing",
                auto_answer=self.auto_answer,
            )

            op = pj.CallOpParam()
            if self.auto_answer:
                op.statusCode = 200
                call.answer(op)
                logger.info("IncomingCall: auto-answered 200 OK")

                # Collect call answered event
                self._collect_event(
                    event_type="call_answered",
                    call_id=str(prm.callId),
                    call_state="answered",
                    call_code=200,
                )
            else:
                op.statusCode = 180
                call.answer(op)
                logger.info("IncomingCall: sent 180 Ringing")

                # Collect call ringing event
                self._collect_event(
                    event_type="call_ringing",
                    call_id=str(prm.callId),
                    call_state="ringing",
                    call_code=180,
                )
        except Exception as e:
            logger.error("IncomingCall error: %s", e, exc_info=True)
            # Collect error event
            self._collect_event(
                event_type="call_error",
                call_id=str(prm.callId),
                call_state="error",
                error=str(e),
            )
