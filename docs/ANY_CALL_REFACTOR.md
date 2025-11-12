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
| `mixins/call_state_handler.py` | Handles `onCallState`, assembles call records, removes call refs. |
| `mixins/call_media_handler.py` | Handles `onCallMediaState`, wiring playback/recording/VAD/ASR. |
| `calls/any_call.py` | Orchestrates mixins, initialises state, keeps core API surface. |

## Key Behaviour Retained
- Welcome message playback, mixed recording, and VAD-driven auto-hangup.
- ASR chunk submission with account-level service reuse.
- Elasticsearch call record emission with incoming/outgoing/mixed metadata.

## Follow-Up Ideas
- Add unit tests around each mixin to cover edge conditions.
- Evaluate moving shared recording utilities into a dedicated helper module.
- Document mixin lifecycle in developer onboarding guides.

