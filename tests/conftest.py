"""
Pytest configuration and fixtures for the PJSUA2 call monitoring system.
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch
from typing import Generator

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_elasticsearch_client():
    """Mock Elasticsearch client for testing."""
    mock_client = Mock()
    mock_client.index.return_value = {"_id": "test_id", "result": "created"}
    mock_client.search.return_value = {"hits": {"hits": []}}
    mock_client.ping.return_value = True
    return mock_client


@pytest.fixture
def mock_pjsua2():
    """Mock PJSUA2 library for testing."""
    with patch('pjsua2') as mock_pjsua2:
        # Mock common PJSUA2 classes
        mock_pjsua2.Endpoint.return_value = Mock()
        mock_pjsua2.Account.return_value = Mock()
        mock_pjsua2.Call.return_value = Mock()
        yield mock_pjsua2


@pytest.fixture
def sample_call_data():
    """Sample call data for testing."""
    return {
        "call_id": "test-call-123",
        "timestamp": "2025-01-25T10:00:00Z",
        "caller": "1001",
        "callee": "1002",
        "direction": "outgoing",
        "duration": 120,
        "status": "completed"
    }


@pytest.fixture
def temp_recording_dir(tmp_path):
    """Temporary directory for recording files during tests."""
    recording_dir = tmp_path / "recordings"
    recording_dir.mkdir()
    return recording_dir


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Store original values
    original_values = {}
    test_env = {
        "ES_HOST": "localhost",
        "ES_PORT": "9200",
        "ES_USERNAME": "elastic",
        "ES_PASSWORD": "",
        "ES_USE_SSL": "false",
        "ES_VERIFY_CERTS": "false",
        "ELASTIC_INDEX_PREFIX": "test-calls",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "ELASTICSEARCH_INDEX": "test_calls",
        "RECORDING_DIR": "/tmp/test_recordings"
    }
    
    # Store original values and set test values
    for key, value in test_env.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value
