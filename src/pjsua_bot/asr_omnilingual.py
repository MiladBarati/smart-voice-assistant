"""ASR (Automatic Speech Recognition) service integration with omnilingual-asr.

This module provides a wrapper around omnilingual-asr for transcribing audio recordings.
It maintains compatibility with the original Whisper-based ASR interface while providing
improved multilingual support and translation capabilities.
"""

from __future__ import annotations

import os
import time
import warnings
import wave
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Import omnilingual-asr components
_omnilingual_error: str | None = None
ASRInferencePipeline: Any = None

try:
    from omnilingual_asr.models.inference.pipeline import (
        ASRInferencePipeline as _ASRInferencePipeline,
    )

    ASRInferencePipeline = _ASRInferencePipeline
    _omnilingual_error = None
except Exception as exc:
    _omnilingual_error = str(exc)

_OMNILINGUAL_AVAILABLE = ASRInferencePipeline is not None


@dataclass
class ASRConfig:
    """Configuration for ASR service."""

    # omnilingual-asr models: "omniASR_CTC_1B", "omniASR_CTC_350M"
    model_name: str = "omniASR_CTC_1B"
    device: str = "auto"  # "auto", "cpu", or "cuda"

    # Language code in omnilingual format (e.g., "fas_Arab" for Farsi)
    language: Optional[str] = "fas_Arab"  # Farsi/Persian

    # For translation (set target_language to translate)
    target_language: Optional[str] = None  # e.g., "eng_Latn" for English

    batch_size: int = 1  # Batch size for processing

    # Retry configuration
    max_retries: int = 3  # Maximum number of retry attempts
    retry_delay: float = 1.0  # Delay between retries in seconds
    retry_backoff: float = 2.0  # Exponential backoff multiplier

    # Error handling
    skip_on_error: bool = True  # If True, return None on error instead of raising
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
    """ASR service wrapper for omnilingual-asr.

    This service provides automatic speech recognition using omnilingual-asr,
    which supports 100+ languages and built-in translation capabilities.

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
        self._pipeline: Optional[Any] = None
        self._device: Optional[str] = None
        self.available = False
        self._load_error: Optional[str] = None

        self._load_model_if_possible()

    def _load_model_if_possible(self) -> None:
        """Load the ASR model if omnilingual-asr is available."""
        if not _OMNILINGUAL_AVAILABLE:
            error_msg = _omnilingual_error or "import failed"
            self._load_error = f"omnilingual-asr not available: {error_msg}"
            return

        try:
            # Determine device
            if self.cfg.device == "auto":
                try:
                    import torch

                    if torch.cuda.is_available():
                        self._device = "cuda"
                        device_name = torch.cuda.get_device_name(0)
                        print(f"***ASR: Using CUDA device: {device_name}")
                    else:
                        self._device = "cpu"
                        print("***ASR: Using CPU device")
                except Exception:
                    self._device = "cpu"
                    print("***ASR: Using CPU device (torch not available)")
            else:
                self._device = self.cfg.device
                print(f"***ASR: Using specified device: {self._device}")

            # Load omnilingual-asr pipeline
            print(f"***ASR: Loading model {self.cfg.model_name}...")
            print("***ASR: This may download ~1-2GB on first run...")

            self._pipeline = ASRInferencePipeline(model_card=self.cfg.model_name)

            print(f"***ASR: Model loaded successfully on {self._device}")

            self.available = True
            self._load_error = None

        except Exception as e:
            self._pipeline = None
            self.available = False
            self._load_error = f"model loading failed: {str(e)}"
            print(f"***ASR: Error loading model: {e}")

    def _get_audio_duration(self, audio_path: str) -> Optional[float]:
        """Get duration of audio file in seconds.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds or None on error
        """
        try:
            with wave.open(audio_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)
        except Exception:
            return None

    def transcribe(
        self, audio_path: str, retry_count: int = 0
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

        if not os.path.exists(audio_path):
            if self.cfg.log_errors:
                print(f"***ASR: Audio file not found: {audio_path}")
            return None

        start_time = time.time()

        try:
            # Get audio duration
            duration = self._get_audio_duration(audio_path)

            # Prepare language parameter
            lang = [self.cfg.language] if self.cfg.language else None

            # Transcribe using omnilingual-asr
            if self._pipeline is None:
                raise RuntimeError("ASR pipeline not initialized")
            transcriptions = self._pipeline.transcribe(
                [audio_path], lang=lang, batch_size=self.cfg.batch_size
            )

            processing_time = time.time() - start_time

            # Extract transcription text
            text = transcriptions[0] if transcriptions else ""

            # Create result object
            result = TranscriptionResult(
                text=text,
                language=self.cfg.language,
                language_probability=None,  # omnilingual-asr doesn't provide this
                duration=duration if duration else 0.0,
                processing_time=processing_time,
                metadata={
                    "audio_path": audio_path,
                    "model": self.cfg.model_name,
                    "device": self._device,
                    "source_language": self.cfg.language,
                    "target_language": self.cfg.target_language,
                },
            )

            if self.cfg.log_errors:
                duration_str = f"({duration:.2f}s) " if duration else ""
                print(
                    f"***ASR: Transcribed {audio_path} "
                    f"{duration_str}in {processing_time:.2f}s"
                )
                if duration and processing_time > 0:
                    rtf = processing_time / duration
                    print(f"***ASR: Real-Time Factor: {rtf:.2f}x")

            return result

        except Exception as e:
            error_msg = str(e)

            # Retry logic
            if retry_count < self.cfg.max_retries:
                retry_delay = self.cfg.retry_delay * (
                    self.cfg.retry_backoff**retry_count
                )
                if self.cfg.log_errors:
                    print(f"***ASR: Error transcribing {audio_path}: {error_msg}")
                    print(
                        f"***ASR: Retrying in {retry_delay:.2f}s "
                        f"(attempt {retry_count + 1}/{self.cfg.max_retries})..."
                    )

                time.sleep(retry_delay)
                return self.transcribe(audio_path, retry_count=retry_count + 1)

            # All retries exhausted
            if self.cfg.log_errors:
                print(
                    f"***ASR: Failed to transcribe {audio_path} after "
                    f"{self.cfg.max_retries} attempts: {error_msg}"
                )

            if self.cfg.skip_on_error:
                return None
            else:
                raise Exception(f"ASR transcription failed: {error_msg}") from e

    def transcribe_chunks(
        self, audio_chunks: List[str], max_workers: int = 1
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

    def transcribe_batch(
        self, audio_files: List[str], languages: Optional[List[str]] = None
    ) -> List[Optional[TranscriptionResult]]:
        """Transcribe multiple audio files in a batch (more efficient).

        Args:
            audio_files: List of paths to audio files
            languages: Optional list of language codes (one per file)

        Returns:
            List of TranscriptionResult objects (None for failed transcriptions)
        """
        if not self.available:
            if self.cfg.log_errors:
                print(f"***ASR: Service not available - {self._load_error}")
            return [None] * len(audio_files)

        # Use provided languages or default config language
        if languages is None:
            default_lang = self.cfg.language or ""
            languages = [default_lang] * len(audio_files)

        try:
            start_time = time.time()

            # Batch transcribe
            if self._pipeline is None:
                raise RuntimeError("ASR pipeline not initialized")
            transcriptions = self._pipeline.transcribe(
                audio_files, lang=languages, batch_size=self.cfg.batch_size
            )

            processing_time = time.time() - start_time

            # Create result objects
            results: List[Optional[TranscriptionResult]] = []
            for i, (audio_path, text) in enumerate(
                zip(audio_files, transcriptions, strict=False)
            ):
                duration = self._get_audio_duration(audio_path)

                result = TranscriptionResult(
                    text=text,
                    language=languages[i] if i < len(languages) else None,
                    language_probability=None,
                    duration=duration if duration else 0.0,
                    processing_time=processing_time / len(audio_files),  # Approximate
                    metadata={
                        "audio_path": audio_path,
                        "model": self.cfg.model_name,
                        "device": self._device,
                        "batch_processing": True,
                    },
                )
                results.append(result)

            if self.cfg.log_errors:
                print(
                    f"***ASR: Batch transcribed {len(audio_files)} files "
                    f"in {processing_time:.2f}s "
                    f"({processing_time / len(audio_files):.2f}s avg per file)"
                )

            return results

        except Exception as e:
            if self.cfg.log_errors:
                print(f"***ASR: Batch transcription failed: {e}")

            if self.cfg.skip_on_error:
                return [None] * len(audio_files)
            else:
                raise

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
            "backend": "omnilingual-asr",
        }

        return info


# Backward compatibility aliases
OmnilingualASRService = ASRService
OmnilingualASRConfig = ASRConfig
