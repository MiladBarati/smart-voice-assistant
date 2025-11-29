"""Intent classification package for call bot."""

from .classifier import IntentClassifier, RuleBasedClassifier
from .faq_config import FAQS, get_faq_system_prompt
from .ollama_classifier import OllamaClassifier

__all__ = [
    "IntentClassifier",
    "RuleBasedClassifier",
    "OllamaClassifier",
    "FAQS",
    "get_faq_system_prompt",
]
