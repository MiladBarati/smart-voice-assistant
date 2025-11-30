"""Tests for EventLoggerMixin."""

from unittest.mock import Mock

from pjsua_bot.calls.mixins.event_logger import EventLoggerMixin


class MockCall(EventLoggerMixin):
    """Mock call class that uses EventLoggerMixin."""

    def __init__(self) -> None:
        self._init_event_logger()

    def getId(self) -> int:
        """Mock getId method."""
        return 123


class TestEventLoggerMixin:
    """Test cases for EventLoggerMixin."""

    def test_init_event_logger(self) -> None:
        """Test event logger initialization."""
        call = MockCall()
        assert call._collected_events == []

    def test_collect_event(self) -> None:
        """Test collecting an event."""
        call = MockCall()
        call._collect_event("test_event", key1="value1", key2="value2")

        assert len(call._collected_events) == 1
        event = call._collected_events[0]
        assert event["event_type"] == "test_event"
        assert event["key1"] == "value1"
        assert event["key2"] == "value2"
        assert event["call_id"] == "123"
        assert "@timestamp" in event

    def test_collect_multiple_events(self) -> None:
        """Test collecting multiple events."""
        call = MockCall()
        call._collect_event("event1")
        call._collect_event("event2")
        call._collect_event("event3")

        assert len(call._collected_events) == 3
        assert call._collected_events[0]["event_type"] == "event1"
        assert call._collected_events[1]["event_type"] == "event2"
        assert call._collected_events[2]["event_type"] == "event3"

    def test_collect_event_without_getid(self) -> None:
        """Test collecting event when getId is not available."""
        call = EventLoggerMixin()
        call._init_event_logger()
        # Don't add getId method
        call._collect_event("test_event")

        assert len(call._collected_events) == 1
        event = call._collected_events[0]
        assert event["call_id"] == "unknown"

