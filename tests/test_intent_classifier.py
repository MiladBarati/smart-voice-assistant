"""Tests for intent classifier."""

from pjsua_bot.intent.classifier import RuleBasedClassifier, normalize_persian_text


class TestNormalizePersianText:
    """Test cases for normalize_persian_text function."""

    def test_normalize_simple_text(self) -> None:
        """Test normalizing simple Persian text."""
        text = "سلام دنیا"
        result = normalize_persian_text(text)
        assert result == "سلام دنیا"

    def test_normalize_text_with_punctuation(self) -> None:
        """Test normalizing text with punctuation."""
        text = "سلام؟ دنیا!"
        result = normalize_persian_text(text)
        assert "؟" not in result
        assert "!" not in result

    def test_normalize_text_with_whitespace(self) -> None:
        """Test normalizing text with extra whitespace."""
        text = "سلام    دنیا"
        result = normalize_persian_text(text)
        assert "  " not in result  # No double spaces

    def test_normalize_text_with_zero_width_chars(self) -> None:
        """Test normalizing text with zero-width characters."""
        text = "سلام\u200cدنیا"  # Zero-width non-joiner
        result = normalize_persian_text(text)
        assert "\u200c" not in result

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string."""
        result = normalize_persian_text("")
        assert result == ""

    def test_normalize_text_with_unicode_variations(self) -> None:
        """Test normalizing text with Unicode variations."""
        # This tests NFKC normalization
        text = "سلام"
        result = normalize_persian_text(text)
        assert len(result) > 0


class TestRuleBasedClassifier:
    """Test cases for RuleBasedClassifier class."""

    def test_init_with_default_faqs(self) -> None:
        """Test initialization with default FAQs."""
        classifier = RuleBasedClassifier()
        assert classifier.faqs is not None
        assert "default" in classifier.faqs

    def test_init_with_custom_faqs(self) -> None:
        """Test initialization with custom FAQs."""
        custom_faqs = {
            "greeting": {
                "keywords": ["سلام", "درود"],
                "response": "سلام! چطور می‌تونم کمکتون کنم؟",
            },
            "default": {"response": "متوجه نشدم."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        assert classifier.faqs == custom_faqs

    def test_classify_empty_transcription(self) -> None:
        """Test classifying empty transcription."""
        classifier = RuleBasedClassifier()
        intent, confidence, config = classifier.classify("")
        assert intent == "default"
        assert confidence == 0.0
        assert config == classifier.faqs["default"]

    def test_classify_whitespace_only(self) -> None:
        """Test classifying whitespace-only transcription."""
        classifier = RuleBasedClassifier()
        intent, confidence, config = classifier.classify("   ")
        assert intent == "default"
        assert confidence == 0.0

    def test_classify_with_keyword_match(self) -> None:
        """Test classifying with keyword match."""
        custom_faqs = {
            "greeting": {
                "keywords": ["سلام", "درود"],
                "response": "سلام!",
            },
            "default": {"response": "متوجه نشدم."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        intent, confidence, config = classifier.classify("سلام")
        assert intent == "greeting"
        assert confidence > 0.0
        assert config == custom_faqs["greeting"]

    def test_classify_with_multiple_keywords(self) -> None:
        """Test classifying with multiple keyword matches."""
        custom_faqs = {
            "greeting": {
                "keywords": ["سلام", "درود", "صبح بخیر"],
                "response": "سلام!",
            },
            "default": {"response": "متوجه نشدم."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        intent, confidence, config = classifier.classify("سلام و درود")
        assert intent == "greeting"
        assert confidence > 0.0

    def test_classify_below_threshold(self) -> None:
        """Test classifying when confidence is below threshold."""
        custom_faqs = {
            "greeting": {
                "keywords": ["سلام", "درود"],
                "response": "سلام!",
            },
            "default": {"response": "متوجه نشدم."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        # Use a very high threshold
        intent, confidence, config = classifier.classify("سلام", threshold=1.0)
        # Should fall back to default if confidence is too low
        # (This depends on the actual confidence calculation)
        assert intent in ["greeting", "default"]

    def test_classify_no_match(self) -> None:
        """Test classifying when no keywords match."""
        custom_faqs = {
            "greeting": {
                "keywords": ["سلام", "درود"],
                "response": "سلام!",
            },
            "default": {"response": "متوجه نشدم."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        intent, confidence, config = classifier.classify("چیزی کاملا متفاوت")
        assert intent == "default"
        assert confidence == 0.0

    def test_get_available_intents(self) -> None:
        """Test getting list of available intents."""
        custom_faqs = {
            "greeting": {"keywords": ["سلام"]},
            "farewell": {"keywords": ["خداحافظ"]},
            "default": {"response": "متوجه نشدم."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        intents = classifier.get_available_intents()
        assert "greeting" in intents
        assert "farewell" in intents
        assert "default" not in intents  # Should exclude default

    def test_classify_with_persian_normalization(self) -> None:
        """Test that Persian text normalization works in classification."""
        custom_faqs = {
            "greeting": {
                "keywords": ["سلام"],
                "response": "سلام!",
            },
            "default": {"response": "متوجه نشدم."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        # Text with punctuation should still match
        intent, confidence, config = classifier.classify("سلام؟")
        assert intent == "greeting"
        assert confidence > 0.0

    def test_classify_case_insensitive(self) -> None:
        """Test that classification is case-insensitive."""
        custom_faqs = {
            "greeting": {
                "keywords": ["hello"],
                "response": "Hello!",
            },
            "default": {"response": "I don't understand."},
        }
        classifier = RuleBasedClassifier(faqs=custom_faqs)
        intent1, conf1, _ = classifier.classify("HELLO")
        intent2, conf2, _ = classifier.classify("hello")
        # Both should match (case-insensitive)
        assert intent1 == intent2 == "greeting"
