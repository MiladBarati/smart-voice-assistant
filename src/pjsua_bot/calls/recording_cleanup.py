"""Recording cleanup mixin for call handlers.

Provides `_cleanup_recording` implementation extracted from the monolithic
`AnyCall` to keep responsibilities smaller.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from ..utils import convert_wav_to_mp3

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import pjsua2 as pj
else:
    try:
        import pjsua2 as pj  # pragma: no cover - depends on runtime env
    except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
        pj = None


class RecordingCleanupMixin:
    """Mixin encapsulating recording cleanup logic."""

    # Host-provided attributes (declared for type-checkers)
    _cleanup_done: bool
    _vad: Any | None
    _asr: Any | None
    _asr_chunk_texts: list[str]
    _last_transcribed_chunk_count: int
    _collect_event: Callable[..., None]

    _recorder: Any | None
    _recording_call_media: Any | None
    _recording_start_time: datetime | None
    _recording_duration: float
    _recording_file: str

    _outgoing_recorder: Any | None
    _outgoing_recording_call_media: Any | None
    _outgoing_recording_start_time: datetime | None
    _outgoing_recording_duration: float
    _outgoing_recording_file: str

    _mixed_recorder: Any | None
    _mixed_recording_start_time: datetime | None
    _mixed_recording_duration: float
    _mixed_recording_file: str
    _call_media: Any | None
    _player: Any | None

    if TYPE_CHECKING:

        def isActive(self) -> bool: ...  # noqa: N802

    def _cleanup_recording(self) -> None:
        """Clean up recording resources safely."""
        # Prevent double cleanup
        if getattr(self, "_cleanup_done", False):
            logger.info("Recording: cleanup already done, skipping")
            return
        self._cleanup_done = True

        self._finalize_vad_chunks()
        self._finalize_asr_transcription()

        # Clean up all recording types
        if getattr(self, "_recorder", None):
            self._cleanup_single_recording(
                recorder_attr="_recorder",
                call_media_attr="_recording_call_media",
                start_time_attr="_recording_start_time",
                duration_attr="_recording_duration",
                file_attr="_recording_file",
                recording_type="incoming",
                error_event_type="recording_cleanup_error",
            )

        if getattr(self, "_outgoing_recorder", None):
            self._cleanup_single_recording(
                recorder_attr="_outgoing_recorder",
                call_media_attr="_outgoing_recording_call_media",
                start_time_attr="_outgoing_recording_start_time",
                duration_attr="_outgoing_recording_duration",
                file_attr="_outgoing_recording_file",
                recording_type="outgoing",
                error_event_type="outgoing_recording_cleanup_error",
            )

        if getattr(self, "_mixed_recorder", None):
            self._cleanup_mixed_recording()

    def _finalize_vad_chunks(self) -> None:
        """Finalize any active VAD chunks before cleanup."""
        vad = getattr(self, "_vad", None)
        if vad is None or not getattr(vad, "available", False):
            return

        try:
            vad.finalize_all_chunks(time.time)
            chunks = vad.get_chunks()
            if chunks:
                logger.info("VAD: finalized %d voice chunk(s) at call end", len(chunks))
                for i, chunk in enumerate(chunks):
                    file_info = (
                        f", saved to {chunk.file_path}"
                        if chunk.file_path
                        else ", file not saved"
                    )
                    logger.info(
                        "VAD: chunk %d - duration=%.2fs, samples=%d-%d%s",
                        i + 1,
                        chunk.duration_seconds,
                        chunk.start_sample_idx,
                        chunk.end_sample_idx,
                        file_info,
                    )
        except Exception as e:
            logger.warning("VAD: error finalizing chunks: %s", e)

    def _finalize_asr_transcription(self) -> None:
        """Finalize ASR transcription at call end."""
        full_text = ""
        try:
            # Re-check ASR availability in case it became available after call start
            asr_enabled = getattr(self, "_asr_enabled", False)
            if asr_enabled:
                self._update_asr_availability()

            vad = getattr(self, "_vad", None)
            if (
                getattr(self, "_asr_enabled", False)
                and getattr(self, "_asr_available", False)
                and vad is not None
                and getattr(vad, "available", False)
            ):
                self._submit_remaining_chunks(vad)
                self._wait_for_transcription_tasks()
                full_text = self._get_final_transcription_text()

            logger.info(
                "ASR: full transcription: %s", full_text if full_text else "[empty]"
            )
        except Exception as e:
            logger.warning("ASR: error during final transcription: %s", e)

    def _update_asr_availability(self) -> None:
        """Update ASR availability and start thread if needed."""
        acc_ref = getattr(self, "_acc_ref", None)
        if not acc_ref:
            return

        asr_service = getattr(acc_ref, "_asr_service", None)
        asr_available = bool(
            getattr(acc_ref, "_asr_available", False)
            and asr_service is not None
            and getattr(asr_service, "available", False)
        )
        # Update ASR state
        self._asr = asr_service
        self._asr_available = asr_available
        if asr_available and not getattr(self, "_asr_available_was_false", False):
            logger.info("ASR: service became available during call")
            # Start worker thread if not already started
            start_asr_thread = getattr(self, "_start_asr_thread", None)
            if start_asr_thread:
                start_asr_thread()

    def _submit_remaining_chunks(self, vad: Any) -> None:
        """Submit remaining VAD chunks for transcription."""
        chunks = vad.get_chunks()
        start_idx = getattr(self, "_last_transcribed_chunk_count", 0)
        submit_task = getattr(self, "_submit_transcription_task", None)

        # Submit remaining chunks for transcription (non-blocking)
        for idx in range(start_idx, len(chunks)):
            ch = chunks[idx]
            if (
                ch.file_path
                and os.path.exists(ch.file_path)
                and submit_task is not None
            ):
                submit_task(ch.file_path, idx)

        self._last_transcribed_chunk_count = len(chunks)

    def _wait_for_transcription_tasks(self) -> None:
        """Wait for pending transcription tasks to complete."""
        asr_queue = getattr(self, "_asr_queue", None)
        if asr_queue is None:
            return

        try:
            timeout = 30.0  # Maximum wait time in seconds
            start_wait = time.time()
            # Wait for queue to be empty and all tasks to complete
            while (not asr_queue.empty() or asr_queue.unfinished_tasks > 0) and (
                time.time() - start_wait
            ) < timeout:
                time.sleep(0.1)
            # Warn if tasks remain after the timeout.
            if asr_queue.unfinished_tasks > 0:
                logger.warning(
                    "ASR: %d transcription task(s) still pending after timeout",
                    asr_queue.unfinished_tasks,
                )
        except Exception as e:
            logger.warning("ASR: error waiting for transcription tasks: %s", e)

    def _get_final_transcription_text(self) -> str:
        """Get final transcription text (thread-safe)."""
        asr_lock = getattr(self, "_asr_lock", None)
        chunk_texts = getattr(self, "_asr_chunk_texts", [])
        if asr_lock is not None:
            with asr_lock:
                return " ".join(t for t in chunk_texts if t).strip()
        else:
            return " ".join(t for t in chunk_texts if t).strip()

    def _check_call_active(self) -> bool:
        """Check if call is still active."""
        try:
            if hasattr(self, "isActive"):
                return bool(self.isActive())
        except Exception:
            # Call might be destroyed, assume inactive
            pass
        return False

    def _convert_recording_to_mp3(
        self, file_path: str, recording_type: str
    ) -> str | None:
        """Convert recording file to MP3, with retry if file not found.

        Returns the MP3 path if successful, None otherwise.
        """
        if not file_path:
            return None

        # Try immediate conversion
        if os.path.exists(file_path):
            logger.info(
                "Recording: %s file confirmed to exist at %s", recording_type, file_path
            )
            return self._attempt_mp3_conversion(file_path, recording_type)

        # File not found, wait and retry
        logger.warning("Recording: %s file not found at %s", recording_type, file_path)
        time.sleep(0.5)
        if os.path.exists(file_path):
            logger.info(
                "Recording: %s file found after delay at %s", recording_type, file_path
            )
            return self._attempt_mp3_conversion(file_path, recording_type)
        else:
            logger.warning(
                "Recording: %s file still not found after delay", recording_type
            )
            return None

    def _attempt_mp3_conversion(
        self, file_path: str, recording_type: str
    ) -> str | None:
        """Attempt to convert WAV file to MP3.

        Returns the MP3 path if successful, None otherwise.
        """
        logger.info("Recording: attempting to convert %s WAV to MP3...", recording_type)
        mp3_path = convert_wav_to_mp3(file_path, delete_source=True)
        if mp3_path:
            logger.info(
                "Recording: %s file converted to MP3 at %s", recording_type, mp3_path
            )
            return mp3_path
        else:
            logger.warning(
                "Recording: MP3 conversion failed (ffmpeg not available?), "
                "keeping WAV file"
            )
            return None

    def _cleanup_single_recording(
        self,
        recorder_attr: str,
        call_media_attr: str,
        start_time_attr: str,
        duration_attr: str,
        file_attr: str,
        recording_type: str,
        error_event_type: str,
    ) -> None:
        """Clean up a single recording (incoming or outgoing)."""
        try:
            call_active = self._check_call_active()

            # Try to stop transmission, but don't worry if it fails
            # (ports may already be disconnected)
            call_media = getattr(self, call_media_attr, None)
            recorder = getattr(self, recorder_attr, None)
            if call_media is not None and recorder is not None and call_active:
                try:
                    call_media.stopTransmit(recorder)
                except Exception:
                    # Ports already disconnected, ignore silently
                    pass

            # Don't explicitly destroy the recorder - let PJSUA2 handle it
            setattr(self, recorder_attr, None)
            setattr(self, call_media_attr, None)

            # Calculate recording duration
            start_time = getattr(self, start_time_attr, None)
            if start_time is not None:
                duration = (datetime.utcnow() - start_time).total_seconds()
                setattr(self, duration_attr, duration)
                logger.info(
                    "Recording: %s audio captured for %.2f seconds",
                    recording_type,
                    duration,
                )

            file_path = getattr(self, file_attr, None)
            logger.info(
                "Recording: %s audio stopped and saved to %s", recording_type, file_path
            )

            # Convert to MP3 if file exists
            if file_path:
                mp3_path = self._convert_recording_to_mp3(file_path, recording_type)
                if mp3_path:
                    setattr(self, file_attr, mp3_path)

        except Exception as e:
            logger.error(
                "%s recording cleanup error: %s", recording_type.capitalize(), e
            )
            # Collect recording cleanup error event
            try:
                self._collect_event(
                    event_type=error_event_type,
                    media_type="audio",
                    error=str(e),
                )
            except Exception:
                pass

    def _cleanup_mixed_recording(self) -> None:
        """Clean up mixed recording (incoming + outgoing combined)."""
        try:
            call_active = self._check_call_active()

            # Try to stop transmission from both sources, but don't worry
            # if it fails (ports may already be disconnected)
            call_media = getattr(self, "_call_media", None)
            player = getattr(self, "_player", None)
            mixed_recorder = getattr(self, "_mixed_recorder", None)

            if call_media is not None and mixed_recorder is not None and call_active:
                try:
                    call_media.stopTransmit(mixed_recorder)
                except Exception:
                    # Ports already disconnected, ignore silently
                    pass

            if player is not None and mixed_recorder is not None and call_active:
                try:
                    player.stopTransmit(mixed_recorder)
                except Exception:
                    # Ports already disconnected, ignore silently
                    pass

            # Don't explicitly destroy the recorder - let PJSUA2 handle it
            self._mixed_recorder = None

            # Calculate mixed recording duration
            start_time = getattr(self, "_mixed_recording_start_time", None)
            if start_time is not None:
                duration = (datetime.utcnow() - start_time).total_seconds()
                self._mixed_recording_duration = duration
                logger.info(
                    "Recording: mixed audio captured for %.2f seconds", duration
                )

            file_path = getattr(self, "_mixed_recording_file", None)
            logger.info("Recording: mixed audio stopped and saved to %s", file_path)

            # Convert to MP3 if file exists
            if file_path:
                mp3_path = self._convert_recording_to_mp3(file_path, "mixed")
                if mp3_path:
                    self._mixed_recording_file = mp3_path

        except Exception as e:
            logger.error("Mixed recording cleanup error: %s", e)
            # Collect mixed recording cleanup error event
            try:
                self._collect_event(
                    event_type="mixed_recording_cleanup_error",
                    media_type="audio",
                    error=str(e),
                )
            except Exception:
                pass
