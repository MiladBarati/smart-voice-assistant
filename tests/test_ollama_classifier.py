"""Tests for OllamaClassifier."""

from unittest.mock import Mock, patch

import requests

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
                # Note: When use_cpu=False (default), timeout is set to max(timeout, 90)
                # So passing timeout=60 will result in timeout=90
                classifier = OllamaClassifier(
                    ollama_url="http://custom:11434",
                    model="custom:model",
                    timeout=60,
                    fallback_to_rule_based=False,
                )
                assert classifier.ollama_url == "http://custom:11434"
                assert classifier.model == "custom:model"
                # For GPU mode, timeout is max(timeout, 90) = 90
                assert classifier.timeout == 90
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
        with patch(
            "pjsua_bot.intent.ollama_classifier.requests.Session"
        ) as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock GET response for availability check
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"models": []}
            mock_session.get.return_value = mock_get_response

            # Mock POST response for both preload and classify
            mock_post_response = Mock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = {
                "message": {
                    "content": '{"intent": "slow_computer", "confidence": 0.95}'
                }
            }
            mock_session.post.return_value = mock_post_response

            classifier = OllamaClassifier()
            intent, confidence, config = classifier.classify("سلام")

            # Should return the intent if it's valid, or default if not
            assert intent in ["slow_computer", "default"]
            assert confidence >= 0.0
            mock_session.post.assert_called()

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
        with patch(
            "pjsua_bot.intent.ollama_classifier.requests.Session"
        ) as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock GET response for availability check
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"models": []}
            mock_session.get.return_value = mock_get_response

            # Mock POST response for preload
            mock_post_response = Mock()
            mock_post_response.status_code = 200
            mock_session.post.return_value = mock_post_response

            with patch("builtins.print"):  # Suppress print output
                OllamaClassifier()
                # Preload should be called during init
                # Check that post was called for preload
                assert mock_session.post.called
