"""Service initialization functions for ASR and Intent classification."""

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .account import Account
from .config import BotConfig

logger = logging.getLogger(__name__)


def initialize_asr_service(acc: Account, config: BotConfig) -> None:
    """Initialize ASR service if enabled.

    Args:
        acc: Account instance
        config: Bot configuration
    """
    if not config.enable_asr:
        return

    logger.info("ASR: initializing service before registration...")
    try:
        if __package__ in (None, ""):
            from pjsua_bot.asr import ASRConfig, ASRService
        else:
            from .asr import ASRConfig, ASRService

        asr_config = ASRConfig(model_name=config.asr_model)
        acc._asr_service = ASRService(config=asr_config)
        acc._asr_available = bool(acc._asr_service and acc._asr_service.available)
        if acc._asr_available:
            logger.info("ASR: service initialized and ready")
        else:
            load_err = getattr(acc._asr_service, "_load_error", "unknown error")
            logger.warning("ASR: unavailable - %s", load_err)
    except Exception as e:
        logger.error("ASR init error: %s", e, exc_info=True)
        acc._asr_available = False


def initialize_intent_classifier(acc: Account, config: BotConfig) -> None:
    """Initialize intent classifier if enabled.

    Args:
        acc: Account instance
        config: Bot configuration
    """
    if not config.enable_intent:
        return

    logger.info("Intent: initializing classifier before registration...")
    try:
        if __package__ in (None, ""):
            from pjsua_bot.intent.classifier import RuleBasedClassifier
            from pjsua_bot.intent.faq_config import FAQS
            from pjsua_bot.intent.ollama_classifier import OllamaClassifier
        else:
            from .intent.classifier import RuleBasedClassifier
            from .intent.faq_config import FAQS
            from .intent.ollama_classifier import OllamaClassifier

        # Load custom FAQ config if provided
        faqs = FAQS
        if config.faq_config and os.path.exists(config.faq_config):
            import json

            with open(config.faq_config, "r", encoding="utf-8") as f:
                faqs = json.load(f)
            logger.info("Intent: loaded custom FAQ config from %s", config.faq_config)
        elif config.faq_config:
            logger.warning(
                "Intent: warning: FAQ config file not found: %s, using default",
                config.faq_config,
            )

        # Create classifier instance
        if config.intent_classifier == "ollama":
            logger.info(
                "Intent: using Ollama classifier (model: %s)", config.ollama_model
            )
            acc._intent_classifier = OllamaClassifier(
                ollama_url=config.ollama_url,
                model=config.ollama_model,
                faqs=faqs,
                use_cpu=config.ollama_use_cpu,
            )
            if config.ollama_use_cpu:
                logger.info(
                    "Intent: CPU mode requested. "
                    "Note: Set OLLAMA_NUM_GPU=0 before starting "
                    "Ollama server for true CPU mode"
                )
            logger.info(
                "Intent: Ollama classifier initialized at %s", config.ollama_url
            )
        else:
            logger.info("Intent: using rule-based classifier")
            acc._intent_classifier = RuleBasedClassifier(faqs=faqs)

        acc.enable_intent = True
        logger.info("Intent: classifier initialized and ready")
    except Exception as e:
        logger.error("Intent init error: %s", e, exc_info=True)
        acc._intent_classifier = None
        acc.enable_intent = False
