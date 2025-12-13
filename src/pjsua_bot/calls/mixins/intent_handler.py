"""Intent classification and response handling mixin."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Protocol, Tuple, cast

from pjsua_bot.intent.faq_config import FAQS

logger = logging.getLogger(__name__)

# Event type constants
EVENT_INTENT_CLASSIFIED = "intent_classified"
EVENT_INTENT_RESPONSE_PLAYED = "intent_response_played"

if TYPE_CHECKING:
    import pjsua2 as pj

    from pjsua_bot.intent.classifier import IntentClassifier
else:
    # Runtime imports for type hints
    pj = None  # type: ignore[assignment]
    IntentClassifier = None  # type: ignore[assignment, misc]


class AccountProtocol(Protocol):
    """Protocol for account objects used by IntentHandlerMixin."""

    enable_intent: bool
    _intent_classifier: Optional["IntentClassifier"]
    message_duration: int


class IntentHandlerMixin:
    """Mixin providing intent classification and response playback."""

    # Attributes supplied by sibling mixins / host class
    _acc_ref: AccountProtocol
    _asr_enabled: bool
    _asr_available: bool
    _asr_chunk_texts: list[str]
    _asr_lock: threading.Lock
    _call_media: Optional["pj.AudioMedia"]
    _collect_event: Callable[..., None]
    _vad: Any | None

    # Intent classification state
    _intent_classifier: Optional["IntentClassifier"] = None
    _intent_enabled: bool = False
    _intent_classified: bool = False
    _classified_intent: Optional[str] = None
    _intent_confidence: float = 0.0
    _classified_faq_config: Optional[Dict[str, Any]] = None
    _intent_response_played: bool = False
    _intent_response_player: Optional["pj.AudioMediaPlayer"] = None
    _intent_response_start_time: Optional[float] = None
    _intent_response_duration: float = 0.0
    _intent_response_stop_time: Optional[float] = None
    _intent_response_finished: bool = False
    _intent_response_finished_time: Optional[float] = None

    def _get_account_attr(self, attr_name: str, default: object = None) -> object:
        """Get attribute from account reference with fallback.

        Args:
            attr_name: Name of the attribute to get
            default: Default value if attribute doesn't exist

        Returns:
            Attribute value or default
        """
        return getattr(self._acc_ref, attr_name, default)

    def _get_asr_data(self) -> tuple[list[str], Optional[threading.Lock]]:
        """Get ASR chunk texts and lock in a thread-safe way.

        Returns:
            Tuple of (chunk_texts, lock) with safe defaults
        """
        chunk_texts = getattr(self, "_asr_chunk_texts", [])
        asr_lock = getattr(self, "_asr_lock", None)
        return chunk_texts, asr_lock

    def _get_mixed_recorder(self) -> Optional[object]:
        """Get mixed recorder if available.

        Returns:
            Mixed recorder instance or None
        """
        return getattr(self, "_mixed_recorder", None)

    def _get_vad(self) -> Optional[object]:
        """Get VAD instance if available.

        Returns:
            VAD instance or None
        """
        return getattr(self, "_vad", None)

    def _init_intent_state(self) -> None:
        """Initialize intent classification state."""
        # Get intent settings from account
        self._intent_enabled = bool(self._get_account_attr("enable_intent", False))
        self._intent_classifier = cast(
            Optional["IntentClassifier"],
            self._get_account_attr("_intent_classifier", None),
        )

        # Initialize state variables
        self._intent_classified = False
        self._classified_intent = None
        self._intent_confidence = 0.0
        self._classified_faq_config = None
        self._intent_response_played = False
        self._intent_response_player = None
        self._intent_response_start_time = None
        self._intent_response_duration = 0.0
        self._intent_response_stop_time = None
        self._intent_response_finished = False
        self._intent_response_finished_time = None
        self._intent_results: list[Dict[str, object]] = []

        if self._intent_enabled and self._intent_classifier:
            class_name = type(self._intent_classifier).__name__
            logger.info("Intent: classifier enabled: %s", class_name)

    def _setup_intent_classifier(self, classifier: "IntentClassifier") -> None:
        """Setup intent classifier.

        Args:
            classifier: Intent classifier instance
        """
        self._intent_classifier = classifier
        self._intent_enabled = True
        logger.info("Intent: classifier enabled: %s", type(classifier).__name__)

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
            asr_chunk_texts, asr_lock = self._get_asr_data()

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
        except (AttributeError, RuntimeError, TypeError) as exc:
            logger.error("Intent: error getting transcription: %s", exc, exc_info=True)
            return None

        if not transcription_text:
            logger.warning("Intent: no transcription available for classification")
            return None

            # Classify intent
        try:
            intent_name, confidence, faq_config = self._intent_classifier.classify(
                transcription_text
            )

            self._intent_classified = True
            self._classified_intent = intent_name
            self._intent_confidence = confidence
            self._classified_faq_config = faq_config  # Store FAQ config from classifier

            logger.info(
                "Intent: classified as '%s' (confidence: %.2f)",
                intent_name,
                confidence,
            )
            logger.debug("Intent: transcription: %s...", transcription_text[:100])

            # Collect intent classification event
            self._collect_event(
                event_type=EVENT_INTENT_CLASSIFIED,
                intent_name=intent_name,
                confidence=round(confidence, 3),
                transcription_length=len(transcription_text),
            )

            return intent_name, confidence

        except (ValueError, RuntimeError, AttributeError, TypeError) as exc:
            logger.error("Intent: classification error: %s", exc, exc_info=True)
            return None

    def _play_intent_response(self) -> None:
        """Play response audio for classified intent."""
        if self._intent_response_played:
            return

        # Classify intent if not done yet
        classification = self._classify_intent()
        if not classification:
            logger.warning("Intent: no intent classified, skipping response")
            return

        intent_name, confidence = classification

        # Use FAQ config from classifier (stored during classification)
        # Fallback to FAQS dict if not available (backward compatibility)
        faq_config = self._classified_faq_config
        if not faq_config:
            try:
                faq_config = FAQS.get(intent_name, FAQS["default"])
            except (ImportError, KeyError, AttributeError, TypeError) as exc:
                logger.error("Intent: error getting FAQ config: %s", exc, exc_info=True)
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
            logger.warning(
                "Intent: TTS not yet implemented, using text: %s...", truncated
            )
            # For now, just log the response text
            self._intent_response_played = True

    def _play_response_audio(self, audio_path: str, intent_name: str) -> None:
        """Play response audio file.

        Args:
            audio_path: Path to audio file
            intent_name: Name of classified intent
        """
        if not self._call_media:
            logger.warning("Intent: no call media available")
            self._intent_response_finished = True
            return

        try:
            import pjsua2 as pj

            from ...utils import get_wav_duration

            # Get WAV file duration
            response_duration = get_wav_duration(audio_path)
            if response_duration is None:
                response_duration = self._get_account_attr("message_duration", 5)
                logger.warning("Intent: using fallback duration %ss", response_duration)

            # Create player for intent response
            self._intent_response_player = pj.AudioMediaPlayer()
            # PJMEDIA_FILE_NO_LOOP = 1 prevents looping (False=0 would allow looping)
            self._intent_response_player.createPlayer(
                audio_path, pj.PJMEDIA_FILE_NO_LOOP
            )

            # Connect player to call media
            self._intent_response_player.startTransmit(self._call_media)

            # Also connect to mixed recorder if available
            mixed_recorder = self._get_mixed_recorder()
            if mixed_recorder:
                try:
                    self._intent_response_player.startTransmit(mixed_recorder)
                    logger.debug("Intent: transmitting to mixed recorder")
                except (RuntimeError, AttributeError):
                    pass  # Recorder might not be available

            if self._vad and getattr(self._vad, "available", False):
                try:
                    self._vad.set_bot_playback_state(True, time.time)
                except Exception as exc:
                    logger.error("Intent: VAD start error: %s", exc, exc_info=True)

            self._intent_response_played = True
            self._intent_response_start_time = time.time()
            self._intent_response_duration = response_duration
            self._intent_response_stop_time = time.time() + response_duration
            self._intent_response_finished = False

            # Start tracking bot talk duration
            if hasattr(self, "_start_bot_playback_tracking"):
                try:
                    self._start_bot_playback_tracking()
                except (AttributeError, RuntimeError, TypeError) as exc:
                    logger.error(
                        "Bot tracking: error starting intent response tracking: %s",
                        exc,
                        exc_info=True,
                    )

            logger.info(
                "Intent: playing response audio for '%s': %s",
                intent_name,
                audio_path,
            )
            logger.debug(
                "Intent: started playing, will finish after %.2f seconds",
                response_duration,
            )

            # Collect event
            self._collect_event(
                event_type=EVENT_INTENT_RESPONSE_PLAYED,
                intent_name=intent_name,
                audio_file=audio_path,
            )

        except (
            OSError,
            IOError,
            RuntimeError,
            AttributeError,
            ValueError,
            TypeError,
        ) as exc:
            logger.error("Intent: error playing response audio: %s", exc, exc_info=True)
            self._intent_response_played = True  # Mark as played to avoid retry loops
            self._intent_response_finished = True

    def _should_check_response_status(self) -> bool:
        """Check if response status check should proceed.

        Returns:
            True if check should proceed, False if already finished/not playing
        """
        if not self._intent_response_played:
            return False  # Not playing, so consider it "finished"
        if self._intent_response_finished:
            return False  # Already finished
        return True

    def _is_response_stop_time_reached(self) -> bool:
        """Check if response stop time has been reached.

        Returns:
            True if stop time reached and buffer delay has passed, False otherwise
        """
        if not self._intent_response_stop_time:
            return False

        current_time = time.time()
        # Add a buffer delay after the calculated stop time to account for:
        # 1. Audio pipeline latency (jitter buffer, RTP buffering)
        # 2. Time for buffered audio to drain from the pipeline
        # This prevents the goodbye message from starting before the intent response
        # audio has actually finished playing on the remote side.
        AUDIO_DRAIN_BUFFER = 0.5  # seconds - small buffer for pipeline latency
        effective_stop_time = self._intent_response_stop_time + AUDIO_DRAIN_BUFFER

        if current_time >= effective_stop_time:
            elapsed = current_time - (
                self._intent_response_stop_time - self._intent_response_duration
            )
            logger.debug(
                "Intent: stop time reached (current=%.2f, stop=%.2f, elapsed=%.2fs, buffer=%.2fs)",
                current_time,
                self._intent_response_stop_time,
                elapsed,
                AUDIO_DRAIN_BUFFER,
            )
            return True
        return False

    def _stop_player_transmissions(self) -> None:
        """Stop all transmissions from the intent response player."""
        if not self._intent_response_player:
            return

        # Check if call is still active before attempting port disconnection
        # If call is disconnected, PJSUA2 has already disconnected ports
        call_active = False
        try:
            if hasattr(self, "isActive"):
                call_active = self.isActive()
        except Exception:
            # Call might be destroyed, assume inactive
            call_active = False

        if not call_active:
            return

        try:
            # Stop transmission to call media
            self._intent_response_player.stopTransmit(self._call_media)
            logger.debug("Intent: stopped player transmission to call media")

            # Stop transmission to mixed recorder if available
            mixed_recorder = self._get_mixed_recorder()
            if mixed_recorder:
                try:
                    self._intent_response_player.stopTransmit(mixed_recorder)
                    logger.debug(
                        "Intent: stopped player transmission to mixed recorder"
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Intent: error stopping player transmissions: %s", e)

    def _stop_call_media_to_playback(self) -> None:
        """Stop call media to playback transmission.

        Breaks audio path and prevents looping.
        """
        if self._call_media is None:
            return

        # Check if call is still active before attempting port disconnection
        # If call is disconnected, PJSUA2 has already disconnected ports
        call_active = False
        try:
            if hasattr(self, "isActive"):
                call_active = self.isActive()
        except Exception:
            # Call might be destroyed, assume inactive
            call_active = False

        if not call_active:
            return

        # FIX: Skip stopping call_media->playback transmission to avoid PJSUA2
        # internal "Remove port failed" error (same fix as in playback_monitor.py)
        # try:
        #     import pjsua2 as pj
        #     adm = pj.Endpoint.instance().audDevManager()
        #     playback = adm.getPlaybackDevMedia()
        #     self._call_media.stopTransmit(playback)
        #     logger.debug("Intent: stopped call media to playback transmission")
        # except (RuntimeError, AttributeError) as e:
        #     logger.debug("Intent: could not stop call media to playback: %s", e)

    def _stop_and_destroy_player(self) -> None:
        """Stop the player explicitly and destroy it."""
        if not self._intent_response_player:
            return

        try:
            # Try to stop the player explicitly before destroying
            if hasattr(self._intent_response_player, "stop"):
                self._intent_response_player.stop()
                logger.debug("Intent: called player.stop()")
        except (RuntimeError, AttributeError):
            pass  # stop() might not be available, that's OK

        # Destroy the player to ensure it's fully stopped
        self._intent_response_player = None
        logger.info("Intent: response audio finished and player destroyed")

    def _cleanup_intent_response_player(self) -> None:
        """Clean up the intent response player and all related transmissions."""
        if not self._intent_response_player:
            return

        # Check if call is still active
        call_active = False
        try:
            if hasattr(self, "isActive"):
                call_active = self.isActive()
        except Exception:
            call_active = False

        try:
            # Stop all transmissions first (only if call is active)
            if call_active:
                self._stop_player_transmissions()
                # Stop call media to playback transmission
                self._stop_call_media_to_playback()
            else:
                # Call is inactive (user hung up), skip transmission stopping
                # but still destroy the player to allow goodbye transition
                logger.debug(
                    "Intent: call inactive, skipping transmission stop, destroying player directly"
                )

            # Always stop and destroy the player, regardless of call state
            # This ensures cleanup happens even if user hung up
            self._stop_and_destroy_player()

        except (RuntimeError, AttributeError, ValueError, TypeError) as e:
            logger.error("Intent: error stopping response player: %s", e, exc_info=True)
            # Even if there's an error, clear the player reference
            self._intent_response_player = None

    def _notify_response_finished(self) -> None:
        """Notify VAD and stop bot playback tracking that response finished."""
        # Stop tracking bot talk duration
        if hasattr(self, "_stop_bot_playback_tracking"):
            try:
                self._stop_bot_playback_tracking()
            except (AttributeError, RuntimeError, TypeError) as e:
                logger.error(
                    "Bot tracking: error stopping intent response tracking: %s",
                    e,
                    exc_info=True,
                )

        # Notify VAD that bot playback finished (intent response)
        # This helps VAD know that we're transitioning to goodbye phase
        vad = self._get_vad()
        if vad and getattr(vad, "available", False):
            try:
                # VAD expects a callable for time, not the result of time.time()
                vad.set_bot_playback_state(False, time.time)  # type: ignore[attr-defined]
                logger.debug("Intent: notified VAD that response finished")
            except (AttributeError, RuntimeError, TypeError, ValueError) as e:
                logger.error("Intent: error notifying VAD: %s", e, exc_info=True)

    def _mark_response_as_finished(self) -> None:
        """Mark the intent response as finished and update state."""
        self._intent_response_finished = True
        self._intent_response_finished_time = time.time()

    def check_intent_response_status(self) -> bool:
        """Check if intent response has finished playing.

        Returns:
            True if response finished or not needed, False if still playing
        """
        # Early return checks
        if not self._should_check_response_status():
            return True

        # Check if call is still active
        call_active = False
        try:
            if hasattr(self, "isActive"):
                call_active = self.isActive()
        except Exception:
            call_active = False

        # If call is inactive and intent response was playing, force cleanup
        # This handles the case where user hung up before goodbye message
        if (
            not call_active
            and self._intent_response_played
            and not self._intent_response_finished
        ):
            logger.debug(
                "Intent: call inactive but response was playing, forcing cleanup"
            )
            self._cleanup_intent_response_player()
            self._notify_response_finished()
            self._mark_response_as_finished()
            return True

        # Check if it's time to stop the intent response player
        if not self._is_response_stop_time_reached():
            return False  # Still playing

        # Clean up player and related resources
        self._cleanup_intent_response_player()

        # Notify other components that response finished
        self._notify_response_finished()

        # Mark as finished
        self._mark_response_as_finished()
        return True
