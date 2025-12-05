"""Ollama-based intent classifier using Qwen3:8b model."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

import requests

from pjsua_bot.intent.classifier import (
    IntentClassifier,
    RuleBasedClassifier,
    normalize_persian_text,
)
from pjsua_bot.intent.faq_config import FAQS, get_faq_system_prompt


class OllamaClassifier(IntentClassifier):
    """LLM-based intent classifier using Ollama API with Qwen3:8b model."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        faqs: Optional[Dict] = None,
        timeout: int = 30,
        fallback_to_rule_based: bool = True,
        use_cpu: bool = False,
    ):
        """Initialize Ollama classifier.

        Args:
            ollama_url: Base URL for Ollama API (default: http://localhost:11434)
            model: Model name to use (default: qwen2.5:7b)
                For CPU usage, consider smaller models like: qwen2.5:0.5b,
                qwen2.5:1.5b, qwen2.5:3b, or qwen2.5:7b
            faqs: FAQ configuration dict. If None, uses default FAQS.
            timeout: Request timeout in seconds (default: 30, increase for CPU)
            fallback_to_rule_based: If True, fallback to rule-based classifier on errors
            use_cpu: If True, attempt to force CPU usage via API options.
                Note: This is a hint; actual device selection is controlled by
                OLLAMA_NUM_GPU environment variable on the Ollama server.
                To force CPU on server: export OLLAMA_NUM_GPU=0 before starting Ollama
        """
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.faqs = faqs or FAQS
        self.timeout = timeout
        self.api_url = f"{self.ollama_url}/api/chat"
        self.fallback_to_rule_based = fallback_to_rule_based
        self.use_cpu = use_cpu

        # Log resolved endpoint/model for easier debugging of misconfiguration
        print(
            f"***Ollama: using endpoint={self.api_url} model={self.model} "
            f"fallback_to_rule_based={self.fallback_to_rule_based} use_cpu={self.use_cpu}"
        )

        # Increase timeout for CPU usage (CPU is slower)
        if use_cpu and timeout < 60:
            self.timeout = 60
            print(f"***Ollama: CPU mode enabled, timeout increased to {self.timeout}s")
        elif not use_cpu:
            # For GPU, use longer timeout for first request
            # (model loading can take time)
            # Subsequent requests will be faster
            self.timeout = max(timeout, 60)  # At least 60s for GPU model loading

        # Build a concise, strict system prompt to improve JSON compliance.
        intent_names = [name for name in self.faqs.keys() if name != "default"]
        intents_csv = ", ".join(intent_names + ["default"])
        self.system_prompt = (
            'Return exactly one JSON object with a single key "intent". '
            f'Value must be one of: {intents_csv}. '
            "No other keys. No other text."
        )

        # Initialize fallback classifier if enabled
        self._fallback_classifier: Optional[RuleBasedClassifier] = None
        if self.fallback_to_rule_based:
            self._fallback_classifier = RuleBasedClassifier(faqs=self.faqs)

        # Check if Ollama is available and model exists
        self._check_ollama_availability()

        # Preload the model to avoid first-request timeout
        self._preload_model()

    def classify(
        self, transcription: str, threshold: float = 0.5
    ) -> Tuple[str, float, Dict]:
        """Classify intent using Ollama LLM.

        Args:
            transcription: The transcribed user question
            threshold: Confidence threshold (not used for LLM,
                kept for interface compatibility)

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
            options: Dict[str, Any] = {
                # Disable thinking mode for faster responses
                "enable_thinking": False,
                # Force deterministic output to improve JSON adherence
                "temperature": 0,
            }
            # Add device hint if requested
            # (though server-side OLLAMA_NUM_GPU takes precedence)
            if self.use_cpu:
                # Hint to use CPU (server may ignore if OLLAMA_NUM_GPU is set)
                options["num_gpu"] = 0

            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,  # Get complete response, not streamed
                "format": "json",  # Request JSON format for structured output
                "options": options,
            }
            # By default, Ollama will use GPU if available (no options needed)

            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            answer_text = response_data.get("message", {}).get("content", "").strip()

            if not answer_text:
                print("***Ollama: empty response from API")
                return "default", 0.0, self.faqs["default"]

            print(f"***Ollama: received response: {answer_text}...")

            # Try to extract intent name from JSON response
            intent_name = self._extract_intent_from_response(answer_text)

            if intent_name and intent_name in self.faqs:
                confidence = 0.9  # High confidence for LLM matches
                print(f"***Ollama: classified as '{intent_name}'")
                return intent_name, confidence, self.faqs[intent_name]
            else:
                # Invalid or unknown intent; try rule-based fallback before defaulting
                print(f"***Ollama: invalid intent '{intent_name}', using fallback")
                return self._fallback_classify(transcription)

        except requests.exceptions.HTTPError as e:
            # Log detailed error information for HTTP errors (500, 404, etc.)
            # HTTPError is raised by response.raise_for_status()
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", str(error_body))
                error_msg += f": {error_detail}"
            except Exception:
                try:
                    error_msg += f": {e.response.text[:200]}"
                except Exception:
                    error_msg += f": {str(e)}"
            print(f"***Ollama: {error_msg}")
            return self._fallback_classify(transcription)
        except requests.exceptions.Timeout:
            print(f"***Ollama: request timeout after {self.timeout}s")
            return self._fallback_classify(transcription)
        except requests.exceptions.ConnectionError:
            print(
                f"***Ollama: connection error - is Ollama running on {self.ollama_url}?"
            )
            return self._fallback_classify(transcription)
        except requests.exceptions.RequestException as e:
            print(f"***Ollama: request error: {e}")
            return self._fallback_classify(transcription)
        except Exception as e:
            print(f"***Ollama: unexpected error: {e}")
            return self._fallback_classify(transcription)

    def _extract_intent_from_response(self, response_text: str) -> Optional[str]:
        """Extract intent name from Ollama's JSON response.

        Args:
            response_text: The text response from Ollama (should be JSON)

        Returns:
            Intent name if found, None otherwise
        """
        # Try to parse as JSON first
        try:
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(
                r'\{[^{}]*"intent"[^{}]*\}', response_text, re.IGNORECASE
            )
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                intent_name = parsed.get("intent")
                if intent_name:
                    return str(intent_name)
        except (json.JSONDecodeError, AttributeError, KeyError) as e:
            print(f"***Ollama: failed to parse JSON response: {e}")

        # Fallback: try to find intent name as plain text
        # (in case JSON parsing fails)
        # Look for common patterns like "intent": "slow_computer"
        # or just "slow_computer"
        for intent_name in self.faqs.keys():
            # Check if intent name appears in the response
            if (
                f'"intent": "{intent_name}"' in response_text
                or f"\"intent\":'{intent_name}'" in response_text
            ):
                return intent_name
            # Also check for just the intent name if it's clearly mentioned
            if f'"{intent_name}"' in response_text and intent_name != "default":
                return intent_name

        return None

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

    def _check_ollama_availability(self) -> None:
        """Check if Ollama is available and model exists."""
        try:
            # Check if Ollama is running
            health_url = f"{self.ollama_url}/api/tags"
            response = requests.get(health_url, timeout=5)
            response.raise_for_status()

            # Check if model is available
            models_data = response.json()
            available_models = [
                model.get("name", "") for model in models_data.get("models", [])
            ]
            if self.model not in available_models:
                print(
                    f"***Ollama: warning - model '{self.model}' not found. "
                    f"Available models: {', '.join(available_models[:5])}"
                )
                print(
                    "***Ollama: will attempt to use model anyway "
                    "(it may be pulled automatically)"
                )
            else:
                print(f"***Ollama: model '{self.model}' is available")
        except requests.exceptions.ConnectionError:
            print(
                f"***Ollama: warning - cannot connect to {self.ollama_url}. "
                f"Will fallback to rule-based classifier on errors."
            )
        except Exception as e:
            print(f"***Ollama: warning - error checking availability: {e}")

    def _preload_model(self) -> None:
        """Preload the Ollama model to avoid first-request timeout.

        Makes a simple request to load the model into GPU/CPU memory.
        This is similar to how ASR models are preloaded.
        """
        try:
            print(f"***Ollama: preloading model '{self.model}'...")

            # Make a minimal request to trigger model loading
            # Use a very simple prompt to minimize processing time
            options: Dict[str, Any] = {
                "num_predict": 1,  # Only generate 1 token to minimize time
                # Disable thinking mode for faster preload
                "enable_thinking": False,
            }
            # Add CPU hint if requested
            if self.use_cpu:
                options["num_gpu"] = 0

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "test"},
                ],
                "stream": False,
                "options": options,
            }

            # Use a longer timeout for preloading (model loading can take time)
            preload_timeout = max(
                self.timeout, 120
            )  # At least 2 minutes for first load

            response = requests.post(
                self.api_url, json=payload, timeout=preload_timeout
            )
            response.raise_for_status()

            print(f"***Ollama: model '{self.model}' preloaded successfully")

        except requests.exceptions.Timeout:
            print(
                f"***Ollama: preload timeout after {preload_timeout}s - "
                f"model may still be loading. First request may be slow."
            )
        except requests.exceptions.ConnectionError:
            print(
                "***Ollama: cannot preload - connection error. "
                "Will attempt to load on first request."
            )
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", str(error_body))
                error_msg += f": {error_detail}"
            except Exception:
                try:
                    error_msg += f": {e.response.text[:200]}"
                except Exception:
                    error_msg += f": {str(e)}"
            print(
                f"***Ollama: preload failed ({error_msg}) - "
                "will attempt on first request"
            )
        except Exception as e:
            print(f"***Ollama: preload error: {e} - will attempt on first request")

    def _fallback_classify(
        self, transcription: str
    ) -> Tuple[str, float, Dict[str, Any]]:
        """Fallback to rule-based classifier when Ollama fails.

        Args:
            transcription: The transcribed text

        Returns:
            Tuple of (intent_name, confidence_score, faq_config)
        """
        if self._fallback_classifier:
            print("***Ollama: falling back to rule-based classifier")
            try:
                return self._fallback_classifier.classify(transcription)
            except Exception as e:
                print(f"***Ollama: fallback classifier error: {e}")
                return "default", 0.0, self.faqs["default"]
        else:
            print("***Ollama: no fallback classifier available")
            return "default", 0.0, self.faqs["default"]
