#!/usr/bin/env python3
"""
Test batch logging functionality.
"""

from elasticsearch_client import es_logger

def test_batch_logging():
    """Test batch logging functionality."""
    print("Testing batch logging...")
    
    events = [
        {
            'event_type': 'test_event_1',
            'doc_type': 'call',
            'call_id': 'batch_test_1',
            'data': 'test1'
        },
        {
            'event_type': 'test_event_2', 
            'doc_type': 'media',
            'call_id': 'batch_test_1',
            'data': 'test2'
        },
        {
            'event_type': 'test_event_3',
            'doc_type': 'registration',
            'data': 'test3'
        }
    ]
    
    result = es_logger.log_batch_events(events)
    print(f"Batch logging: {'SUCCESS' if result else 'FAILED'}")
    
    return result

if __name__ == "__main__":
    test_batch_logging()
