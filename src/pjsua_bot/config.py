"""Configuration classes for the SIP bot."""

import argparse
import os
from dataclasses import dataclass
from typing import Optional

from .utils import DEFAULT_RECORDING_PATH


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
    asr_model: str = "omniASR_CTC_1B"

    # Intent
    enable_intent: bool = False
    intent_classifier: str = "rule-based"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_use_cpu: bool = False
    faq_config: Optional[str] = None

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
            log_level=args.log_level,
        )
