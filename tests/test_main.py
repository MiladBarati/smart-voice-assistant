"""
Tests for main.py module.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any

import main


class TestMain:
    """Test cases for main module."""

    def test_main_function_exists(self) -> None:
        """Test that main function exists."""
        assert hasattr(main, "main")
        assert callable(main.main)

    def test_main_function_runs(self, capsys: Any) -> None:
        """Test that main function runs without errors."""
        main.main()
        captured = capsys.readouterr()
        assert "Hello from pjsua-installation!" in captured.out

    def test_main_module_structure(self) -> None:
        """Test that main module has expected structure."""
        # Test that main module can be imported
        assert main is not None

        # Test that main function is callable
        assert callable(main.main)
