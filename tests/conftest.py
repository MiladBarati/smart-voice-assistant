"""Pytest configuration and fixtures for testing pjsua_bot.

This file sets up mocks for pjsua2 to enable testing without the actual C++ bindings.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, Mock

import pytest


# Create a mock pjsua2 module that can be used by tests
def create_mock_pjsua2() -> MagicMock:
    """Create a mock pjsua2 module for testing."""
    mock_pj = MagicMock()

    # Create proper base classes that don't cause recursion issues
    class MockAccount:
        """Mock pjsua2.Account base class."""

        def __init__(self) -> None:
            pass

        def getInfo(self) -> MagicMock:  # noqa: N802 - pjsua2 API uses camelCase
            return MagicMock()

    class MockCall:
        """Mock pjsua2.Call base class."""

        def __init__(self, acc: Any, call_id: int | None = None) -> None:
            pass

        def getId(self) -> int:  # noqa: N802 - pjsua2 API uses camelCase
            return 0

        def getInfo(self) -> MagicMock:  # noqa: N802 - pjsua2 API uses camelCase
            return MagicMock()

        def isActive(self) -> bool:  # noqa: N802 - pjsua2 API uses camelCase
            return True

        def getAudioMedia(  # noqa: N802 - pjsua2 API uses camelCase
            self, index: int
        ) -> MagicMock:
            return MagicMock()

        def answer(self, prm: Any = None) -> None:
            pass

    class MockEndpoint:
        """Mock pjsua2.Endpoint."""

        _instance: MockEndpoint | None = None

        @classmethod
        def instance(cls) -> MockEndpoint:
            if cls._instance is None:
                cls._instance = MockEndpoint()
            return cls._instance

        def libHandleEvents(  # noqa: N802 - pjsua2 API uses camelCase
            self, ms: int
        ) -> None:
            pass

        def audDevManager(self) -> MagicMock:  # noqa: N802 - pjsua2 API uses camelCase
            return MagicMock()

    mock_pj.Account = MockAccount
    mock_pj.Call = MockCall
    mock_pj.Endpoint = MockEndpoint
    mock_pj.AudioMediaPlayer = MagicMock
    mock_pj.AudioMediaRecorder = MagicMock
    mock_pj.CallOpParam = MagicMock
    mock_pj.EpConfig = MagicMock
    mock_pj.TransportConfig = MagicMock
    mock_pj.AccountConfig = MagicMock
    mock_pj.AuthCredInfo = MagicMock
    mock_pj.PJMEDIA_FILE_NO_LOOP = 1
    mock_pj.PJSIP_INV_STATE_CONFIRMED = 4
    mock_pj.PJSIP_INV_STATE_DISCONNECTED = 5
    mock_pj.PJMEDIA_TYPE_AUDIO = 0
    mock_pj.PJSUA_CALL_MEDIA_ACTIVE = 1
    mock_pj.PJSIP_TRANSPORT_UDP = 1
    mock_pj.PJSIP_TRANSPORT_TCP = 2
    mock_pj.PJSIP_TRANSPORT_TLS = 3
    mock_pj.Error = Exception

    return mock_pj


@pytest.fixture
def mock_pjsua2() -> MagicMock:
    """Fixture that provides a mock pjsua2 module."""
    return create_mock_pjsua2()


@pytest.fixture(autouse=True)
def reset_pjsua2_mock() -> Any:
    """Reset the pjsua2 mock before each test if it's being used."""
    # This fixture runs before each test but doesn't do anything by default
    # Individual tests can choose to use the mock_pjsua2 fixture
    yield


@pytest.fixture
def mock_elasticsearch_client() -> Mock:
    """Fixture that provides a mock Elasticsearch client."""
    mock_client = Mock()
    mock_info = Mock()
    mock_info.get.return_value = {
        "cluster_name": "test-cluster",
        "version": {"number": "8.0.0"},
    }
    mock_client.info.return_value = mock_info
    mock_client.ping.return_value = True
    mock_client.index.return_value = {"_id": "test_id", "result": "created"}
    return mock_client


@pytest.fixture
def sample_call_data() -> dict[str, Any]:
    """Fixture that provides sample call data for testing."""
    return {
        "call_id": "test_call_123",
        "timestamp": "2024-01-01T00:00:00Z",
        "caller": "1001",
        "callee": "1002",
        "duration": 60,
        "status": "completed",
    }
