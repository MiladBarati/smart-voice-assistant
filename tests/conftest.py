"""Pytest configuration for tests."""

import os
from typing import Any
from unittest.mock import Mock

import pytest

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
