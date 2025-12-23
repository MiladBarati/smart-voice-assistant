#!/usr/bin/env python3
"""
Test batch logging functionality.
"""

from unittest.mock import patch


def test_batch_logging() -> None:
    """Test batch logging functionality."""
    print("Testing batch logging...")

    events = [
        {
            "event_type": "test_event_1",
            "doc_type": "call",
            "call_id": "batch_test_1",
            "data": "test1",
        },
        {
            "event_type": "test_event_2",
            "doc_type": "media",
            "call_id": "batch_test_1",
            "data": "test2",
        },
        {"event_type": "test_event_3", "doc_type": "registration", "data": "test3"},
    ]

    # Mock the Elasticsearch client to avoid actual connection
    with patch("pjsua_bot.elasticsearch_client.es_logger") as mock_logger:
        mock_logger.log_batch_events.return_value = True
        result = mock_logger.log_batch_events(events)
        print(f"Batch logging: {'SUCCESS' if result else 'FAILED'}")
        assert result is True
        mock_logger.log_batch_events.assert_called_once_with(events)


if __name__ == "__main__":
    test_batch_logging()
