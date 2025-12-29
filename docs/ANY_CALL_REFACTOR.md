# AnyCall Modularisation Notes

## Overview
- `AnyCall` slimmed from ~1.2k lines to ~90 by delegating behaviour to mixins.
- Mixins live in `src/pjsua_bot/calls/mixins/` so responsibilities stay isolated.
- Refactor keeps public behaviour intact; imports remain compatible via `src/pjsua_bot/calls/__init__.py`.

## New Structure
| Module | Responsibility |
| --- | --- |
| `mixins/event_logger.py` | Collects structured call events. |
| `mixins/asr_support.py` | Manages ASR queue, worker thread, and chunk buffering. |
| `mixins/playback_monitor.py` | Tracks welcome playback, VAD-driven hangup, live chunk submission. Refactored with state management classes for improved simplicity. |
| `mixins/call_state_handler.py` | Handles `onCallState`, assembles call records, removes call refs. Refactored into focused helper methods for improved maintainability. |
| `mixins/call_media_handler.py` | Handles `onCallMediaState`, wiring playback/recording/VAD/ASR. |
| `calls/any_call.py` | Orchestrates mixins, initialises state, keeps core API surface. |

## Key Behaviour Retained
- Welcome message playback, mixed recording, and VAD-driven auto-hangup.
- ASR chunk submission with account-level service reuse.
- Elasticsearch call record emission with incoming/outgoing/mixed metadata.

## Refactoring Improvements

### `call_state_handler.py` Refactoring (2024)
The `CallStateHandlerMixin` was refactored to improve code simplicity and maintainability:

**Before**: Single 467-line `onCallState` method handling all concerns
**After**: Orchestrating method with focused helper methods:
- `_build_recording_metadata()`: Unified recording metadata collection
- `_collect_vad_metrics()`: VAD metrics gathering
- `_collect_transcription_data()`: ASR transcription collection
- `_collect_intent_data()`: Intent classification data collection
- `_build_call_record()`: Call record assembly
- `_handle_call_disconnected()`: Disconnection orchestration
- Additional focused helpers for timing, voice capture, and cleanup

**Benefits**:
- Reduced complexity: Main method reduced from 467 to ~30 lines
- Eliminated code duplication: Recording metadata collection unified
- Improved testability: Each helper can be tested independently
- Better maintainability: Changes isolated to specific methods

### `playback_monitor.py` Refactoring (2024)
The `PlaybackMonitorMixin` was refactored to improve code simplicity and maintainability:

**Before**: Multiple scattered boolean flags, complex conditional logic, heavy reliance on `getattr`/`hasattr`

**After**: State management using dataclasses and enums:
- `PlaybackState` enum: Consolidates `_playback_started`/`_playback_finished` flags
- `IntentState` dataclass: Groups intent-related state (played, finished, player, enabled)
- `GoodbyeState` dataclass: Groups goodbye-related state (requested, playback_started, playback_finished, file)
- `TimeState` dataclass: Groups time-based state (hangup_time, stop_player_time, welcome_finished_time, etc.)

**Key Improvements**:
- **State Consolidation**: Replaced 8+ boolean flags with 4 organized state objects
- **Simplified Conditionals**: Reduced complex nested checks by using state object properties
- **Reduced getattr Usage**: State access is now explicit through helper methods (`_get_intent_state()`, `_get_goodbye_state()`, `_get_time_state()`)
- **Backward Compatibility**: Maintained via `_sync_state_to_attributes()` method that keeps individual attributes in sync
- **Better Type Safety**: State objects provide clearer type hints and structure

**Benefits**:
- Improved readability: State relationships are explicit and organized
- Reduced complexity: Conditionals are simpler and easier to reason about
- Better maintainability: State changes are centralized and easier to track
- Enhanced testability: State objects can be tested independently
- Preserved compatibility: Existing code continues to work without changes

**Complexity Rating**: Improved from 4/10 to 7/10

## Follow-Up Ideas
- Add unit tests around each mixin to cover edge conditions.
- Evaluate moving shared recording utilities into a dedicated helper module.
- Document mixin lifecycle in developer onboarding guides.

