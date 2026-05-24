"""Account configuration and setup functions."""

import logging
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
from .utils import get_wav_duration

logger = logging.getLogger(__name__)


def create_account_config(config: BotConfig) -> Any:
    """Create account configuration.

    Args:
        config: Bot configuration

    Returns:
        Configured AccountConfig object
    """
    acfg = pj.AccountConfig()
    acfg.idUri = f"sip:{config.user}@{config.domain}"
    acfg.regConfig.registrarUri = f"sip:{config.domain}"

    # NAT/keepalive hardening (best-effort; ignore if not available)
    try:
        acfg.sipConfig.keepAliveIntervalSec = 15
        acfg.natConfig.sipOutbound = 1
        acfg.natConfig.iceEnabled = True
    except Exception:
        pass

    # Credentials
    cred = pj.AuthCredInfo(
        "digest",
        "*",
        config.auth_user or config.user,
        0,
        config.password,
    )
    acfg.sipConfig.authCreds.append(cred)

    # Outbound proxy
    if config.outbound_proxy:
        acfg.sipConfig.proxies.append(config.outbound_proxy)

    # Disable SIP Outbound & ICE temporarily
    try:
        acfg.natConfig.sipOutboundUse = pj.PJSUA_SIP_OUTBOUND_DISABLED
    except AttributeError:
        acfg.natConfig.sipOutboundUse = 0

    try:
        acfg.natConfig.contactRewriteUse = pj.PJSUA_CONTACT_REWRITE_USE_DISABLED
        acfg.natConfig.viaRewriteUse = pj.PJSUA_VIA_REWRITE_USE_DISABLED
    except AttributeError:
        acfg.natConfig.contactRewriteUse = 0
        acfg.natConfig.viaRewriteUse = 0

    try:
        acfg.natConfig.contactUseSrcPort = False
    except AttributeError:
        pass

    return acfg


def configure_account(acc: Account, config: BotConfig) -> None:
    """Configure account instance with settings.

    Args:
        acc: Account instance
        config: Bot configuration
    """
    acc.auto_answer = config.auto_answer
    acc.play_file = config.play_file
    acc.goodbye_file = config.goodbye_file
    acc.hangup_delay = config.hangup_delay
    acc.enable_recording = config.enable_recording
    acc.recording_path = config.recording_path
    acc.enable_vad = config.enable_vad
    acc.silence_after_speech_sec = config.silence_after_speech_sec
    acc.vad_threshold = config.vad_threshold
    acc.enable_asr = config.enable_asr
    acc.username = config.user
    acc.domain = config.domain

    acc.flow_mode = config.flow_mode
    acc.max_satisfaction_retries = config.max_satisfaction_retries
    acc.support_transfer_extension = config.support_transfer_extension

    # Get actual duration from WAV file or use fallback
    if config.play_file:
        actual_duration = get_wav_duration(config.play_file)
        acc.message_duration = actual_duration
        logger.info("Using actual WAV duration: %.2f seconds", actual_duration)
    else:
        acc.message_duration = config.message_duration
