"""Quick manual demo for the Ollama intent classifier."""

from __future__ import annotations

from pjsua_bot.intent.ollama_classifier import OllamaClassifier


def main() -> None:
    text = "رمز عبورم رو فراموش کردم. چیکار باید بکنم"

    print("*** Creating OllamaClassifier (will contact Ollama and preload model)...")
    classifier = OllamaClassifier()

    print(f"*** Classifying: {text}")
    intent, confidence, config = classifier.classify(text)

    print("\nResult:")
    print(f"  intent     : {intent}")
    print(f"  confidence : {confidence}")
    print(f"  response   : {config.get('response_text')}")


if __name__ == "__main__":
    main()


