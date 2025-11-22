"""Account class for PJSUA2 SIP registration and call handling."""

from datetime import datetime
from typing import Any, Dict

import pjsua2 as pj

from .utils import generate_unique_id, parse_sip_user


class Account(pj.Account):
    """SIP Account with incoming call handling and event collection."""

    def __init__(self) -> None:
        super().__init__()
        self.auto_answer = False
        self.calls: Dict[int, Any] = {}  # keep strong refs to live calls
        self.play_file: str | None = None  # WAV file to play on connect
        # WAV file to play before hanging up
        self.goodbye_file: str | None = None
        # WAV file to play when VAD detects silence (waiting for ASR)
        self.waiting_file: str | None = None
        # Batch logging - collect events during account lifetime
        self._collected_events: list[dict[str, Any]] = []
        # ASR service (shared across all calls for this account)
        self._asr_service: Any | None = None
        self._asr_available: bool = False

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
        event_type = (
            "registration_success"
            if (info.regIsActive and info.regStatus == 200)
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

        if info.regIsActive and info.regStatus == 200:
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
