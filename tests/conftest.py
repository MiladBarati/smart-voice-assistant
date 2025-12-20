"""Pytest configuration for tests."""

import os
import sys
from typing import Any
from unittest.mock import Mock

import pytest

# Mock pjsua2 module before any imports to prevent ImportError during test collection
# This allows tests to be collected even when pjsua2 is not installed
if "pjsua2" not in sys.modules:
    mock_pjsua2 = Mock()

    # Create a mock Endpoint class with instance() method
    mock_endpoint_instance = Mock()
    mock_endpoint_class = Mock()
    mock_endpoint_class.instance = Mock(return_value=mock_endpoint_instance)
    mock_endpoint_class.return_value = mock_endpoint_instance

    # Add common pjsua2 classes and attributes that might be accessed
    mock_pjsua2.Account = Mock
    mock_pjsua2.Call = Mock
    mock_pjsua2.Endpoint = mock_endpoint_class
    mock_pjsua2.AudioMediaPlayer = Mock
    mock_pjsua2.AudioMedia = Mock
    mock_pjsua2.TransportConfig = Mock
    mock_pjsua2.AccountConfig = Mock
    mock_pjsua2.AuthCredInfo = Mock
    mock_pjsua2.EpConfig = Mock
    mock_pjsua2.CallInfo = Mock
    mock_pjsua2.CallOpParam = Mock
    mock_pjsua2.MediaFormat = Mock
    mock_pjsua2.MediaFormatAudio = Mock
    sys.modules["pjsua2"] = mock_pjsua2

# Exclude standalone scripts that aren't pytest tests
collect_ignore = ["test_asr_migration.py"]


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up test environment variables before each test."""
    # Set default test environment variables
    test_env = {
        "ES_HOST": "localhost",
        "ES_PORT": "9200",
        "ELASTIC_INDEX_PREFIX": "test_calls",
        "ELASTICSEARCH_HOST": "localhost",  # For backward compatibility
        "ELASTICSEARCH_PORT": "9200",  # For backward compatibility
        "ELASTICSEARCH_INDEX": "test_calls",  # For backward compatibility
    }
    for key, value in test_env.items():
        if key not in os.environ:
            monkeypatch.setenv(key, value)


@pytest.fixture
def mock_elasticsearch_client() -> Any:
    """Create a mock Elasticsearch client for testing."""
    mock_client = Mock()
    mock_client.info.return_value = {
        "cluster_name": "test-cluster",
        "version": {"number": "8.0.0"},
    }
    mock_client.ping.return_value = True
    mock_client.index.return_value = {"_id": "test-id", "_index": "test-index"}
    mock_client.cluster.health.return_value = {
        "status": "green",
        "number_of_nodes": 1,
        "active_shards": 1,
    }
    return mock_client


@pytest.fixture
def sample_call_data() -> dict[str, Any]:
    """Create sample call data for testing."""
    return {
        "call_id": "test-call-123",
        "timestamp": "2024-01-01T00:00:00Z",
        "caller_number": "+1234567890",
        "callee_ext": "100",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-01T00:05:00Z",
        "duration_sec": 300,
        "status": "completed",
        "direction": "incoming",
    }
