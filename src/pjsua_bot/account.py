"""Account class for PJSUA2 SIP registration and call handling."""

import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional

import pjsua2 as pj

from .utils import generate_unique_id, parse_sip_user


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

        print("***VAD: preloading model before registration...")
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
                    print("***VAD: model preloaded successfully")
                else:
                    error_msg = getattr(
                        self._vad_preloader, "_load_error", "unknown error"
                    )
                    print(f"***VAD: preload failed - {error_msg}")
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(tmp_wav_path):
                        os.unlink(tmp_wav_path)
                except Exception:
                    pass
        except Exception as e:
            print(f"***VAD preload error: {e}")
            import traceback

            traceback.print_exc()

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
        print(f"***OnRegState: {prm.reason}")
        info = self.getInfo()
        print(f"***RegStatus: active={info.regIsActive} code={info.regStatus}")

        # Collect registration event
        # Accept any 2xx status code as success (200, 201, 202, etc.)
        is_success_2xx = (info.regIsActive and 200 <= info.regStatus < 300)
        event_type = (
            "registration_success"
            if is_success_2xx
            else "registration_failed"
        )
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
            print("***Registered successfully")

    def onIncomingCall(self, prm: Any) -> None:  # noqa: N802 - pjsua2 callback name
        """Handle incoming call."""
        print("***IncomingCall: ringing")
        try:
            # Import here to avoid circular dependency
            from .calls import AnyCall

            call = AnyCall(self, prm.callId)
            self.calls[prm.callId] = call  # <-- keep it!

            # Parse caller information early
            try:
                call_info = call.getInfo()
                remote_uri = call_info.remoteUri
                call._caller_number = parse_sip_user(remote_uri)
                print(f"***IncomingCall: caller identified as {call._caller_number}")
            except Exception as e:
                print(f"***IncomingCall: could not parse caller info: {e}")
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
                print("***IncomingCall: auto-answered 200 OK")

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
                print("***IncomingCall: sent 180 Ringing")

                # Collect call ringing event
                self._collect_event(
                    event_type="call_ringing",
                    call_id=str(prm.callId),
                    call_state="ringing",
                    call_code=180,
                )
        except Exception as e:
            print(f"***IncomingCall error: {e}")
            # Collect error event
            self._collect_event(
                event_type="call_error",
                call_id=str(prm.callId),
                call_state="error",
                error=str(e),
            )
