"""Intent classification and response handling mixin."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any, Callable, Tuple

if TYPE_CHECKING:
    pass


class IntentHandlerMixin:
    """Mixin providing intent classification and response playback."""

    # Attributes supplied by sibling mixins / host class
    _acc_ref: Any
    _asr_enabled: bool
    _asr_available: bool
    _asr_chunk_texts: list[str]
    _asr_lock: Any  # threading.Lock from ASRSupportMixin
    _call_media: Any | None
    _collect_event: Callable[..., None]

    # Intent classification state
    _intent_classifier: Any | None = None
    _intent_enabled: bool = False
    _intent_classified: bool = False
    _classified_intent: str | None = None
    _intent_confidence: float = 0.0
    _intent_response_played: bool = False
    _intent_response_player: Any | None = None
    _intent_response_start_time: float | None = None
    _intent_response_duration: float = 0.0
    _intent_response_stop_time: float | None = None
    _intent_response_finished: bool = False
    _intent_response_finished_time: float | None = None

    def _init_intent_state(self) -> None:
        """Initialize intent classification state."""
        # Get intent settings from account
        self._intent_enabled = bool(getattr(self._acc_ref, "enable_intent", False))
        self._intent_classifier = getattr(self._acc_ref, "_intent_classifier", None)

        # Initialize state variables
        self._intent_classified = False
        self._classified_intent = None
        self._intent_confidence = 0.0
        self._intent_response_played = False
        self._intent_response_player = None
        self._intent_response_start_time = None
        self._intent_response_duration = 0.0
        self._intent_response_stop_time = None
        self._intent_response_finished = False
        self._intent_response_finished_time = None
        self._intent_results = []

        if self._intent_enabled and self._intent_classifier:
            class_name = type(self._intent_classifier).__name__
            print(f"***Intent: classifier enabled: {class_name}")

    def _setup_intent_classifier(self, classifier: Any) -> None:
        """Setup intent classifier.

        Args:
            classifier: Intent classifier instance
        """
        self._intent_classifier = classifier
        self._intent_enabled = True
        print(f"***Intent: classifier enabled: {type(classifier).__name__}")

    def _classify_intent(self) -> Tuple[str, float] | None:
        """Classify intent from transcription.

        Returns:
            Tuple of (intent_name, confidence) or None if not available
        """
        if not self._intent_enabled or not self._intent_classifier:
            return None

        if self._intent_classified:
            if self._classified_intent is None:
                return None
            return self._classified_intent, self._intent_confidence

        # Get transcription text (thread-safe)
        transcription_text = None
        try:
            asr_chunk_texts = getattr(self, "_asr_chunk_texts", [])
            asr_lock = getattr(self, "_asr_lock", None)

            if asr_lock is not None:
                with asr_lock:
                    if asr_chunk_texts:
                        transcription_text = " ".join(
                            t for t in asr_chunk_texts if t
                        ).strip()
            else:
                if asr_chunk_texts:
                    transcription_text = " ".join(
                        t for t in asr_chunk_texts if t
                    ).strip()
        except Exception as exc:
            print(f"***Intent: error getting transcription: {exc}")
            return None

        if not transcription_text:
            print("***Intent: no transcription available for classification")
            return None

        # Classify intent
        try:
            intent_name, confidence, faq_config = self._intent_classifier.classify(
                transcription_text
            )

            self._intent_classified = True
            self._classified_intent = intent_name
            self._intent_confidence = confidence

            print(
                f"***Intent: classified as '{intent_name}' "
                f"(confidence: {confidence:.2f})"
            )
            print(f"***Intent: transcription: {transcription_text[:100]}...")

            # Collect intent classification event
            self._collect_event(
                event_type="intent_classified",
                intent=intent_name,
                confidence=round(confidence, 3),
                transcription_length=len(transcription_text),
            )

            return intent_name, confidence

        except Exception as exc:
            print(f"***Intent: classification error: {exc}")
            return None

    def _play_intent_response(self) -> None:
        """Play response audio for classified intent."""
        if self._intent_response_played:
            return

        # Classify intent if not done yet
        classification = self._classify_intent()
        if not classification:
            print("***Intent: no intent classified, skipping response")
            return

        intent_name, confidence = classification

        # Get FAQ config from classifier
        if not self._intent_classifier:
            return

        try:
            # Get actual config for this intent
            from pjsua_bot.intent.faq_config import FAQS

            faq_config = FAQS.get(intent_name, FAQS["default"])
        except Exception as exc:
            print(f"***Intent: error getting FAQ config: {exc}")
            return

        # Determine response method (audio file or TTS)
        response_audio = faq_config.get("response_audio")
        response_text = faq_config.get("response_text", "")

        if response_audio and os.path.exists(response_audio):
            # Play pre-recorded audio
            self._play_response_audio(response_audio, intent_name)
        elif response_text:
            # Fallback: use TTS (Phase 2 or 3)
            truncated = response_text[:50]
            print(f"***Intent: TTS not yet implemented, using text: {truncated}...")
            # For now, just log the response text
            self._intent_response_played = True

    def _play_response_audio(self, audio_path: str, intent_name: str) -> None:
        """Play response audio file.

        Args:
            audio_path: Path to audio file
            intent_name: Name of classified intent
        """
        if not self._call_media:
            print("***Intent: no call media available")
            self._intent_response_finished = True
            return

        try:
            import pjsua2 as pj

            from ...utils import get_wav_duration

            # Get WAV file duration
            response_duration = get_wav_duration(audio_path)
            if response_duration is None:
                response_duration = getattr(self._acc_ref, "message_duration", 5)
                print(f"***Intent: using fallback duration {response_duration}s")

            # Create player for intent response
            self._intent_response_player = pj.AudioMediaPlayer()
            self._intent_response_player.createPlayer(audio_path, False)  # No loop

            # Connect player to call media
            self._intent_response_player.startTransmit(self._call_media)

            # Also connect to mixed recorder if available
            mixed_recorder = getattr(self, "_mixed_recorder", None)
            if mixed_recorder:
                try:
                    self._intent_response_player.startTransmit(mixed_recorder)
                    print("***Intent: transmitting to mixed recorder")
                except Exception:
                    pass  # Recorder might not be available

            self._intent_response_played = True
            self._intent_response_start_time = time.time()
            self._intent_response_duration = response_duration
            self._intent_response_stop_time = time.time() + response_duration
            self._intent_response_finished = False

            # Start tracking bot talk duration
            if hasattr(self, "_start_bot_playback_tracking"):
                try:
                    self._start_bot_playback_tracking()
                except Exception as exc:
                    print(
                        "***Bot tracking: error starting intent response "
                        f"tracking: {exc}"
                    )

            print(
                f"***Intent: playing response audio for '{intent_name}': {audio_path}"
            )
            print(
                f"***Intent: started playing, will finish after "
                f"{response_duration:.2f} seconds"
            )

            # Collect event
            self._collect_event(
                event_type="intent_response_played",
                intent=intent_name,
                audio_file=audio_path,
            )

        except Exception as exc:
            print(f"***Intent: error playing response audio: {exc}")
            self._intent_response_played = True  # Mark as played to avoid retry loops
            self._intent_response_finished = True

    def check_intent_response_status(self) -> bool:
        """Check if intent response has finished playing.

        Returns:
            True if response finished or not needed, False if still playing
        """
        if not self._intent_response_played:
            return True  # Not playing, so consider it "finished"

        if self._intent_response_finished:
            return True  # Already finished

        # Check if it's time to stop the intent response player
        current_time = time.time()
        if (
            self._intent_response_stop_time
            and current_time >= self._intent_response_stop_time
        ):
            print(
                f"***Intent: stop time reached (current={current_time:.2f}, stop={self._intent_response_stop_time:.2f}, elapsed={current_time - (self._intent_response_stop_time - self._intent_response_duration):.2f}s)"
            )
            # Stop the player
            if self._intent_response_player:
                try:
                    import pjsua2 as pj  # local import

                    # Stop all transmissions first
                    self._intent_response_player.stopTransmit(self._call_media)
                    print("***Intent: stopped player transmission to call media")

                    mixed_recorder = getattr(self, "_mixed_recorder", None)
                    if mixed_recorder:
                        try:
                            self._intent_response_player.stopTransmit(mixed_recorder)
                            print(
                                "***Intent: stopped player transmission to mixed recorder"
                            )
                        except Exception:
                            pass

                    # Also stop the call media to playback transmission
                    # to break the audio path and prevent looping
                    try:
                        adm = pj.Endpoint.instance().audDevManager()
                        playback = adm.getPlaybackDevMedia()
                        self._call_media.stopTransmit(playback)
                        print("***Intent: stopped call media to playback transmission")
                    except Exception:
                        pass

                    # Try to stop the player explicitly before destroying
                    try:
                        # Some PJSUA2 players have a stop() method
                        if hasattr(self._intent_response_player, "stop"):
                            self._intent_response_player.stop()
                            print("***Intent: called player.stop()")
                    except Exception:
                        pass  # stop() might not be available, that's OK

                    # Destroy the player to ensure it's fully stopped
                    self._intent_response_player = None
                    print("***Intent: response audio finished and player destroyed")
                except Exception as e:
                    print(f"***Intent: error stopping response player: {e}")
                    # Even if there's an error, clear the player reference
                    self._intent_response_player = None

                # Stop tracking bot talk duration
                if hasattr(self, "_stop_bot_playback_tracking"):
                    try:
                        self._stop_bot_playback_tracking()
                    except Exception as e:
                        print(
                            "***Bot tracking: error stopping intent response "
                            f"tracking: {e}"
                        )

                # Notify VAD that bot playback finished (intent response)
                # This helps VAD know that we're transitioning to goodbye phase
                if hasattr(self, "_vad") and getattr(self, "_vad", None):
                    vad = getattr(self, "_vad", None)
                    if vad and getattr(vad, "available", False):
                        try:
                            vad.set_bot_playback_state(False, time.time)
                            print("***Intent: notified VAD that response finished")
                        except Exception as e:
                            print(f"***Intent: error notifying VAD: {e}")

            self._intent_response_finished = True
            self._intent_response_finished_time = time.time()
            return True

        return False  # Still playing
