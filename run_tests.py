#!/usr/bin/env python3
"""
Test runner script for the PJSUA2 call monitoring system.
"""
import sys
import subprocess
import argparse
import os


def run_tests(test_type="all", verbose=False, coverage=True):
    """
    Run tests with specified options.
    
    Args:
        test_type (str): Type of tests to run ('unit', 'integration', 'all')
        verbose (bool): Enable verbose output
        coverage (bool): Enable coverage reporting
    """
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=elasticsearch_client", "--cov=main", "--cov-report=html", "--cov-report=term-missing"])
    
    # Filter by test type
    if test_type == "unit":
        cmd.extend(["-m", "not integration and not slow"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "fast":
        cmd.extend(["-m", "not slow"])
    
    # Add test directory
    cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n[SUCCESS] All tests passed!")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n[FAILED] Tests failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("[ERROR] pytest not found. Please install it with: pip install pytest pytest-cov")
        return 1


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run tests for PJSUA2 call monitoring system")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "fast", "all"], 
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--no-coverage", 
        action="store_true",
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=not args.no_coverage
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
