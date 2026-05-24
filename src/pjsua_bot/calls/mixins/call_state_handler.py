"""`onCallState` handler extracted from the monolithic `AnyCall`.

This module implements the PJSUA `onCallState` callback handler, which manages
call state transitions and assembles comprehensive call records for Elasticsearch.

The module has been refactored into focused helper methods for improved maintainability:
- Recording metadata collection (incoming/outgoing/mixed)
- VAD metrics and bot talk duration tracking
- Transcription and intent data collection
- Call record assembly and Elasticsearch logging
- Call cleanup and reference management

The main `onCallState` method orchestrates these helpers, keeping the logic simple
and easy to follow.
"""

from __future__ import annotations

import logging
import os
import socket
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None

from ...elasticsearch_client import es_logger
from ...utils import convert_recording_path_to_url, generate_unique_id, parse_sip_user

logger = logging.getLogger(__name__)


class CallStateHandlerMixin:
    """Implements the PJSUA `onCallState` callback.

    This mixin handles call state changes and orchestrates the collection of call
    metadata when calls disconnect. It's responsible for:

    - Tracking call state transitions and emitting events
    - Collecting recording metadata (incoming/outgoing/mixed)
    - Gathering VAD metrics and bot talk duration
    - Collecting transcription and intent classification data
    - Building and sending comprehensive call records to Elasticsearch
    - Cleaning up call references when calls end

    The implementation is organized into focused helper methods:
    - `_build_recording_metadata()`: Consolidates recording metadata collection
    - `_collect_vad_metrics()`: Gathers VAD metrics and bot talk duration
    - `_collect_transcription_data()`: Collects ASR transcription text
    - `_collect_intent_data()`: Collects intent classification results
    - `_build_call_record()`: Assembles the complete call record dictionary
    - `_handle_call_disconnected()`: Orchestrates disconnection handling
    """

    _acc_ref: Any
    _collect_event: Callable[..., None]
    _start_time_utc: datetime | None
    _end_time_utc: datetime | None
    _direction: str | None
    _caller_number: str | None
    _callee_ext: str | None
    _recording_metadata: dict[str, Any] | None
    _recording_file: str
    _recording_duration: float
    _outgoing_recording_file: str
    _outgoing_recording_duration: float
    _mixed_recording_file: str
    _mixed_recording_duration: float
    _hangup_time: float | None
    _vad: Any | None
    _playback_started: bool
    _playback_finished: bool
    _bot_playback_start_time: float | None
    _total_bot_talk_duration: float
    _start_bot_playback_tracking: Callable[[], None]
    _stop_bot_playback_tracking: Callable[[], None]
    _get_total_bot_talk_duration: Callable[[], float]

    if TYPE_CHECKING:

        def getInfo(self) -> Any: ...  # noqa: N802

        def _stop_asr_thread(self) -> None: ...

        def _cleanup_recording(self) -> None: ...

    def _add_recording_metadata(
        self,
        recording_metadata: dict[str, Any],
        file_path: str,
        duration: float,
        direction: str,
        event_type: str,
    ) -> None:
        """Add recording metadata for a single recording direction."""
        if not file_path or not os.path.exists(file_path):
            return

        file_size = os.path.getsize(file_path)
        file_url = convert_recording_path_to_url(file_path)
        capture_duration = round(duration, 2) if duration else 0

        recording_metadata[direction] = {
            "file_path": file_url,
            "file_size_bytes": file_size,
            "recorded": True,
            "voice_captured": True,
            "capture_duration": capture_duration,
        }

        self._collect_event(
            event_type=event_type,
            media_type="audio",
            recording_file=file_url,
            file_size_bytes=file_size,
            direction=direction,
            capture_duration=capture_duration,
        )

    def _build_recording_metadata(self) -> dict[str, Any]:
        """Build recording metadata for all recording types."""
        recording_metadata: dict[str, Any] = {}

        self._add_recording_metadata(
            recording_metadata,
            self._recording_file,
            self._recording_duration,
            "incoming",
            "recording_finished",
        )

        self._add_recording_metadata(
            recording_metadata,
            self._outgoing_recording_file,
            self._outgoing_recording_duration,
            "outgoing",
            "outgoing_recording_finished",
        )

        self._add_recording_metadata(
            recording_metadata,
            self._mixed_recording_file,
            self._mixed_recording_duration,
            "mixed",
            "mixed_recording_finished",
        )

        if recording_metadata:
            self._recording_metadata = recording_metadata
            self._log_recording_formats(recording_metadata)

        return recording_metadata

    def _log_recording_formats(self, recording_metadata: dict[str, Any]) -> None:
        """Log file formats being sent to Elasticsearch."""
        for direction, metadata in recording_metadata.items():
            file_path = str(metadata.get("file_path", ""))
            file_ext = os.path.splitext(file_path)[1]
            logger.info(
                "Elasticsearch: sending %s recording as %s format: %s",
                direction,
                file_ext.upper(),
                file_path,
            )

    def _collect_vad_metrics(self) -> tuple[dict[str, Any] | None, float | None]:
        """Collect VAD metrics and bot talk duration."""
        if not (self._vad and self._vad.available):
            return None, None

        try:
            self._vad.finalize_silence_tracking(time.time)

            vad_metrics = {
                "speech_duration": self._vad.get_speech_duration(),
                "chunk_count": self._vad.get_chunk_count(),
                "vad_confidence": self._vad.get_vad_confidence(),
                "silence_duration": self._vad.get_silence_duration(time.time),
            }

            bot_talk_duration = self._vad.get_bot_playback_duration(time.time)
            return vad_metrics, bot_talk_duration
        except Exception as exc:
            logger.error("Error calculating VAD metrics: %s", exc, exc_info=True)
            return None, None

    def _get_bot_talk_duration(self) -> float:
        """Get bot talk duration from VAD or fallback to manual tracking."""
        # Try VAD first (preferred, more accurate)
        _, bot_talk_duration = self._collect_vad_metrics()
        if bot_talk_duration is not None:
            return bot_talk_duration

        # Finalize any ongoing bot playback session
        if hasattr(self, "_stop_bot_playback_tracking"):
            try:
                self._stop_bot_playback_tracking()
            except Exception as exc:
                logger.error(
                    "Bot tracking: error finalizing playback tracking: %s",
                    exc,
                    exc_info=True,
                )

        # Fall back to manually tracked duration
        if hasattr(self, "_get_total_bot_talk_duration"):
            try:
                return self._get_total_bot_talk_duration()
            except Exception as exc:
                logger.error(
                    "Bot tracking: error getting total duration: %s", exc, exc_info=True
                )

        return 0.0

    def _collect_transcription_data(
        self,
    ) -> tuple[str | None, list[str] | None]:
        """Collect transcription text and chunks if ASR was enabled."""
        try:
            asr_chunk_texts = getattr(self, "_asr_chunk_texts", [])
            asr_lock = getattr(self, "_asr_lock", None)

            if not asr_chunk_texts:
                return None, None

            # Get transcription text thread-safely
            if asr_lock is not None:
                with asr_lock:
                    transcription_text = " ".join(
                        t for t in asr_chunk_texts if t
                    ).strip()
                    transcription_chunks = asr_chunk_texts.copy()
            else:
                transcription_text = " ".join(t for t in asr_chunk_texts if t).strip()
                transcription_chunks = asr_chunk_texts.copy()

            if transcription_text:
                truncated = transcription_text[:100]
                logger.info(
                    "ASR: including transcription in call record: %s...", truncated
                )

            return transcription_text, transcription_chunks
        except Exception as exc:
            logger.error("Error collecting transcription: %s", exc, exc_info=True)
            return None, None

    def _collect_satisfaction_flow_data(self) -> dict[str, Any] | None:
        """Collect satisfaction-flow telemetry, if the flow was active.

        Returns a dict with `turns`, `retry_count`, `resolution`, and
        `escalation_*` fields when `flow_mode == "satisfaction"`, otherwise
        None so the call record key is omitted entirely.
        """
        try:
            flow_mode = getattr(self._acc_ref, "flow_mode", "legacy")
            if flow_mode != "satisfaction":
                return None

            flow_state = getattr(self, "_flow_state", None)
            if flow_state is None:
                return None

            turns_raw = getattr(flow_state, "turns", []) or []
            turns: list[dict[str, Any]] = []
            for turn in turns_raw:
                turns.append(
                    {
                        "index": getattr(turn, "index", None),
                        "question": getattr(turn, "question", None),
                        "intent": getattr(turn, "intent", None),
                        "intent_confidence": getattr(
                            turn, "intent_confidence", None
                        ),
                        "answer_audio": getattr(turn, "answer_audio", None),
                        "satisfaction": getattr(turn, "satisfaction", None),
                        "classification_failed": getattr(
                            turn, "classification_failed", False
                        ),
                    }
                )

            resolution = getattr(flow_state, "resolution", None)
            if resolution is None and turns_raw:
                # Caller hung up before the satisfaction state resolved.
                resolution = "hangup_no_answer"

            data: dict[str, Any] = {
                "flow_mode": "satisfaction",
                "turns": turns,
                "retry_count": int(getattr(flow_state, "retry_count", 0)),
                "max_satisfaction_retries": int(
                    getattr(flow_state, "max_satisfaction_retries", 2)
                ),
                "resolution": resolution,
            }

            escalation_succeeded = getattr(flow_state, "escalation_succeeded", None)
            if escalation_succeeded is not None:
                data["escalation_succeeded"] = bool(escalation_succeeded)
            if getattr(flow_state, "escalation_failed", False):
                data["escalation_failed"] = True

            return data
        except Exception as exc:
            logger.error(
                "Error collecting satisfaction-flow data: %s", exc, exc_info=True
            )
            return None

    def _collect_intent_data(self) -> dict[str, Any] | None:
        """Collect intent classification data if available."""
        try:
            intent_classified = getattr(self, "_intent_classified", False)
            if not intent_classified:
                return None

            classified_intent = getattr(self, "_classified_intent", None)
            intent_confidence = getattr(self, "_intent_confidence", None)
            intent_response_played = getattr(self, "_intent_response_played", False)
            intent_response_duration = getattr(self, "_intent_response_duration", None)
            intent_response_finished_time = getattr(
                self, "_intent_response_finished_time", None
            )

            # Convert finished time from float timestamp to ISO format
            finished_time_iso = None
            if intent_response_finished_time:
                try:
                    finished_time_iso = (
                        datetime.utcfromtimestamp(
                            intent_response_finished_time
                        ).isoformat()
                        + "Z"
                    )
                except Exception:
                    pass  # If conversion fails, leave as None

            intent_data = {
                "classified": intent_classified,
                "intent_name": classified_intent,
                "confidence": (
                    round(intent_confidence, 3)
                    if intent_confidence is not None
                    else None
                ),
                "response_played": intent_response_played,
                "response_duration": (
                    round(intent_response_duration, 2)
                    if intent_response_duration is not None
                    else None
                ),
                "response_finished_time": finished_time_iso,
            }

            if classified_intent:
                logger.info(
                    "Intent: including intent classification in call record: "
                    "'%s' (confidence: %.2f)",
                    classified_intent,
                    intent_confidence,
                )

            return intent_data
        except Exception as exc:
            logger.error("Error collecting intent data: %s", exc, exc_info=True)
            return None

    def _calculate_call_timing(self) -> tuple[str | None, str, int | None]:
        """Calculate call start, end, and duration."""
        self._end_time_utc = datetime.utcnow()
        start_iso = (
            self._start_time_utc.isoformat() + "Z" if self._start_time_utc else None
        )
        end_iso = self._end_time_utc.isoformat() + "Z"

        duration_sec = None
        if self._start_time_utc:
            duration_sec = int(
                (self._end_time_utc - self._start_time_utc).total_seconds()
            )

        return start_iso, end_iso, duration_sec

    def _calculate_voice_capture_info(
        self, duration_sec: int | None
    ) -> tuple[bool, str | None, float]:
        """Calculate voice capture status, audio file path, and total duration."""
        has_incoming = self._recording_file and os.path.exists(self._recording_file)
        has_outgoing = self._outgoing_recording_file and os.path.exists(
            self._outgoing_recording_file
        )
        voice_captured = bool(has_incoming or has_outgoing)

        # Get primary audio file path (prefer incoming, fallback to outgoing)
        primary_local_path = (
            self._recording_file
            if has_incoming
            else (self._outgoing_recording_file if has_outgoing else None)
        )
        audio_file_path = (
            convert_recording_path_to_url(primary_local_path)
            if primary_local_path
            else None
        )

        # Calculate total capture duration
        total_capture_duration = 0.0
        if has_incoming and self._recording_duration:
            total_capture_duration += self._recording_duration
        if has_outgoing and self._outgoing_recording_duration:
            total_capture_duration += self._outgoing_recording_duration

        # Cap capture duration to not exceed call duration
        if duration_sec and total_capture_duration > duration_sec:
            total_capture_duration = duration_sec

        return voice_captured, audio_file_path, total_capture_duration

    def _build_call_record(
        self,
        start_iso: str | None,
        end_iso: str,
        duration_sec: int | None,
        recording_metadata: dict[str, Any],
        voice_captured: bool,
        audio_file_path: str | None,
        total_capture_duration: float,
        vad_metrics: dict[str, Any] | None,
        bot_talk_duration: float,
        transcription_text: str | None,
        transcription_chunks: list[str] | None,
        intent_data: dict[str, Any] | None,
        satisfaction_flow_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the complete call record dictionary."""
        return {
            "event_type": "call_record",
            "call_id": generate_unique_id(),
            "caller_number": self._caller_number,
            "callee_ext": self._callee_ext,
            "start_time": start_iso,
            "end_time": end_iso,
            "duration_sec": duration_sec,
            "status": "disconnected",
            "direction": self._direction or "inbound",
            "media": {
                "file_played": getattr(self._acc_ref, "play_file", None),
                "playback_started": self._playback_started,
                "playback_finished": self._playback_finished,
            },
            "recording": recording_metadata if recording_metadata else None,
            "voice_captured": voice_captured,
            "audio_file_path": audio_file_path,
            "capture_duration": (
                round(total_capture_duration, 2) if total_capture_duration > 0 else 0
            ),
            "vad": vad_metrics,
            "bot": {
                "auto_answer": getattr(self._acc_ref, "auto_answer", False),
                "domain": getattr(self._acc_ref, "domain", None),
                "user": getattr(self._acc_ref, "username", None),
                "talk_duration": round(bot_talk_duration, 2),
            },
            "transcription": (
                {
                    "text": transcription_text,
                    "chunks": transcription_chunks,
                    "chunk_count": (
                        len(transcription_chunks) if transcription_chunks else 0
                    ),
                }
                if transcription_text
                else None
            ),
            "intent": intent_data if intent_data else None,
            "satisfaction_flow": (
                satisfaction_flow_data if satisfaction_flow_data else None
            ),
            "host": socket.gethostname(),
            "ingest_ts": datetime.utcnow().isoformat() + "Z",
        }

    def _send_collected_events(self) -> None:
        """Send collected events to Elasticsearch."""
        try:
            collected_events = getattr(self, "_collected_events", [])
            if not collected_events:
                return

            # Filter for intent-related events for logging
            intent_events = [
                event
                for event in collected_events
                if event.get("event_type")
                in ("intent_classified", "intent_response_played")
            ]
            if intent_events:
                logger.info(
                    "Elasticsearch: sending %d intent events in batch",
                    len(intent_events),
                )

            es_logger.log_batch_events(collected_events)
            logger.info(
                "Elasticsearch: sent %d collected events", len(collected_events)
            )
        except Exception as exc:
            logger.error("Error sending collected events: %s", exc, exc_info=True)

    def _cleanup_call_references(self, ci: Any) -> None:
        """Remove call from account's call dictionary."""
        try:
            call_id_to_remove = getattr(self, "_pjsua_call_id", None)
            if (
                call_id_to_remove is not None
                and call_id_to_remove in self._acc_ref.calls
            ):
                del self._acc_ref.calls[call_id_to_remove]
                return

            # Fallback: try to get ID from call info if still valid
            try:
                if hasattr(ci, "id") and ci.id in self._acc_ref.calls:
                    del self._acc_ref.calls[ci.id]
                    return
            except Exception:
                pass

            # Final fallback: remove by object reference
            self._acc_ref.calls = {
                k: v for k, v in self._acc_ref.calls.items() if v is not self
            }
        except Exception as exc:
            # Safe fallback: clear everything if unknown
            logger.warning("Error removing call from dict: %s", exc, exc_info=True)
            self._acc_ref.calls = {
                k: v for k, v in self._acc_ref.calls.items() if v is not self
            }

    def _handle_call_disconnected(self, ci: Any) -> None:
        """Handle call disconnection: collect data and send call record."""
        # Stop ASR worker thread (cleanup_recording will wait for pending tasks)
        self._stop_asr_thread()
        # Clean up recording early to avoid media disconnect issues
        self._cleanup_recording()

        # Build recording metadata FIRST, before sending call record
        recording_metadata = self._build_recording_metadata()

        # Build call record and send as a single log
        try:
            start_iso, end_iso, duration_sec = self._calculate_call_timing()

            voice_captured, audio_file_path, total_capture_duration = (
                self._calculate_voice_capture_info(duration_sec)
            )

            # Collect VAD metrics (this also gets bot_talk_duration from VAD)
            vad_metrics, _ = self._collect_vad_metrics()
            bot_talk_duration = self._get_bot_talk_duration()

            transcription_text, transcription_chunks = (
                self._collect_transcription_data()
            )
            intent_data = self._collect_intent_data()
            satisfaction_flow_data = self._collect_satisfaction_flow_data()

            call_record = self._build_call_record(
                start_iso=start_iso,
                end_iso=end_iso,
                duration_sec=duration_sec,
                recording_metadata=recording_metadata,
                voice_captured=voice_captured,
                audio_file_path=audio_file_path,
                total_capture_duration=total_capture_duration,
                vad_metrics=vad_metrics,
                bot_talk_duration=bot_talk_duration,
                transcription_text=transcription_text,
                transcription_chunks=transcription_chunks,
                intent_data=intent_data,
                satisfaction_flow_data=satisfaction_flow_data,
            )

            es_logger.log_call_record(call_record)
            self._send_collected_events()

        except Exception as exc:
            logger.error("Error sending single call record: %s", exc, exc_info=True)

        # Cleanup: drop strong reference so GC can collect safely now
        self._cleanup_call_references(ci)
        # Also release any active player
        self._player = None

    def _update_call_timing(self, ci: Any) -> None:
        """Update call start time if not already set."""
        if self._start_time_utc is None and ci.connectDuration.sec == 0:
            self._start_time_utc = datetime.utcnow()

        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED and self._start_time_utc is None:
            self._start_time_utc = datetime.utcnow()

    def _update_call_identifiers(self, ci: Any) -> None:
        """Fill caller/callee and direction from call info."""
        try:
            remote_uri = ci.remoteUri
            local_uri = ci.localUri
            self._caller_number = parse_sip_user(remote_uri)
            self._callee_ext = parse_sip_user(local_uri)
            # If this account auto-answers incoming -> inbound
            self._direction = "inbound"
        except Exception:
            pass

    def onCallState(self, prm: Any) -> None:  # noqa: N802 - PJSUA2 callback name
        """Handle call state changes."""
        try:
            ci = self.getInfo()
        except Exception as exc:
            # Call might already be destroyed, skip processing
            logger.error(
                "CallState: error getting call info (call may be destroyed): %s",
                exc,
                exc_info=True,
            )
            return

        logger.info("CallState: state=%s code=%s", ci.stateText, ci.lastStatusCode)

        # Collect call state change event
        self._collect_event(
            event_type="call_state_change",
            call_state=ci.stateText,
            call_code=ci.lastStatusCode,
            state=ci.state,
            state_text=ci.stateText,
            last_status_code=ci.lastStatusCode,
        )

        # Update call timing and identifiers
        self._update_call_timing(ci)
        self._update_call_identifiers(ci)

        # Handle disconnection
        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self._handle_call_disconnected(ci)
