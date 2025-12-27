"""Resource cleanup functions for the SIP bot."""

import logging
from typing import Any

from .elasticsearch_client import es_logger

logger = logging.getLogger(__name__)


def cleanup_resources(acc: Any) -> None:
    """Clean up all resources including ASR models, intent classifiers, and connections.

    Args:
        acc: Account instance that may contain resources to clean up
    """
    logger.info("Cleaning up resources...")

    # Stop all ASR threads from all calls
    try:
        calls_copy = dict(getattr(acc, "calls", {}))
        for _call_id, call in calls_copy.items():
            try:
                if hasattr(call, "_stop_asr_thread"):
                    call._stop_asr_thread()
            except Exception:
                pass
    except Exception as e:
        logger.error("ASR thread cleanup error: %s", e, exc_info=True)

    # Cleanup ASR Service
    try:
        if hasattr(acc, "_asr_service") and acc._asr_service is not None:
            logger.info("Cleaning up ASR service...")
            asr_service = acc._asr_service

            # Release the pipeline/model
            if hasattr(asr_service, "_pipeline") and asr_service._pipeline is not None:
                asr_service._pipeline = None
                logger.debug("ASR: Pipeline released")

            # Clear CUDA cache if GPU was used
            if hasattr(asr_service, "_device") and asr_service._device == "cuda":
                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                        logger.debug("ASR: CUDA cache cleared")
                except ImportError:
                    pass  # torch not available
                except Exception as e:
                    logger.warning("ASR: Error clearing CUDA cache: %s", e)

            acc._asr_service = None
            logger.info("ASR: Service cleaned up")
    except Exception as e:
        logger.error("ASR cleanup error: %s", e, exc_info=True)

    # Cleanup Intent Classifier
    try:
        if hasattr(acc, "_intent_classifier") and acc._intent_classifier is not None:
            logger.info("Cleaning up intent classifier...")
            classifier = acc._intent_classifier

            if hasattr(classifier, "_fallback_classifier"):
                classifier._fallback_classifier = None

            acc._intent_classifier = None
            acc.enable_intent = False
            logger.info("Intent: Classifier cleaned up")
    except Exception as e:
        logger.error("Intent classifier cleanup error: %s", e, exc_info=True)

    # Cleanup Elasticsearch client
    try:
        if es_logger.client is not None:
            logger.info("Cleaning up Elasticsearch connection...")
            if hasattr(es_logger.client, "close"):
                try:
                    es_logger.client.close()
                    logger.debug("Elasticsearch: Connection closed")
                except Exception as e:
                    logger.warning("Elasticsearch: Error closing connection: %s", e)

            es_logger.client = None
            es_logger.connected = False
            logger.info("Elasticsearch: Client cleaned up")
    except Exception as e:
        logger.error("Elasticsearch cleanup error: %s", e, exc_info=True)

    logger.info("Resource cleanup complete")

