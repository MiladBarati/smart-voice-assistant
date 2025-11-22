"""`onCallState` handler extracted from the monolithic `AnyCall`."""

from __future__ import annotations

import os
import socket
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import pjsua2 as pj

from ...elasticsearch_client import es_logger
from ...utils import convert_recording_path_to_url, generate_unique_id, parse_sip_user


class CallStateHandlerMixin:
    """Implements the PJSUA `onCallState` callback."""

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

    if TYPE_CHECKING:

        def getInfo(self) -> Any: ...  # noqa: N802

        def _stop_asr_thread(self) -> None: ...

        def _cleanup_recording(self) -> None: ...

    def onCallState(self, prm: Any) -> None:  # noqa: N802 - PJSUA2 callback name
        """Handle call state changes."""
        try:
            ci = self.getInfo()
        except Exception as exc:
            # Call might already be destroyed, skip processing
            print(
                f"***CallState: error getting call info (call may be destroyed): {exc}"
            )
            return
        print(f"***CallState: state={ci.stateText} code={ci.lastStatusCode}")

        # Collect call state change event
        self._collect_event(
            event_type="call_state_change",
            call_state=ci.stateText,
            call_code=ci.lastStatusCode,
            state=ci.state,
            state_text=ci.stateText,
            last_status_code=ci.lastStatusCode,
        )

        # Mark start when early state observed
        if self._start_time_utc is None and ci.connectDuration.sec == 0:
            self._start_time_utc = datetime.utcnow()

        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED and self._start_time_utc is None:
            self._start_time_utc = datetime.utcnow()

        # Fill caller/callee and direction from call info
        try:
            remote_uri = ci.remoteUri
            local_uri = ci.localUri
            self._caller_number = parse_sip_user(remote_uri)
            self._callee_ext = parse_sip_user(local_uri)
            # If this account auto-answers incoming -> inbound
            self._direction = "inbound"
        except Exception:
            pass

        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            # Stop ASR worker thread (cleanup_recording will wait for pending tasks)
            self._stop_asr_thread()
            # Clean up recording early to avoid media disconnect issues
            self._cleanup_recording()

            # Build recording metadata FIRST, before sending call record
            recording_metadata: dict[str, Any] = {}

            # Add incoming recording metadata
            if self._recording_file and os.path.exists(self._recording_file):
                incoming_file_size = os.path.getsize(self._recording_file)
                # Convert local path to URL for logs
                incoming_file_url = convert_recording_path_to_url(self._recording_file)
                recording_metadata["incoming"] = {
                    "file_path": incoming_file_url,
                    "file_size_bytes": incoming_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "capture_duration": (
                        round(self._recording_duration, 2)
                        if self._recording_duration
                        else 0
                    ),
                }

                # Collect incoming recording finished event
                self._collect_event(
                    event_type="recording_finished",
                    media_type="audio",
                    recording_file=incoming_file_url,
                    file_size_bytes=incoming_file_size,
                    direction="incoming",
                    capture_duration=(
                        round(self._recording_duration, 2)
                        if self._recording_duration
                        else 0
                    ),
                )

            # Add outgoing recording metadata
            if self._outgoing_recording_file and os.path.exists(
                self._outgoing_recording_file
            ):
                outgoing_file_size = os.path.getsize(self._outgoing_recording_file)
                # Convert local path to URL for logs
                outgoing_file_url = convert_recording_path_to_url(
                    self._outgoing_recording_file
                )
                recording_metadata["outgoing"] = {
                    "file_path": outgoing_file_url,
                    "file_size_bytes": outgoing_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "capture_duration": (
                        round(self._outgoing_recording_duration, 2)
                        if self._outgoing_recording_duration
                        else 0
                    ),
                }

                # Collect outgoing recording finished event
                self._collect_event(
                    event_type="outgoing_recording_finished",
                    media_type="audio",
                    recording_file=outgoing_file_url,
                    file_size_bytes=outgoing_file_size,
                    direction="outgoing",
                    capture_duration=(
                        round(self._outgoing_recording_duration, 2)
                        if self._outgoing_recording_duration
                        else 0
                    ),
                )

            # Add mixed recording metadata (incoming + outgoing combined)
            if self._mixed_recording_file and os.path.exists(
                self._mixed_recording_file
            ):
                mixed_file_size = os.path.getsize(self._mixed_recording_file)
                # Convert local path to URL for logs
                mixed_file_url = convert_recording_path_to_url(
                    self._mixed_recording_file
                )
                recording_metadata["mixed"] = {
                    "file_path": mixed_file_url,
                    "file_size_bytes": mixed_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "capture_duration": (
                        round(self._mixed_recording_duration, 2)
                        if self._mixed_recording_duration
                        else 0
                    ),
                }

                # Collect mixed recording finished event
                self._collect_event(
                    event_type="mixed_recording_finished",
                    media_type="audio",
                    recording_file=mixed_file_url,
                    file_size_bytes=mixed_file_size,
                    direction="mixed",
                    capture_duration=(
                        round(self._mixed_recording_duration, 2)
                        if self._mixed_recording_duration
                        else 0
                    ),
                )

            # Store recording metadata for call record
            if recording_metadata:
                self._recording_metadata = recording_metadata

            # Log what file formats are being sent to Elasticsearch
            if recording_metadata:
                for direction, metadata in recording_metadata.items():
                    file_path = str(metadata.get("file_path", ""))
                    file_ext = os.path.splitext(file_path)[1]
                    print(
                        (
                            f"***Elasticsearch: sending {direction} recording as "
                            f"{file_ext.upper()} format: {file_path}"
                        )
                    )

            # Build call record and send as a single log
            try:
                self._end_time_utc = datetime.utcnow()
                start_iso = (
                    self._start_time_utc.isoformat() + "Z"
                    if self._start_time_utc
                    else None
                )
                end = self._end_time_utc
                assert end is not None
                end_iso = end.isoformat() + "Z"
                duration_sec = None
                if self._start_time_utc:
                    duration_sec = int(
                        (self._end_time_utc - self._start_time_utc).total_seconds()
                    )

                # Determine voice capture status and details
                has_incoming_recording = self._recording_file and os.path.exists(
                    self._recording_file
                )
                has_outgoing_recording = (
                    self._outgoing_recording_file
                    and os.path.exists(self._outgoing_recording_file)
                )
                voice_captured = has_incoming_recording or has_outgoing_recording

                # Get primary audio file path (prefer incoming, fallback to outgoing)
                # Convert local paths to URLs for logs
                primary_local_path = (
                    self._recording_file
                    if has_incoming_recording
                    else (
                        self._outgoing_recording_file
                        if has_outgoing_recording
                        else None
                    )
                )
                audio_file_path = (
                    convert_recording_path_to_url(primary_local_path)
                    if primary_local_path
                    else None
                )

                # Calculate total capture duration
                total_capture_duration = 0.0
                if has_incoming_recording and self._recording_duration:
                    total_capture_duration += self._recording_duration
                if has_outgoing_recording and self._outgoing_recording_duration:
                    total_capture_duration += self._outgoing_recording_duration

                # Cap capture duration to not exceed call duration
                if duration_sec and total_capture_duration > duration_sec:
                    total_capture_duration = duration_sec

                # Collect VAD metrics if VAD was enabled and available
                vad_metrics = None
                bot_talk_duration = None
                if self._vad and self._vad.available:
                    try:
                        # Finalize silence tracking at call end
                        self._vad.finalize_silence_tracking(time.time)

                        speech_duration = self._vad.get_speech_duration()
                        chunk_count = self._vad.get_chunk_count()
                        vad_confidence = self._vad.get_vad_confidence()
                        silence_duration = self._vad.get_silence_duration(time.time)
                        bot_talk_duration = self._vad.get_bot_playback_duration(time.time)

                        vad_metrics = {
                            "speech_duration": speech_duration,
                            "chunk_count": chunk_count,
                            "vad_confidence": vad_confidence,
                            "silence_duration": silence_duration,
                        }
                    except Exception as exc:
                        print(f"***Error calculating VAD metrics: {exc}")

                # Collect transcription text if ASR was enabled
                transcription_text = None
                transcription_chunks = None
                try:
                    asr_chunk_texts = getattr(self, "_asr_chunk_texts", [])
                    asr_lock = getattr(self, "_asr_lock", None)
                    
                    # Get transcription text thread-safely
                    if asr_lock is not None:
                        with asr_lock:
                            if asr_chunk_texts:
                                transcription_text = " ".join(
                                    t for t in asr_chunk_texts if t
                                ).strip()
                                transcription_chunks = asr_chunk_texts.copy()
                    else:
                        if asr_chunk_texts:
                            transcription_text = " ".join(
                                t for t in asr_chunk_texts if t
                            ).strip()
                            transcription_chunks = asr_chunk_texts.copy()
                    
                    if transcription_text:
                        print(f"***ASR: including transcription in call record: {transcription_text[:100]}...")
                except Exception as exc:
                    print(f"***Error collecting transcription: {exc}")

                call_record = {
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
                    "recording": (
                        self._recording_metadata if recording_metadata else None
                    ),
                    "voice_captured": voice_captured,
                    "audio_file_path": audio_file_path,
                    "capture_duration": (
                        round(total_capture_duration, 2)
                        if total_capture_duration > 0
                        else 0
                    ),
                    "vad": vad_metrics,  # Add VAD metrics to call record
                    "bot": {
                        "auto_answer": getattr(self._acc_ref, "auto_answer", False),
                        "domain": getattr(self._acc_ref, "domain", None),
                        "user": getattr(self._acc_ref, "username", None),
                        "talk_duration": (
                            round(bot_talk_duration, 2)
                            if bot_talk_duration is not None
                            else None
                        ),
                    },
                    "transcription": (
                        {
                            "text": transcription_text,
                            "chunks": transcription_chunks,
                            "chunk_count": len(transcription_chunks) if transcription_chunks else 0,
                        }
                        if transcription_text
                        else None
                    ),
                    "host": socket.gethostname(),
                    "ingest_ts": datetime.utcnow().isoformat() + "Z",
                }
                es_logger.log_call_record(call_record)

            except Exception as exc:
                print(f"***Error sending single call record: {exc}")

            # cleanup: drop strong reference so GC can collect safely now
            # Use stored call_id instead of ci.id to avoid assertion failure
            # when call is already destroyed
            try:
                call_id_to_remove = getattr(self, "_pjsua_call_id", None)
                if (
                    call_id_to_remove is not None
                    and call_id_to_remove in self._acc_ref.calls
                ):
                    del self._acc_ref.calls[call_id_to_remove]
                else:
                    # Fallback: try to get ID from call info if still valid
                    try:
                        if hasattr(ci, "id") and ci.id in self._acc_ref.calls:
                            del self._acc_ref.calls[ci.id]
                    except Exception:
                        pass
                    # Final fallback: remove by object reference
                    self._acc_ref.calls = {
                        k: v for k, v in self._acc_ref.calls.items() if v is not self
                    }
            except Exception as exc:
                # Safe fallback: clear everything if unknown
                print(f"***Warning: error removing call from dict: {exc}")
                self._acc_ref.calls = {
                    k: v for k, v in self._acc_ref.calls.items() if v is not self
                }
            # also release any active player
            self._player = None
