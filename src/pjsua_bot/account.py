"""Account class for PJSUA2 SIP registration and call handling."""

import logging
import os
import tempfile
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

try:
    import pjsua2 as pj  # pragma: no cover - depends on runtime env
except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
    pj = None

if TYPE_CHECKING:

    class BaseAccount(pj.Account): ...

elif pj is not None:
    BaseAccount = pj.Account
else:

    class BaseAccount(object):
        pass


from .utils import generate_unique_id, parse_sip_user

logger = logging.getLogger(__name__)


class Account(BaseAccount):
    """SIP Account with incoming call handling and event collection."""

    def __init__(self) -> None:
        if pj is None:
            raise RuntimeError(
                "pjsua2 is required to use Account. "
                "Install/build pjsua2 bindings or run without SIP features."
            )
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

        # Conversation flow settings
        self.enable_conversation_flow: bool = True  # Enable multi-turn conversations
        self.max_followup_questions: int = 2  # Max follow-up questions (+ 1 initial)
        self.support_transfer_extension: Optional[str] = (
            None  # Extension for human support
        )

        # New satisfaction-flow settings. `flow_mode` selects which conversation
        # state machine runs inside `ConversationFlowMixin`:
        #   - "legacy": original any-other-questions + repeat_or_support flow
        #   - "satisfaction": question -> answer -> satisfaction-check loop
        self.flow_mode: str = "legacy"
        # NO answers needed to trigger escalation (only valid as 2 or 3).
        self.max_satisfaction_retries: int = 2

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

    def _handle_call_answer(self, call: Any, op: Any, operation_name: str) -> None:
        """Handle call answer operation with PJ_EPENDING error handling.

        Args:
            call: The call object to answer
            op: CallOpParam with status code and reason
            operation_name: Description of the operation (for logging)
        """
        try:
            call.answer(op)
        except pj.Error as answer_err:
            # PJ_EPENDING (70002) means operation already in progress - not a real error
            if answer_err.status == 70002:
                logger.debug(
                    "IncomingCall: %s already pending (PJ_EPENDING), continuing",
                    operation_name,
                )
            else:
                raise  # Re-raise other errors

    def _reject_call(
        self,
        call: Any,
        call_id: int,
        status_code: int,
        reason: str,
        event_reason: str,
        caller_id: Optional[str] = None,
    ) -> None:
        """Reject a call with the specified status code and reason.

        Args:
            call: The call object to reject
            call_id: The call ID
            status_code: SIP status code (e.g., 403, 486)
            reason: Human-readable reason for rejection
            event_reason: Event reason code for logging
            caller_id: Optional caller ID for event logging
        """
        op = pj.CallOpParam()
        op.statusCode = status_code
        op.reason = reason
        self._handle_call_answer(call, op, f"reject ({status_code})")

        # Collect rejection event
        event_data = {
            "call_id": str(call_id),
            "call_state": "rejected",
            "call_code": status_code,
            "reason": event_reason,
        }
        if caller_id:
            event_data["caller_id"] = caller_id
        self._collect_event("incoming_call_rejected", **event_data)

    def _validate_caller_id(self, caller_number: str) -> tuple[bool, Optional[str]]:
        """Validate that caller ID is in allowed range.

        Args:
            caller_number: The caller number to validate

        Returns:
            Tuple of (is_valid, rejection_reason). If valid, rejection_reason is None.
        """
        try:
            caller_id_int = int(caller_number)
            if caller_id_int < 1001 or caller_id_int > 1010:
                return False, "caller_id_not_allowed"
            return True, None
        except (ValueError, TypeError):
            return False, "invalid_caller_id"

    def _parse_caller_info(self, call: Any) -> str:
        """Parse caller information from call object.

        Args:
            call: The call object

        Returns:
            The caller number, or "unknown" if parsing fails
        """
        try:
            call_info = call.getInfo()
            remote_uri = call_info.remoteUri
            caller_number = parse_sip_user(remote_uri)
            logger.info("IncomingCall: caller identified as %s", caller_number)
            return caller_number
        except Exception as e:
            logger.warning("IncomingCall: could not parse caller info: %s", e)
            return "unknown"

    def _handle_busy_call(self, prm: Any) -> bool:
        """Handle busy call rejection.

        Args:
            prm: Call parameter with callId

        Returns:
            True if call was rejected (busy), False otherwise
        """
        if not self._has_active_call():
            return False

        logger.info("IncomingCall: BUSY - already handling a call, rejecting with 486")

        # Create a temporary call object just to reject it
        from .calls import AnyCall

        temp_call = AnyCall(self, prm.callId)
        self._reject_call(
            call=temp_call,
            call_id=prm.callId,
            status_code=486,
            reason="Busy Here",
            event_reason="busy",
        )
        return True

    def _create_and_validate_call(self, prm: Any) -> Optional[Any]:
        """Create call object and validate caller ID.

        Args:
            prm: Call parameter with callId

        Returns:
            The call object if valid, None if rejected
        """
        from .calls import AnyCall

        call = AnyCall(self, prm.callId)
        self.calls[prm.callId] = call  # <-- keep it!

        # Parse and validate caller information
        caller_number = self._parse_caller_info(call)
        call._caller_number = caller_number

        is_valid, rejection_reason = self._validate_caller_id(caller_number)
        if not is_valid:
            logger.warning(
                "IncomingCall: REJECTED - caller ID '%s' validation failed: %s",
                caller_number,
                rejection_reason,
            )
            event_reason_str = rejection_reason or "unknown"
            self._reject_call(
                call=call,
                call_id=prm.callId,
                status_code=403,
                reason=(
                    "Caller ID not allowed"
                    if rejection_reason == "caller_id_not_allowed"
                    else "Invalid caller ID"
                ),
                event_reason=event_reason_str,
                caller_id=caller_number,
            )
            return None

        return call

    def _answer_call(self, call: Any, call_id: int) -> None:
        """Answer the call (auto-answer or ringing).

        Args:
            call: The call object
            call_id: The call ID
        """
        op = pj.CallOpParam()
        if self.auto_answer:
            op.statusCode = 200
            self._handle_call_answer(call, op, "answer (200)")
            logger.info("IncomingCall: auto-answered 200 OK")

            self._collect_event(
                event_type="call_answered",
                call_id=str(call_id),
                call_state="answered",
                call_code=200,
            )
        else:
            op.statusCode = 180
            self._handle_call_answer(call, op, "ringing (180)")
            logger.info("IncomingCall: sent 180 Ringing")

            self._collect_event(
                event_type="call_ringing",
                call_id=str(call_id),
                call_state="ringing",
                call_code=180,
            )

    def onIncomingCall(self, prm: Any) -> None:  # noqa: N802 - pjsua2 callback name
        """Handle incoming call."""
        logger.info("IncomingCall: ringing")

        try:
            # Check if we're already handling a call - reject if busy
            if self._handle_busy_call(prm):
                return

            # Create call object and validate caller ID
            call = self._create_and_validate_call(prm)
            if call is None:
                return  # Call was rejected due to invalid caller ID

            # Collect incoming call event
            self._collect_event(
                event_type="incoming_call",
                call_id=str(prm.callId),
                call_state="ringing",
                auto_answer=self.auto_answer,
            )

            # Answer the call (auto-answer or ringing)
            self._answer_call(call, prm.callId)

        except Exception as e:
            logger.error("IncomingCall error: %s", e, exc_info=True)
            # Collect error event
            self._collect_event(
                event_type="call_error",
                call_id=str(prm.callId),
                call_state="error",
                error=str(e),
            )
