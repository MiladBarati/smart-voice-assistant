"""Recording cleanup mixin for call handlers.

Provides `_cleanup_recording` implementation extracted from the monolithic
`AnyCall` to keep responsibilities smaller.
"""

import os
from datetime import datetime
from typing import Any

from ..utils import convert_recording_path_to_url, convert_wav_to_mp3


class RecordingCleanupMixin:
    """Mixin encapsulating recording cleanup logic."""

    # Host-provided attributes (declared for type-checkers)
    _cleanup_done: bool
    _vad: Any | None
    _asr: Any | None
    _asr_chunk_texts: list[str]
    _last_transcribed_chunk_count: int
    _collect_event: Any

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

    def _cleanup_recording(self) -> None:
        """Clean up recording resources safely."""
        # Prevent double cleanup
        if getattr(self, "_cleanup_done", False):
            print("***Recording: cleanup already done, skipping")
            return
        self._cleanup_done = True
        
        # Finalize any active VAD chunks before cleanup
        vad = getattr(self, "_vad", None)
        if vad is not None and getattr(vad, "available", False):
            try:
                import time as time_module
                vad.finalize_all_chunks(time_module.time)
                chunks = vad.get_chunks()
                if chunks:
                    print(f"***VAD: finalized {len(chunks)} voice chunk(s) at call end")
                    for i, chunk in enumerate(chunks):
                        file_info = (
                            f", saved to {chunk.file_path}" if chunk.file_path else ", file not saved"
                        )
                        print(
                            "***VAD: chunk "
                            f"{i+1} - duration={chunk.duration_seconds:.2f}s, "
                            f"samples={chunk.start_sample_idx}-{chunk.end_sample_idx}"
                            f"{file_info}"
                        )
            except Exception as e:
                print(f"***VAD: error finalizing chunks: {e}")
        
        # Final transcription at call end:
        # transcribe any remaining chunks and print full text
        full_text = ""
        try:
            if (
                getattr(self, "_asr_enabled", False)
                and getattr(self, "_asr_available", False)
                and vad is not None
                and getattr(vad, "available", False)
            ):
                chunks = vad.get_chunks()
                start_idx = getattr(self, "_last_transcribed_chunk_count", 0)
                asr = getattr(self, "_asr", None)
                for idx in range(start_idx, len(chunks)):
                    ch = chunks[idx]
                    if ch.file_path and os.path.exists(ch.file_path) and asr is not None:
                        res = asr.transcribe(ch.file_path)
                        if res and getattr(res, 'text', None):
                            text = res.text.strip()
                            if text:
                                self._asr_chunk_texts.append(text)
                self._last_transcribed_chunk_count = len(chunks)
                full_text = " ".join(t for t in self._asr_chunk_texts if t).strip()
            print(
                f"***ASR: full transcription: {full_text if full_text else '[empty]'}"
            )
        except Exception as e:
            print(f"***ASR: error during final transcription: {e}")
        
        # Clean up incoming recording
        if getattr(self, "_recorder", None):
            try:
                # Try to stop transmission, but don't worry if it fails
                # (ports may already be disconnected)
                recording_call_media = getattr(self, "_recording_call_media", None)
                recorder = getattr(self, "_recorder", None)
                if recording_call_media is not None and recorder is not None:
                    try:
                        recording_call_media.stopTransmit(recorder)
                    except Exception:
                        # Ports already disconnected, ignore silently
                        pass
                
                # Don't explicitly destroy the recorder - let PJSUA2 handle it
                self._recorder = None
                
                self._recording_call_media = None
                
                # Calculate recording duration
                recording_start_time = getattr(self, "_recording_start_time", None)
                if recording_start_time is not None:
                    self._recording_duration = (
                        (datetime.utcnow() - recording_start_time).total_seconds()
                    )
                    print(
                        "***Recording: incoming audio captured for "
                        f"{self._recording_duration:.2f} seconds"
                    )
                
                print(
                    "***Recording: incoming audio stopped and saved to "
                    f"{getattr(self, '_recording_file', None)}"
                )
                
                # Check if file actually exists
                if getattr(self, "_recording_file", None):
                    if os.path.exists(self._recording_file):
                        print(
                            "***Recording: incoming file confirmed to exist at "
                            f"{self._recording_file}"
                        )
                        # Convert to MP3 and update reference if successful
                        print(
                            "***Recording: attempting to convert incoming WAV to MP3..."
                        )
                        mp3_path = convert_wav_to_mp3(
                            self._recording_file,
                            delete_source=True,
                        )
                        if mp3_path:
                            self._recording_file = mp3_path
                            print(
                                "***Recording: incoming file converted to MP3 at "
                                f"{self._recording_file}"
                            )
                        else:
                            print(
                                "***Recording: MP3 conversion failed (ffmpeg not available?), "
                                "keeping WAV file"
                            )
                    else:
                        print(
                            "***Recording: WARNING - incoming file not found at "
                            f"{self._recording_file}"
                        )
                        # Wait a moment and check again
                        # (PJSUA2 might need time to flush)
                        import time
                        time.sleep(0.5)
                        if os.path.exists(self._recording_file):
                            print(
                                "***Recording: incoming file found after delay at "
                                f"{self._recording_file}"
                            )
                            print(
                                "***Recording: attempting to convert incoming WAV to MP3..."
                            )
                            mp3_path = convert_wav_to_mp3(
                                self._recording_file,
                                delete_source=True,
                            )
                            if mp3_path:
                                self._recording_file = mp3_path
                                print(
                                    "***Recording: incoming file converted to MP3 at "
                                    f"{self._recording_file}"
                                )
                            else:
                                print(
                                    "***Recording: MP3 conversion failed (ffmpeg not available?), "
                                    "keeping WAV file"
                                )
                        else:
                            print(
                                "***Recording: incoming file still not found after delay"
                            )
                            
            except Exception as e:
                print(f"***Recording cleanup error: {e}")
                # Collect recording cleanup error event
                try:
                    self._collect_event(
                        event_type="recording_cleanup_error",
                        media_type="audio",
                        error=str(e)
                    )
                except Exception:
                    pass
        
        # Clean up outgoing recording
        if getattr(self, "_outgoing_recorder", None):
            try:
                # Try to stop transmission, but don't worry if it fails
                # (ports may already be disconnected)
                outgoing_call_media = getattr(self, "_outgoing_recording_call_media", None)
                outgoing_recorder = getattr(self, "_outgoing_recorder", None)
                if outgoing_call_media is not None and outgoing_recorder is not None:
                    try:
                        outgoing_call_media.stopTransmit(outgoing_recorder)
                    except Exception:
                        # Ports already disconnected, ignore silently
                        pass
                
                # Don't explicitly destroy the recorder - let PJSUA2 handle it
                self._outgoing_recorder = None
                
                self._outgoing_recording_call_media = None
                
                # Calculate outgoing recording duration
                outgoing_start_time = getattr(self, "_outgoing_recording_start_time", None)
                if outgoing_start_time is not None:
                    self._outgoing_recording_duration = (
                        (datetime.utcnow() - outgoing_start_time).total_seconds()
                    )
                    print(
                        "***Recording: outgoing audio captured for "
                        f"{self._outgoing_recording_duration:.2f} seconds"
                    )
                
                print(
                    "***Recording: outgoing audio stopped and saved to "
                    f"{getattr(self, '_outgoing_recording_file', None)}"
                )
                
                # Check if outgoing file actually exists
                if getattr(self, "_outgoing_recording_file", None):
                    if os.path.exists(self._outgoing_recording_file):
                        print(
                            "***Recording: outgoing file confirmed to exist at "
                            f"{self._outgoing_recording_file}"
                        )
                        # Convert to MP3 and update reference if successful
                        print(
                            "***Recording: attempting to convert outgoing WAV to MP3..."
                        )
                        mp3_path = convert_wav_to_mp3(
                            self._outgoing_recording_file,
                            delete_source=True,
                        )
                        if mp3_path:
                            self._outgoing_recording_file = mp3_path
                            print(
                                "***Recording: outgoing file converted to MP3 at "
                                f"{self._outgoing_recording_file}"
                            )
                        else:
                            print(
                                "***Recording: MP3 conversion failed (ffmpeg not available?), "
                                "keeping WAV file"
                            )
                    else:
                        print(
                            "***Recording: WARNING - outgoing file not found at "
                            f"{self._outgoing_recording_file}"
                        )
                        # Wait a moment and check again
                        # (PJSUA2 might need time to flush)
                        import time
                        time.sleep(0.5)
                        if os.path.exists(self._outgoing_recording_file):
                            print(
                                "***Recording: outgoing file found after delay at "
                                f"{self._outgoing_recording_file}"
                            )
                            print(
                                "***Recording: attempting to convert outgoing WAV to MP3..."
                            )
                            mp3_path = convert_wav_to_mp3(
                                self._outgoing_recording_file,
                                delete_source=True,
                            )
                            if mp3_path:
                                self._outgoing_recording_file = mp3_path
                                print(
                                    "***Recording: outgoing file converted to MP3 at "
                                    f"{self._outgoing_recording_file}"
                                )
                            else:
                                print(
                                    "***Recording: MP3 conversion failed (ffmpeg not available?), "
                                    "keeping WAV file"
                                )
                        else:
                            print(
                                "***Recording: outgoing file still not found after delay"
                            )
                            
            except Exception as e:
                print(f"***Outgoing recording cleanup error: {e}")
                # Collect outgoing recording cleanup error event
                try:
                    self._collect_event(
                        event_type="outgoing_recording_cleanup_error",
                        media_type="audio",
                        error=str(e)
                    )
                except Exception:
                    pass


