"""Helper functions for ASR tests."""

import sys
from unittest.mock import Mock


def setup_torch_mock() -> Mock:
    """Set up a mock torch module in sys.modules."""
    mock_torch = Mock()
    mock_torch.cuda.is_available.return_value = False
    sys.modules["torch"] = mock_torch
    return mock_torch


def teardown_torch_mock() -> None:
    """Remove mock torch module from sys.modules."""
    if "torch" in sys.modules and isinstance(sys.modules["torch"], Mock):
        del sys.modules["torch"]

