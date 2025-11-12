"""ASR thread/queue support extracted from `AnyCall`."""

from __future__ import annotations

import os
import queue
import threading
from typing import Any

from ...asr import ASRService


class ASRSupportMixin:
    """Encapsulates ASR worker thread lifecycle and queue management."""

    _acc_ref: Any
    _asr_enabled: bool
    _asr_available: bool
    _asr: ASRService | None
    _asr_queue: queue.Queue[dict[str, Any]] | None
    _asr_thread: threading.Thread | None
    _asr_thread_stop: threading.Event
    _asr_chunk_texts: list[str]
    _asr_lock: threading.Lock
    _last_transcribed_chunk_count: int

    def _init_asr_support(self) -> None:
        """Initialise ASR-related state from the owning account."""
        self._asr_enabled = bool(getattr(self._acc_ref, "enable_asr", False))
        self._asr: ASRService | None = getattr(self._acc_ref, "_asr_service", None)
        self._asr_available = bool(
            getattr(self._acc_ref, "_asr_available", False)
            and self._asr is not None
            and self._asr.available
        )
        self._asr_chunk_texts = []
        self._last_transcribed_chunk_count = 0
        self._asr_queue = None
        self._asr_thread = None
        self._asr_thread_stop = threading.Event()
        self._asr_lock = threading.Lock()

    # ---------------------------------------------------------------------#
    # Worker thread lifecycle
    # ---------------------------------------------------------------------#
    def _asr_worker_thread(self) -> None:
        """Worker thread that processes ASR transcription tasks."""
        while not self._asr_thread_stop.is_set():
            try:
                # Wait for a task with a timeout to allow checking stop event
                task = self._asr_queue.get(timeout=1.0) if self._asr_queue else None
                if task is None:
                    continue

                file_path = task.get("file_path")
                chunk_idx = task.get("chunk_idx", -1)

                if not file_path or not os.path.exists(file_path):
                    continue

                if not self._asr or not self._asr_available:
                    continue

                # Perform transcription (this is the blocking operation)
                try:
                    print(
                        f"***ASR: starting transcription for chunk {chunk_idx + 1}..."
                    )
                    res = self._asr.transcribe(file_path)
                    if res and getattr(res, "text", None):
                        text = res.text.strip()
                        if text:
                            # Thread-safe append to _asr_chunk_texts
                            with self._asr_lock:
                                self._asr_chunk_texts.append(text)
                            print(f"***ASR: chunk {chunk_idx + 1} -> {text}")
                        else:
                            print(
                                (
                                    f"***ASR: chunk {chunk_idx + 1} transcribed "
                                    "but text is empty"
                                )
                            )
                    else:
                        print(
                            (
                                f"***ASR: chunk {chunk_idx + 1} transcription "
                                "returned no result"
                            )
                        )
                except Exception as exc:  # pragma: no cover - defensive
                    print(f"***ASR: transcription error for {file_path}: {exc}")

                # Mark task as done
                if self._asr_queue is not None:
                    self._asr_queue.task_done()

            except queue.Empty:
                # Timeout - continue loop to check stop event
                continue
            except Exception as exc:  # pragma: no cover - defensive
                print(f"***ASR: worker thread error: {exc}")

    def _start_asr_thread(self) -> None:
        """Start the ASR worker thread if ASR is enabled and available."""
        if not self._asr_enabled or not self._asr_available:
            return

        if self._asr_thread is not None and self._asr_thread.is_alive():
            return  # Thread already running

        if self._asr_queue is None:
            self._asr_queue = queue.Queue()

        self._asr_thread_stop.clear()
        self._asr_thread = threading.Thread(
            target=self._asr_worker_thread, daemon=True, name="ASRWorker"
        )
        self._asr_thread.start()
        print("***ASR: worker thread started")

    def _stop_asr_thread(self) -> None:
        """Stop the ASR worker thread and wait for pending tasks."""
        if self._asr_thread is None or not self._asr_thread.is_alive():
            return

        # Signal thread to stop
        self._asr_thread_stop.set()

        # Wait for thread to finish (with timeout)
        if self._asr_thread.is_alive():
            self._asr_thread.join(timeout=5.0)
            if self._asr_thread.is_alive():
                print("***ASR: worker thread did not stop within timeout")
            else:
                print("***ASR: worker thread stopped")

        self._asr_thread = None

    def _submit_transcription_task(self, file_path: str, chunk_idx: int = -1) -> None:
        """Submit a transcription task to the ASR worker thread queue.

        Args:
            file_path: Path to audio file to transcribe.
            chunk_idx: Index of the chunk (for logging purposes).
        """
        if not self._asr_enabled or not self._asr_available:
            return

        if self._asr_queue is None:
            # Start thread if not already started
            self._start_asr_thread()

        if self._asr_queue is not None:
            try:
                self._asr_queue.put_nowait(
                    {"file_path": file_path, "chunk_idx": chunk_idx}
                )
                print(
                    (
                        f"***ASR: queued transcription task for chunk {chunk_idx + 1}: "
                        f"{file_path}"
                    )
                )
            except queue.Full:
                print(f"***ASR: queue full, skipping transcription for {file_path}")
