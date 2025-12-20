"""ASR (Automatic Speech Recognition) service integration with omnilingual-asr.

This module exists primarily for compatibility with tests and callers that expect
`pjsua_bot.asr_omnilingual`.

Key goals:
- Avoid importing heavy/native dependencies at test collection time.
- Be robust in CI where system libs like `libsndfile` may be missing.
"""

from __future__ import annotations

import logging
import os
import time
import wave
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional dependency import (can fail with ImportError *or* OSError if native libs
# like libsndfile are missing).
_omnilingual_error: str | None = None
ASRInferencePipeline: Any = None

try:
    from omnilingual_asr.models.inference.pipeline import (
        ASRInferencePipeline as _ASRInferencePipeline,
    )

    ASRInferencePipeline = _ASRInferencePipeline
    _omnilingual_error = None
except Exception as exc:  # noqa: BLE001 - we intentionally catch native loader errors
    _omnilingual_error = str(exc)

_OMNILINGUAL_AVAILABLE = ASRInferencePipeline is not None


@dataclass
class ASRConfig:
    """Configuration for ASR service."""

    # omnilingual-asr model cards: "omniASR_CTC_1B", "omniASR_CTC_350M", ...
    model_name: str = "omniASR_CTC_1B"
    device: str = "auto"  # "auto", "cpu", or "cuda"

    # Language code in omnilingual format (e.g., "fas_Arab" for Farsi)
    language: Optional[str] = "fas_Arab"

    # Translation target language (unused for now; kept for interface stability)
    target_language: Optional[str] = None

    batch_size: int = 1

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0

    # Error handling
    skip_on_error: bool = True
    log_errors: bool = True


@dataclass
class TranscriptionResult:
    """Result of ASR transcription."""

    text: str
    language: Optional[str] = None
    language_probability: Optional[float] = None
    duration: float = 0.0
    processing_time: float = 0.0
    chunks: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class ASRService:
    """ASR service wrapper for omnilingual-asr.

    This implementation is **lazy**: it does not load the model on construction.
    That keeps unit tests fast and avoids CI failures when native dependencies
    aren't installed.
    """

    def __init__(self, config: Optional[ASRConfig] = None):
        self.cfg = config or ASRConfig()
        self._pipeline: Optional[Any] = None
        self._device: Optional[str] = None

        self.available = bool(_OMNILINGUAL_AVAILABLE)
        self._load_error: Optional[str] = None

        if not self.available:
            err = _omnilingual_error or "import failed"
            self._load_error = f"omnilingual-asr not available: {err}"

    def _resolve_device(self) -> str:
        if self.cfg.device != "auto":
            return self.cfg.device

        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _ensure_pipeline_loaded(self) -> bool:
        """Ensure pipeline is loaded; returns True if usable."""
        if not self.available:
            return False

        if self._pipeline is not None:
            return True

        if not _OMNILINGUAL_AVAILABLE:
            self.available = False
            err = _omnilingual_error or "import failed"
            self._load_error = f"omnilingual-asr not available: {err}"
            return False

        try:
            self._device = self._resolve_device()
            # NOTE: omnilingual-asr selects device internally.
            # We keep device locally for metadata/logging only.
            self._pipeline = ASRInferencePipeline(model_card=self.cfg.model_name)
            return True
        except Exception as exc:  # noqa: BLE001 - surface a stable error
            self._pipeline = None
            self.available = False
            self._load_error = f"model loading failed: {exc}"
            if self.cfg.log_errors:
                logger.error("ASR: failed to load omnilingual-asr pipeline: %s", exc)
            return False

    def _get_audio_duration(self, audio_path: str) -> Optional[float]:
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
        if not self.available:
            if self.cfg.log_errors:
                logger.error("ASR: service not available - %s", self._load_error)
            return None

        if not os.path.exists(audio_path):
            if self.cfg.log_errors:
                logger.error("ASR: audio file not found: %s", audio_path)
            return None

        if not self._ensure_pipeline_loaded():
            return None

        start_time = time.time()

        try:
            duration = self._get_audio_duration(audio_path)
            lang = [self.cfg.language] if self.cfg.language else None

            if self._pipeline is None:
                raise RuntimeError("ASR pipeline not initialized")

            transcriptions = self._pipeline.transcribe(
                [audio_path], lang=lang, batch_size=self.cfg.batch_size
            )

            processing_time = time.time() - start_time
            text = transcriptions[0] if transcriptions else ""

            return TranscriptionResult(
                text=text,
                language=self.cfg.language,
                language_probability=None,
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
        except Exception as exc:  # noqa: BLE001 - retry behavior is part of API
            error_msg = str(exc)

            if retry_count < self.cfg.max_retries:
                retry_delay = self.cfg.retry_delay * (
                    self.cfg.retry_backoff**retry_count
                )
                if self.cfg.log_errors:
                    logger.error(
                        "ASR: error transcribing %s: %s", audio_path, error_msg
                    )
                    logger.info(
                        "ASR: retrying in %.2fs (attempt %d/%d)...",
                        retry_delay,
                        retry_count + 1,
                        self.cfg.max_retries,
                    )
                time.sleep(retry_delay)
                return self.transcribe(audio_path, retry_count=retry_count + 1)

            if self.cfg.log_errors:
                logger.error(
                    "ASR: failed to transcribe %s after %d attempts: %s",
                    audio_path,
                    self.cfg.max_retries,
                    error_msg,
                )

            if self.cfg.skip_on_error:
                return None
            raise Exception(f"ASR transcription failed: {error_msg}") from exc


# Backward compatibility aliases (some callers may use these names)
OmnilingualASRService = ASRService
OmnilingualASRConfig = ASRConfig
