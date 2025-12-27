"""Shutdown and cleanup orchestration functions."""

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None

from .account import Account
from .cleanup import cleanup_resources
from .utils import pump_events

logger = logging.getLogger(__name__)


def stop_asr_threads(acc: Account) -> None:
    """Stop all ASR worker threads.

    Args:
        acc: Account instance
    """
    logger.info("Stopping all ASR worker threads...")
    calls_copy = dict(getattr(acc, "calls", {}))
    for _call_id, call in calls_copy.items():
        try:
            if hasattr(call, "_stop_asr_thread"):
                try:
                    call._stop_asr_thread()
                except Exception as e:
                    logger.error("ASR: Error stopping thread: %s", e, exc_info=True)
        except Exception:
            pass

    # Force stop any remaining ASR threads
    for thread in threading.enumerate():
        if thread.name == "ASRWorker" and thread.is_alive():
            logger.warning("ASR: Force stopping thread %s", thread.name)
            thread.join(timeout=1.0)


def hangup_all_calls(acc: Account) -> None:
    """Hang up all active calls.

    Args:
        acc: Account instance
    """
    calls_copy = dict(getattr(acc, "calls", {}))
    for _call_id, call in calls_copy.items():
        try:
            is_active = hasattr(call, "isActive") and call.isActive()
        except Exception:
            is_active = False

        if is_active:
            try:
                op = pj.CallOpParam()
                call.hangup(op)
            except Exception:
                pass

        # Drop strong refs to players/recorders
        for attr in (
            "_player",
            "_goodbye_player",
            "_recorder",
            "_outgoing_recorder",
            "_recording_call_media",
            "_outgoing_recording_call_media",
        ):
            if hasattr(call, attr):
                try:
                    setattr(call, attr, None)
                except Exception:
                    pass

    # Clear the calls dict
    try:
        acc.calls.clear()
    except Exception:
        pass


def unregister_account(ep: Any, acc: Account) -> None:
    """Unregister account and pump events.

    Args:
        ep: PJSUA2 endpoint instance
        acc: Account instance
    """
    try:
        logger.info("Unregistering account...")
        acc.setRegistration(False)
        # Pump events to allow unregistration to complete
        end_by = time.time() + 2.0
        while time.time() < end_by:
            try:
                ep.libHandleEvents(50)
            except Exception:
                break
    except Exception as e:
        logger.error("Account unregistration error: %s", e, exc_info=True)


def destroy_transports(ep: Any) -> None:
    """Destroy all transports.

    Args:
        ep: PJSUA2 endpoint instance
    """
    try:
        logger.info("Destroying transports...")
        transports = ep.transportEnum()
        for tp_id in transports:
            try:
                ep.transportClose(tp_id)
            except Exception:
                pass
        # Pump events to allow transport cleanup
        end_by = time.time() + 0.5
        while time.time() < end_by:
            try:
                ep.libHandleEvents(50)
            except Exception:
                break
    except Exception as e:
        logger.error("Transport destruction error: %s", e, exc_info=True)


def shutdown_gracefully(ep: Any, acc: Optional[Account], stopping: dict) -> None:
    """Perform graceful shutdown of all resources.

    Args:
        ep: PJSUA2 endpoint instance
        acc: Account instance (may be None)
        stopping: Shared stopping flag dict
    """
    stopping["cleanup_done"] = False
    try:
        if acc is not None and isinstance(acc, Account):
            unregister_account(ep, acc)
            stop_asr_threads(acc)
            hangup_all_calls(acc)

            # Pump events for teardown
            end_by = time.time() + 1.0
            while time.time() < end_by:
                try:
                    pump_events(ep, 50)
                except Exception:
                    break

            # Clean up resources
            cleanup_resources(acc)

            # Final event pump
            end_by = time.time() + 0.5
            while time.time() < end_by:
                try:
                    pump_events(ep, 50)
                except Exception:
                    break

        destroy_transports(ep)

        # Destroy endpoint - MUST be called from main thread
        logger.info("Destroying endpoint...")
        ep.libDestroy()

    except Exception as e:
        logger.error("Shutdown error: %s", e, exc_info=True)
    finally:
        stopping["cleanup_done"] = True
        logger.info("Shutdown complete")
        try:
            import sys

            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass

