"""Configuration classes for the SIP bot."""

import argparse
import os
from dataclasses import dataclass
from typing import Literal, Optional

from .utils import DEFAULT_RECORDING_PATH

VALID_SATISFACTION_RETRIES = (2, 3)
VALID_FLOW_MODES = ("legacy", "satisfaction")
FlowMode = Literal["legacy", "satisfaction"]


@dataclass
class BotConfig:
    """Configuration for the SIP bot."""

    # SIP credentials
    user: str
    password: str
    domain: str
    auth_user: Optional[str] = None
    local_port: int = 5060
    outbound_proxy: Optional[str] = None
    transport: str = "udp"
    tls_verify: bool = False

    # Registration
    wait_seconds: int = 10

    # Call handling
    dest: Optional[str] = None
    hangup_seconds: int = 0
    stay_online: bool = False
    auto_answer: bool = True

    # Audio files
    play_file: str = "welcome_message.wav"
    goodbye_file: str = "goodbye_voice.wav"
    hangup_delay: int = 2
    message_duration: int = 5

    # Recording
    enable_recording: bool = False
    recording_path: str = os.getenv("RECORDING_PATH", DEFAULT_RECORDING_PATH)

    # VAD
    enable_vad: bool = False
    silence_after_speech_sec: float = 3.0
    vad_threshold: float = 0.5

    # ASR
    enable_asr: bool = False
    asr_model: str = "omniASR_CTC_300M"

    # Intent
    enable_intent: bool = False
    intent_classifier: str = "rule-based"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_use_cpu: bool = False
    faq_config: Optional[str] = None

    # Conversation flow
    # `legacy`: original "any other questions?" + repeat_or_support flow.
    # `satisfaction`: new question -> answer -> satisfaction-check -> retry/escalate flow.
    flow_mode: FlowMode = "legacy"
    # Retry budget for the satisfaction flow; only NO satisfaction answers
    # consume the budget. Must be 2 or 3.
    max_satisfaction_retries: int = 2
    # Extension to blind-transfer to when the satisfaction retry budget is
    # exhausted. Empty/None means escalation will play the announcement and
    # then hang up (no transfer).
    support_transfer_extension: Optional[str] = None

    # Logging
    log_level: int = 3

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "BotConfig":
        """Create BotConfig from parsed arguments.

        Args:
            args: Parsed command line arguments

        Returns:
            BotConfig instance
        """
        return cls(
            user=args.user,
            password=args.password,
            domain=args.domain,
            auth_user=args.auth_user,
            local_port=args.local_port,
            outbound_proxy=args.outbound_proxy,
            transport=args.transport,
            tls_verify=args.tls_verify,
            wait_seconds=args.wait_seconds,
            dest=args.dest,
            hangup_seconds=args.hangup_seconds,
            stay_online=args.stay_online,
            auto_answer=args.auto_answer or not args.no_auto_answer,
            play_file=args.play_file,
            goodbye_file=args.goodbye_file,
            hangup_delay=args.hangup_delay,
            message_duration=args.message_duration,
            enable_recording=args.enable_recording,
            recording_path=args.recording_path,
            enable_vad=args.enable_vad,
            silence_after_speech_sec=args.silence_after_speech_sec,
            vad_threshold=args.vad_threshold,
            enable_asr=args.enable_asr,
            asr_model=args.asr_model,
            enable_intent=args.enable_intent,
            intent_classifier=args.intent_classifier,
            ollama_url=args.ollama_url,
            ollama_model=args.ollama_model,
            ollama_use_cpu=args.ollama_use_cpu,
            faq_config=args.faq_config,
            flow_mode=args.flow_mode,
            max_satisfaction_retries=args.max_satisfaction_retries,
            support_transfer_extension=args.support_transfer_extension,
            log_level=args.log_level,
        )

    def validate(self) -> None:
        """Validate config values; raise ValueError on bad input."""
        if self.flow_mode not in VALID_FLOW_MODES:
            raise ValueError(
                f"--flow-mode must be one of {VALID_FLOW_MODES!r}, "
                f"got {self.flow_mode!r}"
            )
        if self.max_satisfaction_retries not in VALID_SATISFACTION_RETRIES:
            raise ValueError(
                f"--max-satisfaction-retries must be one of "
                f"{VALID_SATISFACTION_RETRIES!r}, "
                f"got {self.max_satisfaction_retries!r}"
            )
