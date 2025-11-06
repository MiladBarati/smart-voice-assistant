from __future__ import annotations

from typing import Callable, Optional


class SilenceTracker:
    """Track periods when neither party is speaking and bot playback state."""

    def __init__(self) -> None:
        self._bot_playback_active: bool = False
        self._current_silence_start: Optional[float] = None
        self._total_silence_duration: float = 0.0

    def set_bot_playback_state(self, is_playing: bool, monotonic_time_fn: Callable[[], float]) -> None:
        current_time = float(monotonic_time_fn())
        if self._bot_playback_active != is_playing:
            self._finalize_current_silence(current_time)
            self._bot_playback_active = is_playing
            if not is_playing:
                self._start_silence_period(current_time)

    def _start_silence_period(self, monotonic_time: float) -> None:
        if self._current_silence_start is None:
            self._current_silence_start = monotonic_time

    def _finalize_current_silence(self, monotonic_time: float) -> None:
        if self._current_silence_start is not None:
            silence_duration = monotonic_time - self._current_silence_start
            if silence_duration > 0:
                self._total_silence_duration += silence_duration
            self._current_silence_start = None

    def note_non_silence(self, monotonic_time: float) -> None:
        self._finalize_current_silence(monotonic_time)

    def note_possible_silence(self, monotonic_time: float) -> None:
        if not self._bot_playback_active and self._current_silence_start is None:
            self._start_silence_period(monotonic_time)
        elif self._bot_playback_active:
            self._finalize_current_silence(monotonic_time)

    def get_silence_duration(self, monotonic_time_fn: Callable[[], float]) -> float:
        current_time = float(monotonic_time_fn())
        if self._current_silence_start is not None:
            self._finalize_current_silence(current_time)
            if not self._bot_playback_active:
                self._start_silence_period(current_time)
        return round(self._total_silence_duration, 2)

    def finalize(self, monotonic_time_fn: Callable[[], float]) -> None:
        current_time = float(monotonic_time_fn())
        self._finalize_current_silence(current_time)


