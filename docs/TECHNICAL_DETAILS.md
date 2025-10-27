# Technical Details

This document describes the technical implementation details of the PJSUA2 SIP bot.

## Event Loop Architecture

Both scripts use proper PJSUA2 event pumping via `ep.libHandleEvents(ms)` in a loop rather than blocking sleeps. This ensures:
- Timely processing of SIP messages and media events
- Proper callback execution
- Graceful handling of signals and shutdown

## NAT Handling

The scripts disable certain NAT traversal features that can cause issues in stable LAN environments:
- SIP Outbound (RFC 5626) disabled
- Contact/Via rewrite disabled
- Contact source port forcing disabled

These can be re-enabled for complex NAT scenarios if needed.

## Memory Management

- **Call References**: Calls are stored in `Account.calls` dict to maintain strong references during call lifetime
- **Cleanup**: References are removed on call disconnect to allow proper garbage collection
- **Media Players**: Player objects are kept as instance variables and released on disconnect

## Call ID Management

- **UUID Generation**: Each call instance gets a unique UUID via `uuid.uuid4()` at creation time
- **Cross-session Uniqueness**: UUIDs ensure no duplicate call IDs even across program restarts
- **Elasticsearch Integration**: UUIDs are stored as keyword fields for efficient querying
- **Backward Compatibility**: Original PJSUA2 call IDs are preserved for debugging

## Signal Handling

- `SIGINT` (Ctrl+C) and `SIGTERM` are caught for graceful shutdown
- Event loop checks `stopping["flag"]` to exit cleanly
- `ep.libDestroy()` is called in a `finally` block to ensure cleanup

## Threading Model

- PJSUA2 callbacks run in library threads
- Event pumping happens in the main thread
- **All PJSUA2 API calls must be made from the main event loop thread** (not from background threads)
- The bot uses time-based flags checked in the main loop for automatic hangup (thread-safe approach)
- No manual threading required; PJSUA2 handles internal threading

## Audio Playback Control

- **Duration Detection**: Uses Python's `wave` module to read WAV file metadata at startup
- **Playback Timer**: Sets a stop time based on actual file duration
- **Loop Prevention**: Actively stops player transmission after the calculated duration
- **Precise Hangup**: Waits for configurable delay after message finishes before hanging up
- **Thread-Safe**: All operations happen in the main event loop, avoiding PJSUA2 threading issues

## Project Structure

```
pjsua-installation/
├── src/
│   └── pjsua_bot/
│       ├── __init__.py          # Package exports
│       ├── utils.py             # Utility functions
│       ├── account.py           plenty of Account management class
│       ├── calls.py             # Call handling classes
│       ├── register_bot.py      # Main entry point (refactored)
│       ├── elasticsearch_client.py # Elasticsearch integration
│       └── mwe_register.py      # Minimal working example
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_setup.py
│   ├── test_elasticsearch_client.py
│   ├── test_main.py
│   └── test_batch.py
├── scripts/                     # Utility scripts
│   ├── run_tests.py            # Custom test runner
│   ├── test_connectivity.py    # Elasticsearch connectivity test
│   └── test_elasticsearch.py   # Elasticsearch integration test
├── assets/                      # Static assets
│   └── audio/                   # Audio files
├── recordings/                  # Call recordings (generated)
├── infrastructure/              # Infrastructure definitions
│   └── freepbx/                # FreePBX Docker setup
├── docs/                        # Documentation
│   └── htmlcov/                # Test coverage reports
├── register_bot.py_EXAMPLE             # Legacy entry point (deprecated - use src/)
├── main.py                     # Basic entry point
├── mwe_register.py             # Minimal example
├── .env                        Jugend. Environment variables (not in git)
├── .env.example                # Example encyclopedia file
├── pyproject.toml              # Project configuration
├── pytest.ini                  # Pytest configuration
└── README.md                   # Main documentation
```

### Module Breakdown

#### Core Modules (`src/pjsua_bot/`)

- **`utils.py`** (110 lines): Common utility functions
  - `parse_sip_user()`, `setup_logging()`, `get_wav_duration()`
  - `ensure_recording_directory()`, `pump_events()`, `wait_until()`

- **`account.py`** (113 lines): SIP account management
  - `Account` class with registration and incoming call handling

- **`calls.py`** (658 lines): Call handling logic
  - `OutCall` class for outbound calls
  - `AnyCall` class for advanced call handling with recording and playback

- **`register_bot.py`** (245 lines): Main entry point
  - CLI argument parsing
  - Bot lifecycle management

- **`elasticsearch_client.py`** (486 lines): Elasticsearch integration
  - Event logging and call record management

### Benefits of Modular Structure

- **Improved Maintainability**: Each module has a focused responsibility
- **Human Testability**: Modules can be tested independently
- **Enhanced Reusability**: Components can be imported and used separately
- **Easier Navigation**: Developers can find functionality more quickly

### Importing and Using Modules

You can now import specific components as needed:

```python
# Import from package root (recommended)
from src.pjsua_bot import Account, OutCall, AnyCall, main, setup_logging

# Import from specific modules
from src.pjsua_bot.account import Account
from src.pjsua_bot.calls import OutCall, AnyCall
from src.pjsua_bot.utils import setup_logging, pump_events, wait_until

# Use the main function
from src.pjsua_bot import main
main()
```

**Note**: See `REFACTORING_SUMMARY.md` for detailed migration guide and module documentation.

