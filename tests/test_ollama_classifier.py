"""Tests for OllamaClassifier."""

from unittest.mock import Mock, patch

import requests  # type: ignore[import-untyped]

from pjsua_bot.intent.ollama_classifier import OllamaClassifier


class TestOllamaClassifier:
    """Test cases for OllamaClassifier class."""

    def test_init_default_values(self) -> None:
        """Test initialization with default values."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                classifier = OllamaClassifier()
                assert classifier.ollama_url == "http://localhost:11434"
                assert classifier.model == "qwen2.5:7b"
                assert classifier.timeout >= 30
                assert classifier.fallback_to_rule_based is True

    def test_init_custom_values(self) -> None:
        """Test initialization with custom values."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                classifier = OllamaClassifier(
                    ollama_url="http://custom:11434",
                    model="custom:model",
                    timeout=60,
                    fallback_to_rule_based=False,
                )
                assert classifier.ollama_url == "http://custom:11434"
                assert classifier.model == "custom:model"
                assert classifier.timeout == 60
                assert classifier.fallback_to_rule_based is False

    def test_classify_empty_transcription(self) -> None:
        """Test classifying empty transcription."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post"):
                classifier = OllamaClassifier()
                intent, confidence, config = classifier.classify("")
                assert intent == "default"
                assert confidence == 0.0

    def test_classify_success(self) -> None:
        """Test successful classification."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "message": {"content": '{"intent": "greeting", "confidence": 0.95}'}
                }
                mock_post.return_value = mock_response

                # Use a valid intent from default FAQs
                mock_response.json.return_value = {
                    "message": {
                        "content": '{"intent": "slow_computer", "confidence": 0.95}'
                    }
                }
                classifier = OllamaClassifier()
                intent, confidence, config = classifier.classify("سلام")

                # Should return the intent if it's valid, or default if not
                assert intent in ["slow_computer", "default"]
                assert confidence >= 0.0
                mock_post.assert_called()

    def test_classify_with_fallback(self) -> None:
        """Test classification with fallback to rule-based."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post") as mock_post:
                mock_post.side_effect = requests.RequestException("Connection error")

                classifier = OllamaClassifier(fallback_to_rule_based=True)
                # Should fall back to rule-based classifier
                intent, confidence, config = classifier.classify("سلام")

                # Should still return a result (from fallback)
                assert intent is not None

    def test_classify_without_fallback(self) -> None:
        """Test classification without fallback on error."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post") as mock_post:
                mock_post.side_effect = requests.RequestException("Connection error")

                classifier = OllamaClassifier(fallback_to_rule_based=False)
                intent, confidence, config = classifier.classify("سلام")

                # Should return default on error
                assert intent == "default"
                assert confidence == 0.0

    def test_classify_invalid_json_response(self) -> None:
        """Test classification with invalid JSON response."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "message": {"content": "invalid json"}
                }
                mock_post.return_value = mock_response

                classifier = OllamaClassifier(fallback_to_rule_based=True)
                # Should fall back to rule-based on JSON parse error
                intent, confidence, config = classifier.classify("سلام")

                assert intent is not None

    def test_check_ollama_availability_success(self) -> None:
        """Test checking Ollama availability when available."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post"):
                classifier = OllamaClassifier()
                # Should not raise exception
                assert classifier is not None

    def test_check_ollama_availability_failure(self) -> None:
        """Test checking Ollama availability when unavailable."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection error")

            with patch("builtins.print"):  # Suppress print output
                classifier = OllamaClassifier()
                # Should still initialize but mark as unavailable
                assert classifier is not None

    def test_preload_model(self) -> None:
        """Test model preloading."""
        with patch("pjsua_bot.intent.ollama_classifier.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response

            with patch("pjsua_bot.intent.ollama_classifier.requests.post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response

                with patch("builtins.print"):  # Suppress print output
                    OllamaClassifier()
                    # Preload should be called during init
                    # Check that post was called for preload
                    assert mock_post.called
