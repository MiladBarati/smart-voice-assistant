"""Registration and call handling functions."""

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None

from .account import Account
from .config import BotConfig
from .calls import OutCall
from .utils import pump_events, wait_until

logger = logging.getLogger(__name__)


def wait_for_registration(ep: Any, acc: Account, timeout_seconds: int) -> bool:
    """Wait for account registration.

    Args:
        ep: PJSUA2 endpoint instance
        acc: Account instance
        timeout_seconds: Maximum time to wait

    Returns:
        True if registered, False otherwise
    """
    logger.info("Waiting for registration (up to %ds)...", timeout_seconds)

    def _is_registered() -> bool:
        info: Any = acc.getInfo()
        try:
            reg_is_active = getattr(info, "regIsActive", False)
            reg_status = getattr(info, "regStatus", 0)
            return bool(reg_is_active and 200 <= reg_status < 300)
        except Exception:
            return False

    registered = wait_until(ep, _is_registered, timeout_seconds)
    if not registered:
        info: Any = acc.getInfo()
        active = getattr(info, "regIsActive", False)
        status = getattr(info, "regStatus", "unknown")
        logger.warning(
            "Warning: not registered (active=%s code=%s). Continuing...",
            active,
            status,
        )
    return registered


def handle_outbound_call(
    ep: Any, acc: Account, config: BotConfig, stopping: dict
) -> None:
    """Handle outbound call if destination is specified.

    Args:
        ep: PJSUA2 endpoint instance
        acc: Account instance
        config: Bot configuration
        stopping: Shared stopping flag dict
    """
    if not config.dest:
        return

    dest_uri = (
        config.dest
        if config.dest.startswith("sip:")
        else f"sip:{config.dest}@{config.domain}"
    )
    call = OutCall(acc)
    prm = pj.CallOpParam(True)
    logger.info("Dialing: %s", dest_uri)

    # Collect outbound call attempt
    call._collect_event(
        event_type="outbound_call",
        call_state="dialing",
        remote_uri=dest_uri,
        local_uri=f"sip:{config.user}@{config.domain}",
    )

    call.makeCall(dest_uri, prm)

    # Wait for connection or timeout
    connected = wait_until(
        ep,
        lambda: call.connected,
        max(config.wait_seconds, 10),
    )
    if not connected:
        logger.warning("Warning: call not connected within timeout")

    # Optional auto-hangup after connected
    if call.connected and config.hangup_seconds > 0:
        logger.info("Connected. Auto-hangup in %ds", config.hangup_seconds)
        deadline = time.time() + config.hangup_seconds
        while time.time() < deadline and not stopping["flag"]:
            pump_events(ep, 50)
        try:
            call.hangup(pj.CallOpParam())
        except Exception:
            pass

    # Ensure we process teardown
    end_deadline = time.time() + 3
    while time.time() < end_deadline:
        pump_events(ep, 50)


def run_main_loop(ep: Any, acc: Account, stopping: dict) -> None:
    """Run main event loop for receiving calls.

    Args:
        ep: PJSUA2 endpoint instance
        acc: Account instance
        stopping: Shared stopping flag dict
    """
    logger.info("Online: waiting for incoming calls (Ctrl+C to exit)")
    while not stopping["flag"]:
        pump_events(ep, 50)

        # Check for calls that should be hung up
        for call in list(acc.calls.values()):
            try:
                if hasattr(call, "check_playback_status"):
                    call.check_playback_status()

                if hasattr(call, "should_hangup") and call.should_hangup():
                    try:
                        if call.isActive():
                            logger.info("Auto-hanging up after welcome message")
                            op = pj.CallOpParam()
                            call.hangup(op)
                    except Exception as e:
                        logger.error("Hangup error: %s", e, exc_info=True)
            except Exception as e:
                logger.error(
                    "Error in main loop for call %s: %s", call, e, exc_info=True
                )

