#!/usr/bin/env python3
"""Check if Ollama is running and accessible."""

import argparse
import sys
from typing import Optional

import requests


def check_ollama_health(ollama_url: str = "http://localhost:11434", timeout: int = 5) -> bool:
    """Check if Ollama service is running and accessible.

    Args:
        ollama_url: Base URL for Ollama API (default: http://localhost:11434)
        timeout: Request timeout in seconds (default: 5)

    Returns:
        True if Ollama is accessible, False otherwise
    """
    try:
        url = f"{ollama_url.rstrip('/')}/api/tags"
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return True
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False
    except requests.exceptions.RequestException:
        return False


def check_model_available(
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5:14b",
    timeout: int = 5,
) -> tuple[bool, Optional[str]]:
    """Check if a specific model is available in Ollama.

    Args:
        ollama_url: Base URL for Ollama API (default: http://localhost:11434)
        model: Model name to check (default: qwen2.5:14b)
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Tuple of (is_available, error_message)
    """
    try:
        url = f"{ollama_url.rstrip('/')}/api/tags"
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        models = [m.get("name", "") for m in data.get("models", [])]

        # Check if exact model name exists
        if model in models:
            return True, None

        # Check if model name without tag exists (e.g., "qwen2.5:14b" vs "qwen2.5")
        model_base = model.split(":")[0]
        matching_models = [m for m in models if m.startswith(model_base)]
        if matching_models:
            return True, f"Model '{model}' not found, but found: {', '.join(matching_models)}"

        return False, f"Model '{model}' not found. Available models: {', '.join(models) if models else 'none'}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to Ollama at {ollama_url}"
    except requests.exceptions.Timeout:
        return False, f"Connection to Ollama at {ollama_url} timed out"
    except requests.exceptions.RequestException as e:
        return False, f"Error checking model: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def main() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Check if Ollama is running and accessible, optionally check for a specific model."
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama API base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name to check (e.g., qwen2.5:14b). If not specified, only checks if Ollama is running.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Request timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output errors, exit with code 0 if successful",
    )

    args = parser.parse_args()

    # Check if Ollama is running
    if not args.quiet:
        print(f"Checking Ollama availability at {args.ollama_url}...")

    is_running = check_ollama_health(args.ollama_url, args.timeout)

    if not is_running:
        if not args.quiet:
            print(f"❌ Ollama is not accessible at {args.ollama_url}")
            print("   Make sure Ollama is running: ollama serve")
        return 1

    if not args.quiet:
        print(f"✅ Ollama is running at {args.ollama_url}")

    # If model is specified, check if it's available
    if args.model:
        if not args.quiet:
            print(f"Checking if model '{args.model}' is available...")

        is_available, error_msg = check_model_available(
            args.ollama_url, args.model, args.timeout
        )

        if not is_available:
            if not args.quiet:
                print(f"❌ {error_msg}")
                if "not found" in error_msg.lower():
                    print(f"   Pull the model with: ollama pull {args.model}")
            return 1

        if not args.quiet:
            if error_msg:
                print(f"⚠️  {error_msg}")
            else:
                print(f"✅ Model '{args.model}' is available")

    return 0


if __name__ == "__main__":
    sys.exit(main())




