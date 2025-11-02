"""Silero VAD integration utilities.

This module provides a thin wrapper around Silero VAD for incremental
processing of growing WAV recordings. It is designed to be called
periodically from the event pump to detect the last time speech was
observed from the caller.
"""

from __future__ import annotations

import io
import os
import time
import wave
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

import numpy as np

try:
    import torch
    import torchaudio
    _TORCH_AVAILABLE = True
    _TORCH_ERROR = None
except ImportError as e:  # pragma: no cover - optional dependency at runtime
    torch = None  # type: ignore
    torchaudio = None  # type: ignore
    _TORCH_AVAILABLE = False
    _TORCH_ERROR = str(e)
except Exception as e:
    torch = None  # type: ignore
    torchaudio = None  # type: ignore
    _TORCH_AVAILABLE = False
    _TORCH_ERROR = str(e)


@dataclass
class VoiceChunk:
    """Represents a detected voice chunk with boundary information."""
    start_time_monotonic: float
    end_time_monotonic: float
    start_sample_idx: int  # Sample index in original WAV file
    end_sample_idx: int    # Sample index in original WAV file
    duration_seconds: float
    sample_rate: int
    file_path: Optional[str] = None  # Path to saved chunk file, if saved


@dataclass
class VADConfig:
    target_sample_rate: int = 16000
    threshold: float = 0.5  # Silero default
    min_speech_duration_ms: int = 150
    min_silence_duration_ms: int = 100
    window_size_samples: int = 16000 // 10  # 100ms
    max_chunk_duration_sec: float = 15.0  # Maximum chunk duration in seconds
    min_chunk_duration_sec: float = 3.0  # Minimum chunk duration in seconds
    min_silence_for_boundary_sec: float = 0.5  # Minimum silence duration to create chunk boundary


class SileroVAD:
    """Incremental VAD over a growing WAV file recorded by PJSUA2.

    Usage:
    - Create once per call using the path to the incoming recording WAV file
    - Call `process_new_audio()` periodically; it will read appended frames only
    - Check `last_speech_time_monotonic` to decide on hangup timing
    """

    def __init__(self, wav_path: str, config: Optional[VADConfig] = None, chunks_output_dir: Optional[str] = None):
        self.wav_path = wav_path
        self.cfg = config or VADConfig()
        self._model = None
        self._last_frame_idx = 0  # in samples at original wav sample rate
        self._wav_sample_rate: Optional[int] = None
        self._resampler = None
        self.last_speech_time_monotonic: Optional[float] = None
        self.available: bool = False
        self._load_error: Optional[str] = None
        # Cache for manual parsing
        self._manual_wav_info: Optional[Tuple[int, int, int, int]] = None  # (channels, sampwidth, framerate, data_offset)
        
        # Chunk tracking state
        self._chunks: List[VoiceChunk] = []  # Completed chunks
        self._current_chunk_start_time: Optional[float] = None  # Monotonic time when current chunk started
        self._current_chunk_start_sample: Optional[int] = None  # Sample index when current chunk started
        self._current_chunk_end_sample: Optional[int] = None  # Last sample index in current chunk
        self._last_speech_sample: Optional[int] = None  # Last sample index where speech was detected
        self._silence_start_time: Optional[float] = None  # Monotonic time when current silence period started
        
        # Chunk saving configuration
        self._chunks_output_dir = chunks_output_dir  # Directory to save chunk files
        self._chunk_counter = 0  # Counter for chunk filenames
        
        # VAD confidence tracking for metrics
        self._speech_probabilities: List[float] = []  # Track probabilities for speech frames
        
        # Silence duration tracking
        self._bot_playback_active: bool = False  # Track when bot is playing audio
        self._current_silence_start: Optional[float] = None  # Start time of current silence period
        self._total_silence_duration: float = 0.0  # Cumulative silence duration (when neither party speaks)
        self._call_start_time: Optional[float] = None  # Call start time for silence tracking
        
        self._load_model_if_possible()

    def _load_model_if_possible(self) -> None:
        if torch is None:
            self._load_error = f"torch/torchaudio not available: {_TORCH_ERROR or 'import failed'}"
            return
        try:
            model_result = torch.hub.load(
                'snakers4/silero-vad', 'silero_vad', force_reload=False, onnx=False
            )
            # Handle both cases: model can be returned directly or as a tuple (model, utils)
            if isinstance(model_result, tuple):
                self._model = model_result[0]  # Extract model from tuple
            else:
                self._model = model_result
            self._model.eval()
            self.available = True
            self._load_error = None
        except Exception as e:
            # leave unavailable; caller will skip VAD
            self._model = None
            self.available = False
            self._load_error = f"model loading failed: {str(e)}"

    def _ensure_resampler(self, input_sr: int):
        if torch is None or torchaudio is None:
            return None
        if self._resampler is None and input_sr != self.cfg.target_sample_rate:
            self._resampler = torchaudio.transforms.Resample(
                orig_freq=input_sr,
                new_freq=self.cfg.target_sample_rate,
            )
        return self._resampler

    def _is_wav_ready(self) -> bool:
        """Check if the WAV file is ready (has valid headers and can be opened).
        
        WAV files need at least 44 bytes for headers, and should start with 'RIFF'.
        We also try to actually open it with wave.open() to ensure it's truly ready.
        """
        if not os.path.exists(self.wav_path):
            return False
        
        # Check file size - WAV headers are at least 44 bytes
        try:
            size = os.path.getsize(self.wav_path)
            if size < 44:
                return False
            
            # Check if it starts with RIFF (WAV file signature)
            with open(self.wav_path, 'rb') as f:
                header = f.read(12)
                if len(header) < 12 or not header.startswith(b'RIFF'):
                    return False
                # Check for 'WAVE' after RIFF
                if header[8:12] != b'WAVE':
                    return False
            
            # Try to actually open it with wave.open() to verify it's readable
            # For streaming WAV files, wave.open() might fail initially even with valid headers
            # So we'll be lenient: if file has RIFF/WAVE and substantial data, try reading it anyway
            try:
                with wave.open(self.wav_path, 'rb') as test_wf:
                    # Try to read the header info
                    test_wf.getnchannels()
                    test_wf.getframerate()
                    test_wf.getnframes()
                # Success! Cache that it's ready
                self._file_was_ready = True
                return True
            except (wave.Error, Exception):
                # File has RIFF header but wave.open() fails
                # For streaming files being written by PJSUA2, this might be normal
                # If file is large enough (has data), we'll try reading it anyway
                # The actual read will handle errors gracefully
                if size > 1000:  # File has substantial data (more than just header)
                    # Cache that we've seen it ready once to avoid repeated checks
                    if not hasattr(self, '_file_was_ready'):
                        self._file_was_ready = False
                    return True  # Try reading it - errors will be handled in _read_new_frames
                return False
        except Exception:
            return False
        
        return False
    
    def _parse_wav_header(self) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """Manually parse WAV file header to get format info.
        
        Returns (n_channels, sampwidth, framerate, data_offset) or (None, None, None, None) on error.
        """
        try:
            with open(self.wav_path, 'rb') as f:
                # Read RIFF header
                riff = f.read(4)
                if riff != b'RIFF':
                    return None, None, None, None
                
                # Skip file size (4 bytes)
                f.read(4)
                
                # Read WAVE header
                wave = f.read(4)
                if wave != b'WAVE':
                    return None, None, None, None
                
                # Find 'fmt ' chunk
                fmt_found = False
                while True:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        return None, None, None, None
                    
                    chunk_size = int.from_bytes(f.read(4), 'little')
                    
                    if chunk_id == b'fmt ':
                        fmt_found = True
                        # Read fmt chunk data
                        audio_format = int.from_bytes(f.read(2), 'little')
                        n_channels = int.from_bytes(f.read(2), 'little')
                        framerate = int.from_bytes(f.read(4), 'little')
                        f.read(4)  # byte_rate
                        f.read(2)  # block_align
                        bits_per_sample = int.from_bytes(f.read(2), 'little')
                        # Convert bits to bytes (Python's wave module uses bytes)
                        sampwidth = bits_per_sample // 8
                        
                        # Skip any remaining fmt chunk data
                        if chunk_size > 16:
                            f.read(chunk_size - 16)
                        break
                    else:
                        # Skip this chunk
                        f.read(chunk_size)
                
                if not fmt_found:
                    return None, None, None, None
                
                # Find 'data' chunk
                data_offset = None
                while True:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        break
                    
                    chunk_size = int.from_bytes(f.read(4), 'little')
                    
                    if chunk_id == b'data':
                        data_offset = f.tell()
                        break
                    else:
                        # Skip this chunk
                        f.read(chunk_size)
                
                if data_offset is None:
                    return None, None, None, None
                
                return n_channels, sampwidth, framerate, data_offset
                
        except Exception:
            return None, None, None, None
    
    def _read_new_frames(self) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Read newly appended PCM frames from the WAV file.

        Returns a tuple (float32_pcm, input_sample_rate). The pcm is mono float32 in [-1, 1].
        Returns (None, None) if no new data available or file isn't ready yet.
        """
        if not os.path.exists(self.wav_path):
            return None, None
        
        # Wait for WAV file to be ready (headers complete)
        if not self._is_wav_ready():
            # Debug: report that we're waiting for file to be ready
            if not hasattr(self, '_last_wait_time'):
                self._last_wait_time = 0
            import time as time_module
            if time_module.time() - self._last_wait_time > 3.0:
                try:
                    size = os.path.getsize(self.wav_path)
                    print(f"***VAD: waiting for WAV file to be ready (size={size} bytes)")
                except Exception:
                    print(f"***VAD: waiting for WAV file to be ready")
                self._last_wait_time = time_module.time()
            return None, None

        # Try to use wave.open() first, but fall back to manual parsing if it fails
        try:
            with wave.open(self.wav_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()

                if self._wav_sample_rate is None:
                    self._wav_sample_rate = framerate
                    # Debug: print file info on first read
                    import time as time_module
                    print(f"***VAD: WAV file opened - {n_channels}ch, {sampwidth}byte/sample, {framerate}Hz, {n_frames} frames")

                if n_frames <= self._last_frame_idx:
                    # Debug: occasionally report that we're waiting for new data
                    if not hasattr(self, '_last_no_data_time'):
                        self._last_no_data_time = 0
                    import time as time_module
                    if time_module.time() - self._last_no_data_time > 5.0:
                        print(f"***VAD: waiting for new audio (last_idx={self._last_frame_idx}, total={n_frames})")
                        self._last_no_data_time = time_module.time()
                    return None, None

                wf.setpos(self._last_frame_idx)
                frames_to_read = n_frames - self._last_frame_idx
                raw = wf.readframes(frames_to_read)
                self._last_frame_idx = n_frames
                
        except (wave.Error, Exception):
            # wave.open() failed - try manual parsing for streaming WAV files
            # Cache the parsed info to avoid re-parsing every time
            if self._manual_wav_info is None:
                self._manual_wav_info = self._parse_wav_header()
            
            if self._manual_wav_info is None or any(x is None for x in self._manual_wav_info):
                # Can't parse header - wait for file to be ready
                if not hasattr(self, '_last_error_time'):
                    self._last_error_time = 0
                import time as time_module
                if time_module.time() - self._last_error_time > 10.0:
                    print(f"***VAD: WAV read error - cannot parse WAV header (trying manual parsing)")
                    self._last_error_time = time_module.time()
                return None, None
            
            n_channels, sampwidth, framerate, data_offset = self._manual_wav_info
            
            # Initialize on first read
            if self._wav_sample_rate is None:
                self._wav_sample_rate = framerate
                import time as time_module
                # Fix display - sampwidth is in bytes, but output was confusing
                print(f"***VAD: WAV file parsed manually - {n_channels}ch, {sampwidth*8}bit/sample, {framerate}Hz")
            
            # Read new frames manually
            try:
                with open(self.wav_path, 'rb') as f:
                    bytes_per_frame = n_channels * sampwidth
                    current_data_pos = data_offset + (self._last_frame_idx * bytes_per_frame)
                    
                    # Calculate how much data is available
                    file_size = os.path.getsize(self.wav_path)
                    available_bytes = file_size - current_data_pos
                    
                    # Debug occasionally
                    if not hasattr(self, '_last_debug_time'):
                        self._last_debug_time = 0
                    import time as time_module
                    if time_module.time() - self._last_debug_time > 5.0:
                        print(f"***VAD: manual read - file_size={file_size}, data_offset={data_offset}, current_pos={current_data_pos}, available={available_bytes}, bytes_per_frame={bytes_per_frame}, last_idx={self._last_frame_idx}")
                        self._last_debug_time = time_module.time()
                    
                    if available_bytes < bytes_per_frame:
                        # No new frames available
                        if not hasattr(self, '_last_no_data_time'):
                            self._last_no_data_time = 0
                        import time as time_module
                        if time_module.time() - self._last_no_data_time > 5.0:
                            print(f"***VAD: waiting for new audio (manual read)")
                            self._last_no_data_time = time_module.time()
                        return None, None
                    
                    # Seek to current position and read
                    f.seek(current_data_pos)
                    raw = f.read(available_bytes)
                    frames_read = len(raw) // bytes_per_frame
                    self._last_frame_idx += frames_read
                    
                    # Debug: report occasionally when we read frames (reduce spam)
                    if frames_read > 0:
                        if not hasattr(self, '_last_read_report_time'):
                            self._last_read_report_time = 0
                        import time as time_module
                        if time_module.time() - self._last_read_report_time > 5.0:
                            print(f"***VAD: read {frames_read} frames ({len(raw)} bytes) manually (total_idx={self._last_frame_idx})")
                            self._last_read_report_time = time_module.time()
                    
            except Exception as e:
                # Error reading manually
                if not hasattr(self, '_last_error_time'):
                    self._last_error_time = 0
                import time as time_module
                if time_module.time() - self._last_error_time > 10.0:
                    print(f"***VAD: manual read error: {e}")
                    self._last_error_time = time_module.time()
                return None, None

        if not raw:
            return None, None

        # Convert raw bytes to mono float32
        dtype = {1: np.int8, 2: np.int16, 3: None, 4: np.int32}.get(sampwidth)  # type: ignore
        if dtype is None:
            # 24-bit not handled; skip
            return None, None
        pcm = np.frombuffer(raw, dtype=dtype)
        if n_channels > 1:
            pcm = pcm.reshape(-1, n_channels).mean(axis=1)
        # normalize to float32 -1..1
        max_val = float(np.iinfo(dtype).max)
        pcm_f32 = (pcm.astype(np.float32) / max_val).clip(-1.0, 1.0)
        return pcm_f32, framerate

    def _start_new_chunk(self, monotonic_time: float, start_sample_idx: int) -> None:
        """Start tracking a new voice chunk."""
        self._current_chunk_start_time = monotonic_time
        self._current_chunk_start_sample = start_sample_idx
        self._current_chunk_end_sample = start_sample_idx
        self._last_speech_sample = start_sample_idx
        self._silence_start_time = None
        if not hasattr(self, '_chunk_count'):
            self._chunk_count = 0
        self._chunk_count += 1

    def _save_chunk_audio_internal(self, start_sample: int, end_sample: int, duration: float) -> Optional[str]:
        """Internal method to save chunk audio using sample indices.
        
        Returns the path to the saved chunk file, or None on error.
        """
        if self._chunks_output_dir is None:
            return None
        
        # Ensure output directory exists
        try:
            os.makedirs(self._chunks_output_dir, exist_ok=True)
        except Exception as e:
            print(f"***VAD: error creating chunks directory: {e}")
            return None
        
        # Generate chunk filename
        self._chunk_counter += 1
        import time as time_module
        chunk_filename = f"chunk_{self._chunk_counter:04d}_{int(time_module.time())}.wav"
        chunk_path = os.path.join(self._chunks_output_dir, chunk_filename)
        
        try:
            # Read chunk audio from the original WAV file
            # Note: If the WAV file is still being written (streaming), wave.open() might fail
            # In that case, we fall back to manual reading
            with wave.open(self.wav_path, 'rb') as wf_in:
                n_channels = wf_in.getnchannels()
                sampwidth = wf_in.getsampwidth()
                framerate = wf_in.getframerate()
                
                # Check if we have enough frames available
                n_frames = wf_in.getnframes()
                if end_sample > n_frames:
                    # File is still growing, use manual reading which handles partial data
                    return self._save_chunk_audio_manual(start_sample, end_sample, chunk_path)
                
                # Seek to start of chunk
                wf_in.setpos(start_sample)
                
                # Read chunk samples
                num_samples = end_sample - start_sample
                if num_samples <= 0:
                    print(f"***VAD: invalid chunk sample range ({start_sample}-{end_sample})")
                    return None
                
                raw_audio = wf_in.readframes(num_samples)
                
                if len(raw_audio) == 0:
                    # No data read, try manual method
                    return self._save_chunk_audio_manual(start_sample, end_sample, chunk_path)
                
                # Write chunk to new WAV file
                with wave.open(chunk_path, 'wb') as wf_out:
                    wf_out.setnchannels(n_channels)
                    wf_out.setsampwidth(sampwidth)
                    wf_out.setframerate(framerate)
                    wf_out.writeframes(raw_audio)
                
                print(f"***VAD: saved chunk {self._chunk_counter} to {chunk_path} ({duration:.2f}s)")
                return chunk_path
                
        except wave.Error as e:
            # wave.open() failed (likely streaming file), use manual reading
            return self._save_chunk_audio_manual(start_sample, end_sample, chunk_path)
        except Exception as e:
            print(f"***VAD: error saving chunk: {e}")
            # Try manual method as fallback
            try:
                return self._save_chunk_audio_manual(start_sample, end_sample, chunk_path)
            except Exception as e2:
                print(f"***VAD: error saving chunk manually: {e2}")
                return None
    
    def _save_chunk_audio_manual(self, start_sample: int, end_sample: int, chunk_path: str) -> Optional[str]:
        """Manually extract and save chunk audio using raw file I/O.
        
        Fallback method when wave.open() fails (e.g., for streaming files).
        """
        if self._manual_wav_info is None:
            self._manual_wav_info = self._parse_wav_header()
        
        if self._manual_wav_info is None or any(x is None for x in self._manual_wav_info):
            return None
        
        n_channels, sampwidth, framerate, data_offset = self._manual_wav_info
        
        try:
            # Check file size to ensure we don't read beyond available data
            file_size = os.path.getsize(self.wav_path)
            bytes_per_frame = n_channels * sampwidth
            
            # Calculate byte positions
            start_byte_pos = data_offset + (start_sample * bytes_per_frame)
            num_samples = end_sample - start_sample
            num_bytes = num_samples * bytes_per_frame
            
            if num_samples <= 0:
                return None
            
            # Check if we have enough data in the file
            end_byte_pos = start_byte_pos + num_bytes
            if end_byte_pos > file_size:
                # File might still be growing, try reading what we can
                available_bytes = max(0, file_size - start_byte_pos)
                if available_bytes == 0:
                    print(f"***VAD: chunk data not available yet (file_size={file_size}, needed={end_byte_pos})")
                    return None
                # Adjust num_bytes to available data
                num_bytes = available_bytes
                num_samples = available_bytes // bytes_per_frame
                if num_samples == 0:
                    return None
                print(f"***VAD: warning - chunk file incomplete, reading {num_bytes}/{end_sample - start_sample} bytes")
            
            with open(self.wav_path, 'rb') as f_in:
                # Seek to start and read chunk audio
                f_in.seek(start_byte_pos)
                raw_audio = f_in.read(num_bytes)
                
                if len(raw_audio) != num_bytes:
                    print(f"***VAD: warning - read {len(raw_audio)} bytes, expected {num_bytes}")
                    if len(raw_audio) == 0:
                        return None
                
                # Write chunk to new WAV file
                with wave.open(chunk_path, 'wb') as wf_out:
                    wf_out.setnchannels(n_channels)
                    wf_out.setsampwidth(sampwidth)
                    wf_out.setframerate(framerate)
                    wf_out.writeframes(raw_audio)
                
                return chunk_path
                
        except Exception as e:
            print(f"***VAD: error in manual chunk save: {e}")
            return None

    def _finalize_current_chunk(self, monotonic_time: float, end_sample_idx: int, force: bool = False) -> Optional[VoiceChunk]:
        """Finalize the current chunk and add it to the chunks list.
        
        Args:
            monotonic_time: Current monotonic time
            end_sample_idx: End sample index for the chunk
            force: If True, finalize even if chunk is below minimum duration (e.g., at call end)
        
        Returns the finalized chunk or None if no chunk was active or below minimum duration.
        """
        if self._current_chunk_start_time is None:
            return None
        
        if self._wav_sample_rate is None:
            # Can't create chunk without sample rate
            return None
        
        duration = monotonic_time - self._current_chunk_start_time
        end_sample = end_sample_idx if end_sample_idx is not None else self._current_chunk_end_sample
        start_sample = self._current_chunk_start_sample
        
        # Check minimum chunk duration (unless forced, e.g., at call end)
        if not force and duration < self.cfg.min_chunk_duration_sec:
            # Chunk is too short - don't finalize yet
            if not hasattr(self, '_last_short_chunk_time'):
                self._last_short_chunk_time = 0
            import time as time_module
            current_time = time_module.time()
            if current_time - self._last_short_chunk_time > 2.0:  # Log every 2 seconds to avoid spam
                print(f"***VAD: chunk too short ({duration:.2f}s < {self.cfg.min_chunk_duration_sec}s minimum), waiting for more speech")
                self._last_short_chunk_time = current_time
            return None
        
        # Save chunk audio to file first (before adding to list)
        # This ensures the file path is available when creating the chunk
        chunk_file_path = self._save_chunk_audio_internal(
            start_sample=start_sample,
            end_sample=end_sample,
            duration=duration
        )
        
        chunk = VoiceChunk(
            start_time_monotonic=self._current_chunk_start_time,
            end_time_monotonic=monotonic_time,
            start_sample_idx=start_sample,
            end_sample_idx=end_sample,
            duration_seconds=duration,
            sample_rate=self._wav_sample_rate,
            file_path=chunk_file_path
        )
        
        self._chunks.append(chunk)
        
        # Reset current chunk state
        self._current_chunk_start_time = None
        self._current_chunk_start_sample = None
        self._current_chunk_end_sample = None
        self._silence_start_time = None
        
        print(f"***VAD: chunk finalized - duration={duration:.2f}s, samples={start_sample}-{end_sample}")
        
        return chunk

    def _check_chunk_boundaries(self, monotonic_time: float, current_sample_idx: int, has_speech: bool) -> None:
        """Check if chunk boundaries should be created based on silence or max duration.
        
        Args:
            monotonic_time: Current monotonic time
            current_sample_idx: Current sample index in the WAV file
            has_speech: Whether speech was detected in the current frame
        """
        
        # Track silence periods
        if has_speech:
            # Speech detected - reset silence tracking
            self._silence_start_time = None
            if self._current_chunk_start_time is None:
                # Start a new chunk if we're not in one
                self._start_new_chunk(monotonic_time, current_sample_idx)
            else:
                # Update current chunk end sample
                self._current_chunk_end_sample = current_sample_idx
                self._last_speech_sample = current_sample_idx
        else:
            # No speech - track silence
            if self._silence_start_time is None and self._current_chunk_start_time is not None:
                # Silence just started
                self._silence_start_time = monotonic_time
            
            # Check if we should finalize chunk due to silence
            if (self._silence_start_time is not None and 
                self._current_chunk_start_time is not None):
                silence_duration = monotonic_time - self._silence_start_time
                if silence_duration >= self.cfg.min_silence_for_boundary_sec:
                    # Silence long enough - check if chunk meets minimum duration
                    chunk_duration = monotonic_time - self._current_chunk_start_time
                    if chunk_duration >= self.cfg.min_chunk_duration_sec:
                        # Chunk meets minimum duration - finalize it
                        # Use last speech sample as end point
                        end_sample = self._last_speech_sample if self._last_speech_sample is not None else self._current_chunk_end_sample
                        finalized = self._finalize_current_chunk(monotonic_time, end_sample)
                        if not finalized:
                            # Chunk was below minimum duration, wait for more speech
                            pass
        
        # Check 15-second maximum duration
        if (self._current_chunk_start_time is not None and 
            monotonic_time - self._current_chunk_start_time >= self.cfg.max_chunk_duration_sec):
            # Chunk exceeded max duration - finalize it (force=True to override minimum duration)
            end_sample = self._last_speech_sample if self._last_speech_sample is not None else self._current_chunk_end_sample
            finalized = self._finalize_current_chunk(monotonic_time, end_sample, force=True)
            if finalized:
                print(f"***VAD: chunk split due to max duration ({self.cfg.max_chunk_duration_sec}s)")
            # If there's still speech, start a new chunk immediately
            if has_speech:
                self._start_new_chunk(monotonic_time, current_sample_idx)

    def get_chunks(self) -> List[VoiceChunk]:
        """Get all completed voice chunks."""
        return self._chunks.copy()
    
    def get_speech_duration(self) -> float:
        """Calculate total speech duration from all completed chunks.
        
        Returns total duration in seconds of all voice chunks.
        """
        total_duration = sum(chunk.duration_seconds for chunk in self._chunks)
        # Include current chunk if active
        current_chunk = self.get_current_chunk()
        if current_chunk:
            total_duration += current_chunk.duration_seconds
        return round(total_duration, 2)
    
    def get_chunk_count(self) -> int:
        """Get the total number of voice chunks detected.
        
        Returns count of completed chunks plus 1 if there's an active chunk.
        """
        count = len(self._chunks)
        if self._current_chunk_start_time is not None:
            count += 1
        return count
    
    def get_vad_confidence(self) -> Optional[float]:
        """Calculate average VAD confidence from speech frame probabilities.
        
        Returns average probability across all speech frames, or None if no speech detected.
        """
        if not self._speech_probabilities:
            return None
        avg_confidence = sum(self._speech_probabilities) / len(self._speech_probabilities)
        return round(avg_confidence, 3)
    
    def set_bot_playback_state(self, is_playing: bool, monotonic_time_fn) -> None:
        """Set the bot's audio playback state.
        
        Args:
            is_playing: True if bot is currently playing audio, False otherwise
            monotonic_time_fn: Callable returning current monotonic time
        """
        current_time = float(monotonic_time_fn())
        
        # If state changed, finalize current silence period if applicable
        if self._bot_playback_active != is_playing:
            self._finalize_current_silence(current_time)
            self._bot_playback_active = is_playing
            # Start new silence period if both parties are now silent
            if not is_playing:
                self._start_silence_period(current_time)
    
    def _start_silence_period(self, monotonic_time: float) -> None:
        """Start tracking a silence period (neither party is speaking)."""
        if self._current_silence_start is None:
            self._current_silence_start = monotonic_time
    
    def _finalize_current_silence(self, monotonic_time: float) -> None:
        """Finalize the current silence period and add to total."""
        if self._current_silence_start is not None:
            silence_duration = monotonic_time - self._current_silence_start
            if silence_duration > 0:
                self._total_silence_duration += silence_duration
            self._current_silence_start = None
    
    def get_silence_duration(self, monotonic_time_fn) -> float:
        """Get total silence duration when neither caller nor bot are speaking.
        
        Args:
            monotonic_time_fn: Callable returning current monotonic time
            
        Returns:
            Total silence duration in seconds (rounded to 2 decimal places).
        """
        current_time = float(monotonic_time_fn())
        
        # Finalize current silence period if active (this adds to total)
        if self._current_silence_start is not None:
            self._finalize_current_silence(current_time)
            # If still in silence, restart tracking (for future calls)
            if not self._bot_playback_active:
                self._start_silence_period(current_time)
        
        return round(self._total_silence_duration, 2)
    
    def finalize_silence_tracking(self, monotonic_time_fn) -> None:
        """Finalize silence tracking at call end. Call this when call is complete.
        
        Args:
            monotonic_time_fn: Callable returning current monotonic time
        """
        current_time = float(monotonic_time_fn())
        self._finalize_current_silence(current_time)

    def get_current_chunk(self) -> Optional[VoiceChunk]:
        """Get information about the current active chunk, if any."""
        if self._current_chunk_start_time is None or self._wav_sample_rate is None:
            return None
        
        import time as time_module
        current_time = time_module.time()
        duration = current_time - self._current_chunk_start_time
        
        return VoiceChunk(
            start_time_monotonic=self._current_chunk_start_time,
            end_time_monotonic=current_time,
            start_sample_idx=self._current_chunk_start_sample or 0,
            end_sample_idx=self._current_chunk_end_sample or 0,
            duration_seconds=duration,
            sample_rate=self._wav_sample_rate,
            file_path=None  # Not saved yet - chunk is still active
        )

    def finalize_all_chunks(self, monotonic_time_fn) -> None:
        """Finalize any active chunk. Call this when processing is complete.
        
        This will finalize the chunk even if it's below the minimum duration
        (forced finalization at call end).
        """
        if self._current_chunk_start_time is not None:
            monotonic_time = float(monotonic_time_fn())
            end_sample = self._last_speech_sample if self._last_speech_sample is not None else self._current_chunk_end_sample
            if end_sample is None:
                end_sample = self._last_frame_idx
            # Force finalization at call end, even if below minimum duration
            self._finalize_current_chunk(monotonic_time, end_sample, force=True)

    def process_new_audio(self, monotonic_time_fn) -> None:
        """Process newly appended audio and update last speech time.

        monotonic_time_fn: callable returning a monotonic time base (e.g., time.time())
        """
        if not self.available or self._model is None:
            return

        chunk, input_sr = self._read_new_frames()
        if chunk is None or input_sr is None or chunk.size == 0:
            return

        # Debug: check if we're getting audio
        if not hasattr(self, '_last_audio_check_time'):
            self._last_audio_check_time = 0
        import time as time_module
        if time_module.time() - self._last_audio_check_time > 5.0:
            print(f"***VAD: read {len(chunk)} samples at {input_sr} Hz")
            self._last_audio_check_time = time_module.time()

        # Convert to torch and resample if needed
        if torch is None:
            return
        waveform = torch.from_numpy(chunk).unsqueeze(0)  # (1, N)
        
        # Determine the actual sample rate to use with the model
        # Silero VAD supports 8000 and 16000 Hz
        actual_sr = input_sr
        
        # Resample to target sample rate if needed
        if input_sr != self.cfg.target_sample_rate:
            if torchaudio is None:
                # Can't resample - use original sample rate if it's supported (8000 or 16000)
                if input_sr not in (8000, 16000):
                    # Skip this chunk if sample rate isn't supported
                    if not hasattr(self, '_last_unsupported_sr_time'):
                        self._last_unsupported_sr_time = 0
                    import time as time_module
                    if time_module.time() - self._last_unsupported_sr_time > 10.0:
                        print(f"***VAD: cannot resample from {input_sr}Hz (not 8kHz/16kHz and torchaudio unavailable)")
                        self._last_unsupported_sr_time = time_module.time()
                    return
                # Use original sample rate if it's supported
                actual_sr = input_sr
            else:
                resampler = self._ensure_resampler(input_sr)
                if resampler is None:
                    # Resampler creation failed - use original if supported
                    if input_sr in (8000, 16000):
                        actual_sr = input_sr
                    else:
                        return
                else:
                    with torch.no_grad():
                        waveform = resampler(waveform)
                    actual_sr = self.cfg.target_sample_rate

        # Frame-wise VAD - Silero VAD requires exactly 32ms windows:
        # - 256 samples for 8000 Hz (256/8000 = 32ms)
        # - 512 samples for 16000 Hz (512/16000 = 32ms)
        if actual_sr == 8000:
            window = 256
        elif actual_sr == 16000:
            window = 512
        else:
            # Unsupported sample rate
            if not hasattr(self, '_last_unsupported_sr_time'):
                self._last_unsupported_sr_time = 0
            import time as time_module
            if time_module.time() - self._last_unsupported_sr_time > 10.0:
                print(f"***VAD: unsupported sample rate {actual_sr}Hz (must be 8000 or 16000)")
                self._last_unsupported_sr_time = time_module.time()
            return
        
        # Debug: check waveform size
        if waveform.shape[1] < window:
            # Debug: report if waveform is too small
            if not hasattr(self, '_last_small_waveform_time'):
                self._last_small_waveform_time = 0
            import time as time_module
            if time_module.time() - self._last_small_waveform_time > 5.0:
                print(f"***VAD: waveform too small ({waveform.shape[1]} samples, need {window} for {actual_sr}Hz)")
                self._last_small_waveform_time = time_module.time()
            return
        
        # Debug: track processing stats
        frames_processed = 0
        max_prob = 0.0
        total_frames_available = (waveform.shape[1] - window + 1) // window
        
        # Calculate sample rate ratio to map resampled indices back to original WAV
        sample_rate_ratio = input_sr / actual_sr if actual_sr > 0 else 1.0
        
        # Calculate the starting sample index in the original WAV file for this chunk
        # After _read_new_frames(), _last_frame_idx points to the end of what we just read
        # The chunk we read has len(chunk) samples at the ORIGINAL input_sr
        # So it starts at _last_frame_idx - len(chunk) (in original samples)
        chunk_start_sample = self._last_frame_idx - len(chunk)
        
        # Validate chunk_start_sample is non-negative
        if chunk_start_sample < 0:
            # This shouldn't happen, but handle gracefully
            chunk_start_sample = max(0, self._last_frame_idx - len(chunk))
        
        monotonic_time_fn_ref = monotonic_time_fn
        
        with torch.no_grad():
            # Process in 32ms windows (non-overlapping for now)
            for window_idx, start in enumerate(range(0, waveform.shape[1] - window + 1, window)):
                frame = waveform[:, start : start + window]
                
                # Calculate sample index in original WAV file
                # Map from resampled waveform position to original WAV position
                resampled_sample_pos = start
                original_sample_pos = int(chunk_start_sample + (resampled_sample_pos * sample_rate_ratio))
                
                # Get current monotonic time for chunk boundary detection
                current_monotonic_time = float(monotonic_time_fn_ref())
                
                # Silero VAD requires: model(waveform_tensor, sample_rate_int)
                has_speech = False
                try:
                    # Use the actual sample rate of the waveform
                    sample_rate = int(actual_sr)
                    prob = self._model(frame, sample_rate).item()
                except Exception as e:
                    # Report error only occasionally to avoid spam
                    if not hasattr(self, '_last_model_error_time'):
                        self._last_model_error_time = 0
                    import time as time_module
                    if time_module.time() - self._last_model_error_time > 10.0:
                        print(f"***VAD: model call error: {e}")
                        self._last_model_error_time = time_module.time()
                    # Continue processing other frames even if one fails
                    # For chunk detection, treat error frames as non-speech
                    prob = 0.0
                
                frames_processed += 1
                max_prob = max(max_prob, prob)
                
                # Track speech probabilities for confidence calculation
                if prob >= self.cfg.threshold:
                    self._speech_probabilities.append(prob)
                
                # Check if this frame contains speech
                has_speech = prob >= self.cfg.threshold
                
                # Update chunk boundaries based on speech detection
                self._check_chunk_boundaries(
                    monotonic_time=current_monotonic_time,
                    current_sample_idx=original_sample_pos,
                    has_speech=has_speech
                )
                
                # Track silence periods (when neither caller nor bot are speaking)
                if has_speech:
                    # Speech detected - end any current silence period
                    self._finalize_current_silence(current_monotonic_time)
                    prev_time = self.last_speech_time_monotonic
                    self.last_speech_time_monotonic = current_monotonic_time
                    # Print when speech is first detected or after a gap (avoid spam on continuous speech)
                    if prev_time is None or (self.last_speech_time_monotonic - prev_time) > 0.5:
                        print(f"***VAD: speech detected (prob={prob:.3f}, time={self.last_speech_time_monotonic:.3f}, sample={original_sample_pos})")
                else:
                    # No speech detected - start silence period if bot is also not playing
                    if not self._bot_playback_active:
                        if self._current_silence_start is None:
                            self._start_silence_period(current_monotonic_time)
                    else:
                        # Bot is playing, so this is not a silence period (bot is speaking)
                        self._finalize_current_silence(current_monotonic_time)
        
        # Debug output: print max probability occasionally to diagnose issues
        if frames_processed > 0:
            # Only print debug every few seconds to avoid spam
            import time as time_module
            if not hasattr(self, '_last_debug_time') or time_module.time() - getattr(self, '_last_debug_time', 0) > 5.0:
                print(f"***VAD: processed {frames_processed}/{total_frames_available} frames, max_prob={max_prob:.3f} (threshold={self.cfg.threshold:.3f})")
                self._last_debug_time = time_module.time()
        elif total_frames_available > 0:
            # No frames processed but frames available - something went wrong
            import time as time_module
            if not hasattr(self, '_last_no_proc_time'):
                self._last_no_proc_time = 0
            if time_module.time() - self._last_no_proc_time > 5.0:
                print(f"***VAD: {total_frames_available} frames available but none processed (check model errors)")
                self._last_no_proc_time = time_module.time()
