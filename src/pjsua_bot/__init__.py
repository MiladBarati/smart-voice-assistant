"""
PJSUA Bot Package

A comprehensive SIP bot implementation using PJSUA2 library with advanced features:
- Voice Activity Detection (VAD) with Silero integration
- Automatic Speech Recognition (ASR) with Whisper models
- Call recording (incoming/outgoing streams)
- Audio playback with automatic duration detection
- Elasticsearch integration for call logging and metrics
- Real-time speech detection and chunking
- Silence tracking and auto-hangup logic
"""

__version__ = "1.0.0"

from typing import Any

# Import non-pjsua2 dependencies immediately
from .elasticsearch_client import ElasticsearchLogger, es_logger
from .utils import (
    ensure_recording_directory,
    generate_unique_id,
    get_wav_duration,
    parse_sip_user,
    pump_events,
    setup_logging,
    wait_until,
)


# Lazy imports for pjsua2-dependent modules to avoid import errors during
# test collection. These will only be imported when actually accessed
def __getattr__(name: str) -> Any:
    """Lazy import for pjsua2-dependent modules."""
    if name == "Account":
        from .account import Account

        return Account
    if name == "AnyCall":
        from .calls import AnyCall

        return AnyCall
    if name == "OutCall":
        from .calls import OutCall

        return OutCall
    if name == "main":
        from .register_bot import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Account",
    "OutCall",
    "AnyCall",
    "generate_unique_id",
    "parse_sip_user",
    "setup_logging",
    "get_wav_duration",
    "ensure_recording_directory",
    "pump_events",
    "wait_until",
    "ElasticsearchLogger",
    "es_logger",
    "main",
]
