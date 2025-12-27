"""Main entry point for the SIP registration bot.

This module provides the command-line interface and main orchestration
for the SIP bot. The bot functionality is organized into separate modules:
- config: Configuration management
- endpoint: Endpoint setup and configuration
- account_setup: Account configuration
- services: ASR and Intent service initialization
- registration: Registration and call handling
- shutdown: Graceful shutdown orchestration
- cleanup: Resource cleanup functions
"""

import argparse
import logging
import os
import signal
import sys
import time
from types import FrameType
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None

# Support running both as a module and as a script
if __package__ in (None, ""):
    import os

    # Add parent directory (the 'src' root)
    # so absolute imports work when executed directly
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pjsua_bot.account import Account
    from pjsua_bot.account_setup import configure_account, create_account_config
    from pjsua_bot.config import BotConfig
    from pjsua_bot.elasticsearch_client import es_logger
    from pjsua_bot.endpoint import (
        configure_codecs,
        create_endpoint_config,
        create_transport,
    )
    from pjsua_bot.registration import (
        handle_outbound_call,
        run_main_loop,
        wait_for_registration,
    )
    from pjsua_bot.services import initialize_asr_service, initialize_intent_classifier
    from pjsua_bot.shutdown import shutdown_gracefully
    from pjsua_bot.utils import setup_logging
else:
    from .account import Account
    from .account_setup import configure_account, create_account_config
    from .config import BotConfig
    from .elasticsearch_client import es_logger
    from .endpoint import configure_codecs, create_endpoint_config, create_transport
    from .registration import handle_outbound_call, run_main_loop, wait_for_registration
    from .services import initialize_asr_service, initialize_intent_classifier
    from .shutdown import shutdown_gracefully
    from .utils import setup_logging

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description=(
            "PJSUA2 registration/call bot with proper event pumping and options."
        )
    )
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--domain", required=True, help="Registrar/realm host or domain"
    )
    parser.add_argument("--auth-user", default=None)
    parser.add_argument("--local-port", type=int, default=5060)
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=10,
        help="Time to wait for registration/connect",
    )
    parser.add_argument(
        "--stay-online",
        action="store_true",
        help="Keep endpoint running to receive calls",
    )
    parser.add_argument(
        "--auto-answer",
        action="store_true",
        help="Answer incoming calls with 200 OK (default: True)",
    )
    parser.add_argument(
        "--no-auto-answer",
        action="store_true",
        help="Disable auto-answering of incoming calls",
    )
    parser.add_argument(
        "--dest",
        default=None,
        help="Destination SIP URI or extension (sip:1002@host or just 1002)",
    )
    parser.add_argument(
        "--hangup-seconds",
        type=int,
        default=0,
        help="Auto hangup after N seconds of connection; 0 to disable",
    )
    parser.add_argument(
        "--outbound-proxy",
        default=None,
        help="Outbound proxy URI, e.g. sip:host:5060;lr",
    )
    parser.add_argument(
        "--transport",
        choices=["udp", "tcp", "tls"],
        default="udp",
        help="SIP transport",
    )
    parser.add_argument(
        "--tls-verify",
        action="store_true",
        help="Verify TLS server certificate (when --transport tls)",
    )
    parser.add_argument(
        "--log-level", type=int, default=3, help="Endpoint log level (0-6)"
    )
    parser.add_argument(
        "--play-file",
        default="welcome_message.wav",
        help=(
            "Path to WAV file to play to remote when call media is active "
            "(default: welcome_message.wav)"
        ),
    )
    parser.add_argument(
        "--goodbye-file",
        default="goodbye_voice.wav",
        help="Path to WAV file to play before hanging up (default: goodbye_voice.wav)",
    )
    parser.add_argument(
        "--hangup-delay",
        type=int,
        default=2,
        help="Deprecated: fixed delay; overridden by VAD-based hangup if enabled",
    )
    parser.add_argument(
        "--message-duration",
        type=int,
        default=5,
        help="Fallback duration in seconds if WAV file cannot be read (default: 5)",
    )
    parser.add_argument(
        "--enable-recording",
        action="store_true",
        help="Enable voice capture for incoming calls (default: False)",
    )
    parser.add_argument(
        "--recording-path",
        default=os.getenv("RECORDING_PATH", "./artifacts/recordings"),
        help=(
            "Base directory for storing recorded audio files "
            "(default: ./artifacts/recordings or RECORDING_PATH env var)"
        ),
    )
    parser.add_argument(
        "--enable-vad",
        action="store_true",
        help="Enable Silero VAD-based hangup after caller silence (default: False)",
    )
    parser.add_argument(
        "--silence-after-speech-sec",
        type=float,
        default=3.0,
        help="Seconds of silence after last caller speech to hang up (default: 3.0)",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.5,
        help="Silero VAD speech probability threshold (default: 0.5)",
    )
    parser.add_argument(
        "--enable-asr",
        action="store_true",
        help="Enable ASR for live and final transcription (default: disabled)",
    )
    parser.add_argument(
        "--asr-model",
        type=str,
        default="omniASR_CTC_1B",
        help=(
            "ASR model to use: omniASR_CTC_1B or omniASR_CTC_350M "
            "(default: omniASR_CTC_1B)"
        ),
    )
    parser.add_argument(
        "--enable-intent",
        action="store_true",
        help="Enable intent classification from transcription (default: False)",
    )
    parser.add_argument(
        "--intent-classifier",
        choices=["rule-based", "ollama"],
        default="rule-based",
        help=(
            "Intent classifier to use: rule-based (keyword matching) or "
            "ollama (LLM-based) (default: rule-based)"
        ),
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama API base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="qwen2.5:3b",
        help=(
            "Ollama model name (default: qwen2.5:3b). "
            "Using 1.5b/3b is recommended for GPUs with <8GB VRAM "
            "to coexist with ASR."
        ),
    )
    parser.add_argument(
        "--ollama-use-cpu",
        action="store_true",
        help="Attempt to force CPU usage for Ollama (hint only). "
        "To truly force CPU, set OLLAMA_NUM_GPU=0 before starting Ollama server",
    )
    parser.add_argument(
        "--faq-config",
        type=str,
        default=None,
        help="Path to custom FAQ JSON config file (optional)",
    )

    return parser.parse_args()


def setup_signal_handlers(stopping: dict) -> None:
    """Setup signal handlers for graceful shutdown.

    Args:
        stopping: Shared stopping flag dict
    """

    def _stop_handler(signum: int, frame: Optional[FrameType]) -> None:
        logger.info("Signal %d: stopping...", signum)
        stopping["flag"] = True

        # Set a timeout to force exit if cleanup takes too long (WSL-specific issue)
        def _force_exit() -> None:
            time.sleep(15)  # Wait 15 seconds for cleanup
            cleanup_done = stopping.get("cleanup_done", False)
            if not cleanup_done:
                logger.warning("Force exit: cleanup taking too long, forcing exit...")
                os._exit(1)  # Force exit, bypassing cleanup

        import threading

        threading.Thread(target=_force_exit, daemon=True).start()

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)


def main() -> None:
    """Main entry point for the SIP bot."""
    if pj is None:
        raise RuntimeError(
            "pjsua2 is required to run the SIP bot. "
            "Install/build pjsua2 bindings before running main()."
        )

    args = parse_arguments()
    config = BotConfig.from_args(args)

    # Setup logging
    setup_logging(config.log_level)

    # Test Elasticsearch connection
    logger.info("Testing Elasticsearch connection...")
    health = es_logger.health_check()
    if health.get("status") == "connected":
        logger.info(
            "Elasticsearch connected: %s", health.get("cluster_name", "unknown")
        )
    else:
        err = health.get("error", "unknown error")
        logger.warning("Elasticsearch connection failed: %s", err)

    # Create and initialize endpoint
    ep_cfg = create_endpoint_config(config)
    ep = pj.Endpoint()
    ep.libCreate()
    ep.libInit(ep_cfg)

    # Setup signal handlers
    stopping = {"flag": False, "cleanup_done": False}
    setup_signal_handlers(stopping)

    acc: Optional[Account] = None
    try:
        # Configure codecs before starting library
        configure_codecs(ep)
        ep.libStart()
        ep.audDevManager().setNullDev()

        # Create account configuration
        acfg = create_account_config(config)

        # Create and configure account
        acc = Account()
        configure_account(acc, config)

        # Initialize services before registration
        initialize_asr_service(acc, config)
        initialize_intent_classifier(acc, config)

        # Preload VAD if enabled
        if config.enable_vad:
            acc._preload_vad()

        # Create transport
        create_transport(ep, config)

        # Register account
        logger.info("Creating account and registering %s...", acfg.idUri)
        acc.create(acfg)
        wait_for_registration(ep, acc, config.wait_seconds)

        # Handle outbound call if specified
        handle_outbound_call(ep, acc, config, stopping)

        # Stay online to receive calls
        if config.stay_online and not stopping["flag"]:
            run_main_loop(ep, acc, stopping)

    finally:
        shutdown_gracefully(ep, acc, stopping)


if __name__ == "__main__":
    # Make Ctrl+C exit with a clean code path
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(130)
