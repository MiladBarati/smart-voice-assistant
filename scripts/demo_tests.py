#!/usr/bin/env python3
"""
Quick test demonstration script for the PJSUA2 call monitoring system.
This script shows how to run different types of tests.
"""

import os
import subprocess
import sys
from collections.abc import Sequence


def run_command(cmd: Sequence[str], description: str) -> bool:
    """Run a command and display the result."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[SUCCESS]")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("[FAILED]")
        if e.stdout:
            print("Output:")
            print(e.stdout)
        if e.stderr:
            print("Error:")
            print(e.stderr)
        return False


def main() -> int:
    """Demonstrate different ways to run tests."""
    print("PJSUA2 Call Monitoring System - Test Framework Demo")
    print("=" * 60)

    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Test 1: Basic pytest run
    success1 = run_command(
        ["python", "-m", "pytest", "tests/test_setup.py", "-v", "--no-cov"],
        "Basic pytest run (setup tests only)",
    )

    # Test 2: Unit tests only
    success2 = run_command(
        ["python", "run_tests.py", "--type", "unit", "--no-coverage"],
        "Unit tests only using custom runner",
    )

    # Test 3: All tests with coverage
    success3 = run_command(
        ["python", "-m", "pytest", "tests/", "-v"], "All tests with coverage reporting"
    )

    # Test 4: Specific test file
    success4 = run_command(
        ["python", "-m", "pytest", "tests/test_main.py", "-v", "--no-cov"],
        "Specific test file (main module tests)",
    )

    # Summary
    print(f"\n{'=' * 60}")
    print("DEMO SUMMARY")
    print("=" * 60)

    results = [success1, success2, success3, success4]
    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("[SUCCESS] All test demonstrations completed successfully!")
        print("\nThe testing framework is working correctly.")
        print("\nYou can now:")
        print("- Run tests with: python run_tests.py")
        print("- Run specific tests: pytest tests/test_setup.py -v")
        print("- Run with coverage: pytest --cov=elasticsearch_client --cov=main")
        print("- Run unit tests only: python run_tests.py --type unit")
    else:
        print("[WARNING] Some test demonstrations failed.")
        print("Check the output above for details.")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
