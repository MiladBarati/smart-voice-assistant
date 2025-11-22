"""Intent classification package for call bot."""

from .classifier import IntentClassifier, RuleBasedClassifier
from .faq_config import FAQS

__all__ = ["IntentClassifier", "RuleBasedClassifier", "FAQS"]
