"""Endpoint configuration and setup functions."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None

from .config import BotConfig

logger = logging.getLogger(__name__)


def create_endpoint_config(config: BotConfig) -> Any:
    """Create and configure endpoint configuration.

    Args:
        config: Bot configuration

    Returns:
        Configured EpConfig object
    """
    ep_cfg = pj.EpConfig()
    ep_cfg.logConfig.level = config.log_level
    med = ep_cfg.medConfig
    med.clockRate = 16000
    med.sndClockRate = 16000
    med.channelCount = 1
    med.audioFramePtime = 20
    med.ptime = 20
    med.quality = 10
    med.noVad = False  # save bandwidth under loss
    med.ecTailLen = 512
    med.ecOptions = 1  # Ensure echo cancellation is enabled
    med.jbInit = 100
    med.jbMinPre = 80
    med.jbMaxPre = 300
    med.jbMax = 500
    return ep_cfg


def configure_codecs(ep: Any) -> None:
    """Configure codec priorities.

    Args:
        ep: PJSUA2 endpoint instance
    """
    try:
        codec_priorities = [
            # Wideband codecs (prefer these)
            ("speex/32000/1", 255),  # Ultra-wideband Speex (32kHz)
            ("speex/16000/1", 250),  # Wideband Speex (16kHz)
            ("G722/16000/1", 240),  # G.722 wideband
            ("L16/44100/1", 200),  # Uncompressed
            # Narrowband codecs (lower priority - fallbacks)
            ("PCMU/8000/1", 128),  # G.711 μ-law
            ("PCMA/8000/1", 120),  # G.711 A-law
            ("speex/8000/1", 100),  # Speex narrowband
            ("GSM/8000/1", 80),  # GSM
            ("iLBC/8000/1", 70),  # iLBC
        ]

        for codec_id, priority in codec_priorities:
            try:
                ep.codecSetPriority(codec_id, priority)
                logger.debug("Codec priority set: %s to %d", codec_id, priority)
            except Exception:
                pass  # Ignore if not available

        # Disable unwanted codecs
        unwanted_codecs = ["GSM/8000/1", "iLBC/8000/1"]
        for codec_id in unwanted_codecs:
            try:
                ep.codecSetPriority(codec_id, 0)  # 0 = disabled
                logger.debug("Codec disabled: %s", codec_id)
            except Exception:
                pass  # Ignore if not available

    except Exception as e:
        logger.warning("Codec priority config warning: %s", e)


def create_transport(ep: Any, config: BotConfig) -> None:
    """Create SIP transport.

    Args:
        ep: PJSUA2 endpoint instance
        config: Bot configuration
    """
    sip_tp_config = pj.TransportConfig()
    sip_tp_config.port = config.local_port

    if config.transport == "udp":
        ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sip_tp_config)
        logger.info("Transport: UDP %d", config.local_port)
    elif config.transport == "tcp":
        ep.transportCreate(pj.PJSIP_TRANSPORT_TCP, sip_tp_config)
        logger.info("Transport: TCP %d", config.local_port)
    else:  # TLS
        tls_cfg = pj.TlsConfig()
        tls_cfg.verifyServer = config.tls_verify
        sip_tp_config.tlsConfig = tls_cfg
        ep.transportCreate(pj.PJSIP_TRANSPORT_TLS, sip_tp_config)
        logger.info("Transport: TLS %d verify=%s", config.local_port, config.tls_verify)

