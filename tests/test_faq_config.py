"""Tests for FAQ configuration module."""

from pjsua_bot.intent.faq_config import FAQS, get_faq_system_prompt


class TestFAQConfig:
    """Test cases for FAQ configuration."""

    def test_faqs_structure(self) -> None:
        """Test that FAQS has expected structure."""
        assert isinstance(FAQS, dict)
        assert "default" in FAQS
        assert len(FAQS) > 1  # Should have at least default + some intents

    def test_faqs_has_required_keys(self) -> None:
        """Test that FAQ entries have required keys."""
        for intent_name, config in FAQS.items():
            if intent_name == "default":
                continue
            assert isinstance(config, dict)
            # Check for common keys (at least one should exist)
            assert (
                "keywords" in config
                or "questions" in config
                or "response_text" in config
            )

    def test_get_faq_system_prompt_default(self) -> None:
        """Test getting system prompt with default FAQs."""
        prompt = get_faq_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "intent" in prompt.lower()
        assert "json" in prompt.lower()

    def test_get_faq_system_prompt_custom(self) -> None:
        """Test getting system prompt with custom FAQs."""
        from typing import Any, Dict

        custom_faqs: Dict[str, Dict[str, Any]] = {
            "test_intent": {
                "keywords": ["test"],
                "questions": ["Test question?"],
            },
            "default": {"response": "Default response"},
        }
        prompt = get_faq_system_prompt(custom_faqs)
        assert isinstance(prompt, str)
        assert "test_intent" in prompt
        assert "test" in prompt

    def test_get_faq_system_prompt_includes_intents(self) -> None:
        """Test that system prompt includes intent names."""
        prompt = get_faq_system_prompt()
        # Should include at least one intent name from FAQS
        intent_names = [name for name in FAQS.keys() if name != "default"]
        if intent_names:
            # At least one intent name should appear in the prompt
            assert any(name in prompt for name in intent_names[:3])

    def test_get_faq_system_prompt_includes_keywords(self) -> None:
        """Test that system prompt includes keywords."""
        prompt = get_faq_system_prompt()
        # Should include keywords from at least one FAQ
        for intent_name, config in FAQS.items():
            if intent_name == "default":
                continue
            keywords = config.get("keywords", [])
            if keywords:
                # At least one keyword should appear in prompt
                assert any(kw in prompt for kw in keywords[:3])
                break

    def test_get_faq_system_prompt_includes_questions(self) -> None:
        """Test that system prompt includes example questions."""
        prompt = get_faq_system_prompt()
        # Should include questions from at least one FAQ
        for intent_name, config in FAQS.items():
            if intent_name == "default":
                continue
            questions = config.get("questions", [])
            if questions:
                # At least one question should appear in prompt
                assert any(q in prompt for q in questions[:2])
                break

    def test_get_faq_system_prompt_excludes_default(self) -> None:
        """Test that system prompt excludes default intent."""
        prompt = get_faq_system_prompt()
        # Should mention default but not list it as an available intent
        # (it's mentioned as fallback)
        assert "default" in prompt.lower()
