"""Base classifier interface and rule-based implementation - Persian support."""

from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from pjsua_bot.intent.faq_config import FAQS


def normalize_persian_text(text: str) -> str:
    """Normalize Persian text for better matching.

    Handles:
    - Different Persian/Arabic character variations
    - Whitespace normalization
    - Case normalization (though Persian doesn't have cases)
    - Punctuation removal for better keyword matching
    """
    # Normalize Unicode characters (e.g., different forms of same character)
    text = unicodedata.normalize("NFKC", text)

    # Remove common punctuation marks (both Latin and Persian/Arabic) that
    # might interfere with matching. This includes: ? ! ؟ . ، ; : etc.
    punctuation_chars = "?؟!.,،;:()[]{}\"\"''«»"
    for char in punctuation_chars:
        text = text.replace(char, " ")

    # Normalize whitespace
    text = " ".join(text.split())

    # Remove zero-width characters
    text = text.replace("\u200c", " ")  # Zero-width non-joiner
    text = text.replace("\u200d", " ")  # Zero-width joiner

    # Final whitespace normalization
    text = " ".join(text.split())

    return text.strip()


class IntentClassifier(ABC):
    """Base class for intent classifiers."""

    @abstractmethod
    def classify(
        self, transcription: str, threshold: float = 0.5
    ) -> Tuple[str, float, Dict]:
        """Classify intent from transcription.

        Args:
            transcription: The transcribed text
            threshold: Confidence threshold (0.0-1.0)

        Returns:
            Tuple of (intent_name, confidence_score, faq_config)
        """
        pass


class RuleBasedClassifier(IntentClassifier):
    """Simple keyword-based intent classifier with Persian support."""

    def __init__(self, faqs: Optional[Dict] = None):
        """Initialize rule-based classifier.

        Args:
            faqs: FAQ configuration dict. If None, uses default FAQS.
        """
        self.faqs = faqs or FAQS

        # Normalize and lowercase keywords for matching
        self._normalized_keywords = {}
        for intent, config in self.faqs.items():
            if intent == "default":
                continue

            keywords = config.get("keywords", [])
            # Normalize each keyword
            normalized = [normalize_persian_text(kw.lower()) for kw in keywords]
            self._normalized_keywords[intent] = normalized

    def classify(
        self, transcription: str, threshold: float = 0.3
    ) -> Tuple[str, float, Dict]:
        """Classify intent using keyword matching with Persian normalization.

        Args:
            transcription: The transcribed text (Persian)
            threshold: Minimum keyword matches required (as ratio)

        Returns:
            Tuple of (intent_name, confidence_score, faq_config)
        """
        if not transcription or not transcription.strip():
            return "default", 0.0, self.faqs["default"]

        # Normalize transcription
        transcription_normalized = normalize_persian_text(transcription.lower())

        # Count keyword matches for each intent
        intent_scores = {}
        for intent, keywords in self._normalized_keywords.items():
            matches = 0
            matched_keywords = []

            for kw in keywords:
                # Check if keyword appears in transcription
                if kw in transcription_normalized:
                    matches += 1
                    matched_keywords.append(kw)

            if matches > 0:
                # Confidence calculation: balance between match ratio and
                # keyword specificity
                total_keywords = len(keywords)
                match_ratio = matches / total_keywords if total_keywords > 0 else 0

                # Weight by keyword length (longer keywords = more specific =
                # higher confidence). Calculate average length of matched
                # keywords vs all keywords
                avg_matched_length = (
                    sum(len(kw) for kw in matched_keywords) / matches
                    if matches > 0
                    else 0
                )
                avg_total_length = (
                    sum(len(kw) for kw in keywords) / total_keywords
                    if total_keywords > 0
                    else 0
                )
                length_factor = (
                    avg_matched_length / avg_total_length
                    if avg_total_length > 0
                    else 1.0
                )

                # Base confidence from match ratio, boosted by length factor.
                # Minimum confidence boost for any match to ensure important
                # keywords score well
                base_confidence = match_ratio * 0.5
                length_boost = min(0.4, length_factor * 0.3)
                match_boost = 0.3 if matches > 0 else 0  # Boost for having any matches

                confidence = min(1.0, base_confidence + length_boost + match_boost)

                intent_scores[intent] = {
                    "matches": matches,
                    "confidence": confidence,
                    "matched_keywords": matched_keywords,
                }

        # Return intent with highest confidence above threshold
        if intent_scores:
            # Sort by: 1) longest matched keyword (specificity), 2) confidence,
            # 3) match count. This prioritizes intents with more specific
            # keyword matches
            def score_key(x: tuple[str, Dict[str, Any]]) -> tuple[int, float, int]:
                intent_name, score_data = x
                matched_keywords_list: List[str] = score_data.get(
                    "matched_keywords", []
                )
                max_keyword_length = max(
                    (len(kw) for kw in matched_keywords_list), default=0
                )
                conf_value = score_data.get("confidence", 0.0)
                matches_value = score_data.get("matches", 0)
                return (
                    max_keyword_length,
                    float(conf_value) if isinstance(conf_value, (int, float)) else 0.0,
                    int(matches_value) if isinstance(matches_value, int) else 0,
                )

            best_intent = max(intent_scores.items(), key=score_key)
            intent_name, score_data = best_intent
            conf_value = score_data.get("confidence", 0.0)
            confidence = (
                float(conf_value) if isinstance(conf_value, (int, float)) else 0.0
            )

            if confidence >= threshold:
                matched_kw_list_obj = score_data.get("matched_keywords", [])
                matched_kw_list: List[str] = (
                    matched_kw_list_obj if isinstance(matched_kw_list_obj, list) else []
                )
                print(f"***Intent: Matched keywords: {matched_kw_list[:3]}")
                return intent_name, min(confidence, 1.0), self.faqs[intent_name]

        # Fallback to default
        return "default", 0.0, self.faqs["default"]

    def get_available_intents(self) -> List[str]:
        """Get list of available intent names."""
        return [intent for intent in self.faqs.keys() if intent != "default"]
