"""Ollama-based intent classifier using Qwen2.5:14b model."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import requests

from pjsua_bot.intent.classifier import IntentClassifier, normalize_persian_text
from pjsua_bot.intent.faq_config import FAQS, get_faq_system_prompt


class OllamaClassifier(IntentClassifier):
    """LLM-based intent classifier using Ollama API with Qwen2.5:14b model."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        faqs: Optional[Dict] = None,
        timeout: int = 30,
    ):
        """Initialize Ollama classifier.

        Args:
            ollama_url: Base URL for Ollama API (default: http://localhost:11434)
            model: Model name to use (default: qwen2.5:14b)
            faqs: FAQ configuration dict. If None, uses default FAQS.
            timeout: Request timeout in seconds (default: 30)
        """
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.faqs = faqs or FAQS
        self.timeout = timeout
        self.api_url = f"{self.ollama_url}/api/chat"

        # Build system prompt from FAQs
        self.system_prompt = get_faq_system_prompt(self.faqs)

    def classify(
        self, transcription: str, threshold: float = 0.5
    ) -> Tuple[str, float, Dict]:
        """Classify intent using Ollama LLM.

        Args:
            transcription: The transcribed user question
            threshold: Confidence threshold (not used for LLM, kept for interface compatibility)

        Returns:
            Tuple of (intent_name, confidence_score, faq_config)
        """
        if not transcription or not transcription.strip():
            return "default", 0.0, self.faqs["default"]

        try:
            # Prepare messages for Ollama API
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": transcription},
            ]

            # Make POST request to Ollama API
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,  # Get complete response, not streamed
            }

            response = requests.post(
                self.api_url, json=payload, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            answer_text = response_data.get("message", {}).get("content", "").strip()

            if not answer_text:
                print("***Ollama: empty response from API")
                return "default", 0.0, self.faqs["default"]

            print(f"***Ollama: received response: {answer_text[:100]}...")

            # Check if response indicates unknown question
            if "sorry" in answer_text.lower() and "don't know" in answer_text.lower():
                print("***Ollama: question is outside FAQ scope")
                return "default", 0.0, self.faqs["default"]

            # Match response text to FAQ by comparing with response_text fields
            intent_name = self._match_response_to_faq(answer_text)

            if intent_name and intent_name != "default":
                confidence = 0.9  # High confidence for LLM matches
                return intent_name, confidence, self.faqs[intent_name]
            else:
                # No match found, return default
                print("***Ollama: could not match response to FAQ")
                return "default", 0.0, self.faqs["default"]

        except requests.exceptions.Timeout:
            print(f"***Ollama: request timeout after {self.timeout}s")
            return "default", 0.0, self.faqs["default"]
        except requests.exceptions.ConnectionError:
            print(f"***Ollama: connection error - is Ollama running on {self.ollama_url}?")
            return "default", 0.0, self.faqs["default"]
        except requests.exceptions.RequestException as e:
            print(f"***Ollama: request error: {e}")
            return "default", 0.0, self.faqs["default"]
        except Exception as e:
            print(f"***Ollama: unexpected error: {e}")
            return "default", 0.0, self.faqs["default"]

    def _match_response_to_faq(self, answer_text: str) -> Optional[str]:
        """Match Ollama's response text to a FAQ intent.

        Compares the answer text with FAQ response_text fields to find the best match.

        Args:
            answer_text: The text response from Ollama

        Returns:
            Intent name if match found, None otherwise
        """
        # Normalize answer text for comparison
        answer_normalized = self._normalize_text(answer_text)

        best_match = None
        best_score = 0.0

        # Compare with each FAQ's response_text
        for intent_name, faq_config in self.faqs.items():
            if intent_name == "default":
                continue

            response_text = faq_config.get("response_text", "")
            if not response_text:
                continue

            # Normalize FAQ response text
            faq_normalized = self._normalize_text(response_text)

            # Calculate similarity score (simple word overlap)
            score = self._calculate_similarity(answer_normalized, faq_normalized)

            if score > best_score and score > 0.5:  # Threshold for match
                best_score = score
                best_match = intent_name

        return best_match

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (supports Persian).

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Use Persian normalization from classifier module
        normalized = normalize_persian_text(text.lower())
        return normalized

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using multiple methods.

        Args:
            text1: First text (Ollama response)
            text2: Second text (FAQ response)

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0

        # Method 1: Exact substring match (highest confidence)
        if text2 in text1 or text1 in text2:
            return 0.95

        # Method 2: Word overlap (Jaccard similarity)
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        if union == 0:
            return 0.0

        jaccard_score = intersection / union

        # Method 3: Check if most words from FAQ response are in Ollama response
        # (useful when Ollama response is longer/more detailed)
        if len(words2) > 0:
            words_in_common = len(words1.intersection(words2))
            coverage_score = words_in_common / len(words2)
            # Take the maximum of Jaccard and coverage
            return max(jaccard_score, coverage_score * 0.8)

        return jaccard_score

