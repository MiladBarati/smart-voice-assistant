"""
PJSUA Bot Package

A SIP bot implementation using PJSUA library.
"""

__version__ = "1.0.0"

# Import main components for easy access
from .account import Account
from .calls import AnyCall, OutCall
from .elasticsearch_client import ElasticsearchLogger, es_logger
from .register_bot import main
from .utils import (
    ensure_recording_directory,
    generate_unique_id,
    get_wav_duration,
    parse_sip_user,
    pump_events,
    setup_logging,
    wait_until,
)

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
