#!/usr/bin/env python3
"""Test script for intent classifier performance with various inputs."""

import argparse
import logging
import sys
import time
from typing import List, Tuple

from pjsua_bot.intent.classifier import RuleBasedClassifier
from pjsua_bot.intent.faq_config import FAQS
from pjsua_bot.intent.ollama_classifier import OllamaClassifier

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise, only show warnings/errors
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Test cases: (input_text, expected_intent, description)
TEST_CASES: List[Tuple[str, str, str]] = [
    # Matching intents
    ("کامپیوترم کند است", "slow_computer", "Slow computer - should match"),
    ("صدا نمی‌آید", "no_sound", "No sound - should match"),
    (
        "کامپیوترم ناگهان خاموش می شود",
        "computer_shuts_down",
        "Computer shuts down - should match",
    ),
    ("صفحه نمایش فریز می شود", "screen_freezes", "Screen freezes - should match"),
    ("انترنت ضعیف شده", "slow_internet_general", "Slow internet - should match"),
    # Non-matching (should return default)
    ("هوا چطور", "default", "Weather question - should be default"),
    ("امروز چه روزی است", "default", "Date question - should be default"),
    ("سلام", "default", "Greeting - should be default"),
    ("خداحافظ", "default", "Goodbye - should be default"),
    # Edge cases
    ("", "default", "Empty string - should be default"),
    ("   ", "default", "Whitespace only - should be default"),
    ("انترنت هم زاییف شرش کونه", "default", "Poor transcription - should be default"),
    ("不就ت的", "default", "Garbled text - should be default"),
    # Similar but different intents
    ("کامپیوترم کند کار می‌کند", "slow_computer", "Slow computer variant"),
    ("صدا از کامپیوترم نمی‌آید", "no_sound", "No sound variant"),
    (
        "انترنتهم ضعیف شده چیکارش کنن",
        "slow_internet_general",
        "Internet slow - should match",
    ),
]


def test_classifier(
    classifier, test_cases: List[Tuple[str, str, str]], classifier_name: str
) -> dict:
    """Test a classifier with given test cases.

    Args:
        classifier: The classifier instance to test
        test_cases: List of (input, expected_intent, description) tuples
        classifier_name: Name of the classifier for reporting

    Returns:
        Dictionary with test results
    """
    results = {
        "total": len(test_cases),
        "correct": 0,
        "incorrect": 0,
        "timeouts": 0,
        "errors": 0,
        "total_time": 0.0,
        "details": [],
    }

    print(f"\n{'='*80}")
    print(f"Testing {classifier_name}")
    print(f"{'='*80}\n")

    for i, (input_text, expected_intent, description) in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {description}")
        print(f"  Input: '{input_text}'")
        print(f"  Expected: '{expected_intent}'")

        start_time = time.time()
        try:
            intent, confidence, faq_config = classifier.classify(input_text)
            elapsed = time.time() - start_time
            results["total_time"] += elapsed

            is_correct = intent == expected_intent
            status = "✓" if is_correct else "✗"

            if is_correct:
                results["correct"] += 1
            else:
                results["incorrect"] += 1

            print(
                f"  Result: {status} Got: '{intent}' "
                f"(confidence: {confidence:.2f}) in {elapsed:.2f}s"
            )

            if not is_correct:
                print(f"  ⚠️  MISMATCH: Expected '{expected_intent}', got '{intent}'")

            results["details"].append(
                {
                    "input": input_text,
                    "expected": expected_intent,
                    "got": intent,
                    "confidence": confidence,
                    "time": elapsed,
                    "correct": is_correct,
                    "description": description,
                }
            )

        except Exception as e:
            elapsed = time.time() - start_time
            results["errors"] += 1
            print(f"  ✗ ERROR: {e} (after {elapsed:.2f}s)")
            results["details"].append(
                {
                    "input": input_text,
                    "expected": expected_intent,
                    "got": None,
                    "confidence": 0.0,
                    "time": elapsed,
                    "correct": False,
                    "error": str(e),
                    "description": description,
                }
            )

        print()

    return results


def print_summary(results_ollama: dict, results_rule: dict = None):
    """Print summary of test results."""
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    print("Ollama Classifier:")
    print(f"  Total tests: {results_ollama['total']}")
    correct_pct = 100 * results_ollama["correct"] / results_ollama["total"]
    print(f"  Correct: {results_ollama['correct']} ({correct_pct:.1f}%)")
    print(f"  Incorrect: {results_ollama['incorrect']}")
    print(f"  Errors: {results_ollama['errors']}")
    print(f"  Timeouts: {results_ollama['timeouts']}")
    print(f"  Total time: {results_ollama['total_time']:.2f}s")
    avg_time = results_ollama["total_time"] / results_ollama["total"]
    print(f"  Average time: {avg_time:.2f}s")

    if results_rule:
        print("\nRule-Based Classifier:")
        print(f"  Total tests: {results_rule['total']}")
        correct_pct_rule = 100 * results_rule["correct"] / results_rule["total"]
        print(f"  Correct: {results_rule['correct']} ({correct_pct_rule:.1f}%)")
        print(f"  Incorrect: {results_rule['incorrect']}")
        print(f"  Errors: {results_rule['errors']}")
        print(f"  Total time: {results_rule['total_time']:.2f}s")
        avg_time_rule = results_rule["total_time"] / results_rule["total"]
        print(f"  Average time: {avg_time_rule:.2f}s")

    # Show incorrect classifications
    print("\n" + "=" * 80)
    print("INCORRECT CLASSIFICATIONS:")
    print("=" * 80)

    incorrect_ollama = [r for r in results_ollama["details"] if not r["correct"]]
    if incorrect_ollama:
        for r in incorrect_ollama:
            print(f"\n  Input: '{r['input']}'")
            print(f"  Expected: '{r['expected']}'")
            print(f"  Got: '{r['got']}' (confidence: {r['confidence']:.2f})")
            print(f"  Time: {r['time']:.2f}s")
            if "error" in r:
                print(f"  Error: {r['error']}")
    else:
        print("  None! All tests passed ✓")

    if results_rule:
        incorrect_rule = [r for r in results_rule["details"] if not r["correct"]]
        if incorrect_rule:
            print("\nRule-Based Incorrect:")
            for r in incorrect_rule:
                print(
                    f"  Input: '{r['input']}' -> Expected: '{r['expected']}', "
                    f"Got: '{r['got']}'"
                )


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test intent classifier performance with various inputs"
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model name (default: qwen2.5:7b)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Request timeout in seconds (default: 90)",
    )
    parser.add_argument(
        "--use-cpu",
        action="store_true",
        help="Force CPU usage",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback to rule-based classifier",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Also test rule-based classifier for comparison",
    )
    parser.add_argument(
        "--custom-tests",
        nargs="+",
        help="Custom test inputs (space-separated)",
    )

    args = parser.parse_args()

    # Add custom tests if provided
    test_cases = TEST_CASES.copy()
    if args.custom_tests:
        for test_input in args.custom_tests:
            test_cases.append((test_input, "default", f"Custom test: {test_input}"))

    print("Initializing Ollama Classifier...")
    try:
        ollama_classifier = OllamaClassifier(
            ollama_url=args.ollama_url,
            model=args.model,
            timeout=args.timeout,
            fallback_to_rule_based=not args.no_fallback,
            use_cpu=args.use_cpu,
        )
        # Show system prompt length for diagnostics
        prompt_length = len(ollama_classifier.system_prompt)
        print("✓ Ollama Classifier initialized")
        token_estimate = prompt_length // 4
        print(
            f"  System prompt length: {prompt_length:,} characters "
            f"(~{token_estimate:,} tokens)\n"
        )
    except Exception as e:
        print(f"✗ Failed to initialize Ollama Classifier: {e}")
        sys.exit(1)

    # Test Ollama classifier
    results_ollama = test_classifier(ollama_classifier, test_cases, "Ollama Classifier")

    # Test rule-based classifier for comparison if requested
    results_rule = None
    if args.compare:
        print("\nInitializing Rule-Based Classifier...")
        rule_classifier = RuleBasedClassifier(faqs=FAQS)
        print("✓ Rule-Based Classifier initialized\n")
        results_rule = test_classifier(
            rule_classifier, test_cases, "Rule-Based Classifier"
        )

    # Print summary
    print_summary(results_ollama, results_rule)

    # Exit code based on results
    if results_ollama["incorrect"] > 0 or results_ollama["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
