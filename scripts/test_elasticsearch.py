#!/usr/bin/env python3
"""
Test script for Elasticsearch integration.
This script tests the connection and logs sample data to Elasticsearch.
"""

import sys

from pjsua_bot.elasticsearch_client import es_logger


def test_elasticsearch_connection():
    """Test Elasticsearch connection and log sample data."""
    print("Testing Elasticsearch connection...")

    # Test connection
    health = es_logger.health_check()
    print(f"Health check result: {health}")

    if health.get("status") != "connected":
        print("FAILED Failed to connect to Elasticsearch")
        return False

    print("SUCCESS Successfully connected to Elasticsearch")

    # Test logging different types of events
    print("\nTesting event logging...")

    # Test registration event
    success = es_logger.log_registration_event(
        event_type="registration_success",
        user="test_user",
        domain="test.example.com",
        status="OK",
        code=200,
        additional_data={"test": True},
    )
    print(f"Registration event logged: {'SUCCESS' if success else 'FAILED'}")

    # Test call event
    success = es_logger.log_call_event(
        event_type="incoming_call",
        call_id="test_call_123",
        call_state="ringing",
        call_code=180,
        remote_uri="sip:caller@example.com",
        local_uri="sip:test_user@test.example.com",
        additional_data={"test": True},
    )
    print(f"Call event logged: {'SUCCESS' if success else 'FAILED'}")

    # Test media event
    success = es_logger.log_media_event(
        event_type="playback_started",
        call_id="test_call_123",
        media_type="audio",
        file_played="welcome_message.wav",
        additional_data={"test": True},
    )
    print(f"Media event logged: {'SUCCESS' if success else 'FAILED'}")

    # Test call state change
    success = es_logger.log_call_event(
        event_type="call_connected",
        call_id="test_call_123",
        call_state="connected",
        call_code=200,
        duration=5.5,
        additional_data={"test": True},
    )
    print(f"Call state change logged: {'SUCCESS' if success else 'FAILED'}")

    # Test call end
    success = es_logger.log_call_event(
        event_type="call_disconnected",
        call_id="test_call_123",
        call_state="disconnected",
        call_code=200,
        duration=8.2,
        additional_data={"test": True},
    )
    print(f"Call end logged: {'SUCCESS' if success else 'FAILED'}")

    print("\nSUCCESS All tests completed!")
    print(
        "Check your Elasticsearch cluster at https://kibana.aminraay.ir "
        "to see the logged data."
    )
    print("Look for index: pjsua-calls")

    return True


if __name__ == "__main__":
    try:
        success = test_elasticsearch_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
