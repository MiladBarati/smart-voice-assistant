"""ASR (Automatic Speech Recognition) service integration.

This module provides a wrapper around transformers-based Whisper ASR models
for transcribing audio recordings. It includes error handling and retry logic
for robust transcription processing.
"""

from __future__ import annotations

import os
import time
import wave
import warnings
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import numpy as np

# Set environment variables to suppress Hugging Face warnings before imports
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

# Suppress transformers warnings globally
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*generation_config.*")
warnings.filterwarnings("ignore", message=".*attention mask.*")
warnings.filterwarnings("ignore", message=".*logits processor.*")
warnings.filterwarnings("ignore", message=".*pad token.*")
warnings.filterwarnings("ignore", message=".*eos token.*")
warnings.filterwarnings("ignore", message=".*SuppressTokens.*")

# Suppress transformers logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("transformers.generation").setLevel(logging.ERROR)

try:
    from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
    import torch
    import torchaudio
    _TRANSFORMERS_AVAILABLE = True
    _TRANSFORMERS_ERROR = None
except ImportError as e:
    AutoProcessor = None  # type: ignore
    AutoModelForSpeechSeq2Seq = None  # type: ignore
    torch = None  # type: ignore
    torchaudio = None  # type: ignore
    _TRANSFORMERS_AVAILABLE = False
    _TRANSFORMERS_ERROR = str(e)
except Exception as e:
    AutoProcessor = None  # type: ignore
    AutoModelForSpeechSeq2Seq = None  # type: ignore
    torch = None  # type: ignore
    torchaudio = None  # type: ignore
    _TRANSFORMERS_AVAILABLE = False
    _TRANSFORMERS_ERROR = str(e)


@dataclass
class ASRConfig:
    """Configuration for ASR service."""
    model_name: str = "vhdm/whisper-large-fa-v1"  # Persian/Farsi Whisper model
    device: str = "auto"  # "auto", "cpu", or "cuda"
    language: Optional[str] = "fa"  # Language code (fa = Persian/Farsi)
    task: str = "transcribe"  # "transcribe" or "translate"
    return_timestamps: bool = False  # Whether to return word-level timestamps
    chunk_length_s: int = 30  # Maximum chunk length in seconds for long audio
    batch_size: int = 16  # Batch size for processing
    
    # Retry configuration
    max_retries: int = 3  # Maximum number of retry attempts
    retry_delay: float = 1.0  # Delay between retries in seconds
    retry_backoff: float = 2.0  # Exponential backoff multiplier
    
    # Error handling
    skip_on_error: bool = True  # If True, return None on persistent errors instead of raising
    log_errors: bool = True  # Whether to log errors to console


@dataclass
class TranscriptionResult:
    """Result of ASR transcription."""
    text: str
    language: Optional[str] = None
    language_probability: Optional[float] = None
    duration: float = 0.0  # Duration of transcribed audio in seconds
    processing_time: float = 0.0  # Time taken to process in seconds
    chunks: Optional[List[Dict[str, Any]]] = None  # Chunk-level results if available
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata


class ASRService:
    """ASR service wrapper for Whisper-based speech recognition.
    
    This service provides automatic speech recognition using Hugging Face
    transformers with Whisper models. It includes error handling, retry
    logic, and support for Persian/Farsi transcription.
    
    Usage:
        asr = ASRService()
        if asr.available:
            result = asr.transcribe("path/to/audio.wav")
            if result:
                print(f"Transcribed text: {result.text}")
    """
    
    def __init__(self, config: Optional[ASRConfig] = None):
        """Initialize ASR service.
        
        Args:
            config: ASR configuration. If None, uses default config.
        """
        self.cfg = config or ASRConfig()
        self._processor = None
        self._model = None
        self._device = None
        self.available = False
        self._load_error: Optional[str] = None
        
        self._load_model_if_possible()
    
    def _load_model_if_possible(self) -> None:
        """Load the ASR model if transformers are available."""
        if not _TRANSFORMERS_AVAILABLE:
            self._load_error = f"transformers not available: {_TRANSFORMERS_ERROR or 'import failed'}"
            return
        
        if torch is None:
            self._load_error = "torch not available"
            return
        
        try:
            # Determine device
            if self.cfg.device == "auto":
                if torch.cuda.is_available():
                    self._device = "cuda"
                    print(f"***ASR: Using CUDA device: {torch.cuda.get_device_name(0)}")
                else:
                    self._device = "cpu"
                    print(f"***ASR: Using CPU device")
            else:
                self._device = self.cfg.device
                print(f"***ASR: Using specified device: {self._device}")
            
            # Load processor and model (suppress warnings during loading)
            print(f"***ASR: Loading model {self.cfg.model_name}...")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._processor = AutoProcessor.from_pretrained(self.cfg.model_name)
                self._model = AutoModelForSpeechSeq2Seq.from_pretrained(self.cfg.model_name)
            
            # Move model to device
            self._model = self._model.to(self._device)
            self._model.eval()
            
            # Log model info
            param_count = sum(p.numel() for p in self._model.parameters())
            print(f"***ASR: Model loaded successfully on {self._device}")
            print(f"***ASR: Model parameters: {param_count:,}")
            
            self.available = True
            self._load_error = None
            
        except Exception as e:
            self._processor = None
            self._model = None
            self.available = False
            self._load_error = f"model loading failed: {str(e)}"
            print(f"***ASR: Error loading model: {e}")
    
    def _load_audio(self, audio_path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Load audio file and return as numpy array.
        
        Args:
            audio_path: Path to audio file (WAV format expected)
            
        Returns:
            Tuple of (audio_array, sample_rate) or (None, None) on error
        """
        if not os.path.exists(audio_path):
            if self.cfg.log_errors:
                print(f"***ASR: Audio file not found: {audio_path}")
            return None, None
        
        # Try using torchaudio first (better format support)
        if torchaudio is not None:
            try:
                waveform, sample_rate = torchaudio.load(audio_path)
                # Convert to mono if needed
                if waveform.shape[0] > 1:
                    waveform = torch.mean(waveform, dim=0, keepdim=True)
                # Convert to numpy array
                audio_array = waveform.squeeze().numpy()
                return audio_array, sample_rate
            except Exception as e:
                # torchaudio failed (e.g., TorchCodec not available), fall back to wave module
                if self.cfg.log_errors:
                    error_msg = str(e)
                    # Only log if it's not the common TorchCodec error (to reduce spam)
                    if "TorchCodec" not in error_msg:
                        print(f"***ASR: torchaudio failed for {audio_path}, falling back to wave module: {e}")
                # Fall through to wave module fallback
        
        # Fallback to wave module (more reliable for WAV files)
        try:
            with wave.open(audio_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_audio = wf.readframes(n_frames)
                
                # Convert to numpy array
                if wf.getsampwidth() == 1:
                    dtype = np.int8
                elif wf.getsampwidth() == 2:
                    dtype = np.int16
                elif wf.getsampwidth() == 4:
                    dtype = np.int32
                else:
                    if self.cfg.log_errors:
                        print(f"***ASR: Unsupported sample width: {wf.getsampwidth()}")
                    return None, None
                
                audio_array = np.frombuffer(raw_audio, dtype=dtype)
                
                # Convert to mono if needed
                if n_channels > 1:
                    audio_array = audio_array.reshape(-1, n_channels).mean(axis=1)
                
                # Normalize to float32 [-1, 1]
                max_val = float(np.iinfo(dtype).max)
                audio_array = (audio_array.astype(np.float32) / max_val).clip(-1.0, 1.0)
                
                return audio_array, sample_rate
                
        except Exception as e:
            if self.cfg.log_errors:
                print(f"***ASR: Error loading audio file {audio_path}: {e}")
            return None, None
    
    def _transcribe_audio(self, audio_array: np.ndarray, sample_rate: int) -> Optional[Dict[str, Any]]:
        """Transcribe audio array using the loaded model.
        
        Args:
            audio_array: Audio samples as numpy array (float32, mono, normalized to [-1, 1])
            sample_rate: Sample rate of the audio
            
        Returns:
            Dictionary with transcription results or None on error
        """
        if not self.available or self._model is None or self._processor is None:
            return None
        
        try:
            # Prepare inputs using processor
            inputs = self._processor(
                audio_array,
                sampling_rate=sample_rate,
                return_tensors="pt"
            )
            
            # Move inputs to device
            if self._device:
                inputs = {k: v.to(self._device) if isinstance(v, torch.Tensor) else v 
                         for k, v in inputs.items()}
            
            # Generate transcription (suppress all warnings during generation)
            with torch.no_grad(), warnings.catch_warnings():
                warnings.simplefilter("ignore")
                generated_ids = self._model.generate(
                    inputs["input_features"],
                    language=self.cfg.language,
                    task=self.cfg.task,
                    return_timestamps=self.cfg.return_timestamps,
                )
            
            # Decode transcription
            transcription = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            # Get language detection info if available
            language_info = None
            if hasattr(self._model, 'generate') and generated_ids is not None:
                # Extract language info from model output if available
                try:
                    # Some Whisper models provide language information
                    # This is a simplified extraction - actual implementation depends on model version
                    pass
                except Exception:
                    pass
            
            return {
                "text": transcription,
                "language": self.cfg.language,
                "language_probability": None,  # Model-dependent
            }
            
        except Exception as e:
            if self.cfg.log_errors:
                print(f"***ASR: Error during transcription: {e}")
            return None
    
    def transcribe(
        self, 
        audio_path: str,
        retry_count: int = 0
    ) -> Optional[TranscriptionResult]:
        """Transcribe audio file with error handling and retry logic.
        
        Args:
            audio_path: Path to audio file to transcribe
            retry_count: Internal retry counter (used recursively)
            
        Returns:
            TranscriptionResult if successful, None on error (if skip_on_error=True)
        """
        if not self.available:
            if self.cfg.log_errors:
                print(f"***ASR: Service not available - {self._load_error}")
            return None
        
        start_time = time.time()
        
        try:
            # Load audio
            audio_array, sample_rate = self._load_audio(audio_path)
            if audio_array is None or sample_rate is None:
                raise ValueError(f"Failed to load audio from {audio_path}")
            
            # Calculate audio duration
            duration = len(audio_array) / sample_rate
            
            # Transcribe
            result_dict = self._transcribe_audio(audio_array, sample_rate)
            if result_dict is None:
                raise ValueError("Transcription returned None")
            
            processing_time = time.time() - start_time
            
            # Create result object
            result = TranscriptionResult(
                text=result_dict.get("text", ""),
                language=result_dict.get("language"),
                language_probability=result_dict.get("language_probability"),
                duration=duration,
                processing_time=processing_time,
                metadata={
                    "audio_path": audio_path,
                    "sample_rate": sample_rate,
                    "model": self.cfg.model_name,
                    "device": self._device,
                }
            )
            
            if self.cfg.log_errors:
                print(f"***ASR: Transcribed {audio_path} ({duration:.2f}s) in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            # Retry logic
            if retry_count < self.cfg.max_retries:
                retry_delay = self.cfg.retry_delay * (self.cfg.retry_backoff ** retry_count)
                if self.cfg.log_errors:
                    print(f"***ASR: Error transcribing {audio_path}: {error_msg}")
                    print(f"***ASR: Retrying in {retry_delay:.2f}s (attempt {retry_count + 1}/{self.cfg.max_retries})...")
                
                time.sleep(retry_delay)
                return self.transcribe(audio_path, retry_count=retry_count + 1)
            
            # All retries exhausted
            if self.cfg.log_errors:
                print(f"***ASR: Failed to transcribe {audio_path} after {self.cfg.max_retries} attempts: {error_msg}")
            
            if self.cfg.skip_on_error:
                return None
            else:
                raise Exception(f"ASR transcription failed: {error_msg}") from e
    
    def transcribe_chunks(
        self,
        audio_chunks: List[str],
        max_workers: int = 1
    ) -> List[Optional[TranscriptionResult]]:
        """Transcribe multiple audio chunks.
        
        Args:
            audio_chunks: List of paths to audio files
            max_workers: Maximum number of parallel workers (currently sequential)
            
        Returns:
            List of TranscriptionResult objects (None for failed transcriptions)
        """
        results = []
        for chunk_path in audio_chunks:
            result = self.transcribe(chunk_path)
            results.append(result)
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        info = {
            "available": self.available,
            "model_name": self.cfg.model_name,
            "device": self._device,
            "load_error": self._load_error,
        }
        
        if self._model is not None:
            try:
                param_count = sum(p.numel() for p in self._model.parameters())
                info["parameter_count"] = param_count
            except Exception:
                pass
        
        return info

