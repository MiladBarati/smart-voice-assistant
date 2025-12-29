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
| `mixins/playback_monitor.py` | Tracks welcome playback, VAD-driven hangup, live chunk submission. |
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

## Follow-Up Ideas
- Add unit tests around each mixin to cover edge conditions.
- Evaluate moving shared recording utilities into a dedicated helper module.
- Document mixin lifecycle in developer onboarding guides.

