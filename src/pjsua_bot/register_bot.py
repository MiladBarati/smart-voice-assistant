import argparse
import os
import signal
import sys
import threading
import time
from types import FrameType
from typing import Any

import pjsua2 as pj

# Support running both as a module and as a script
if __package__ in (None, ""):
    import os

    # Add parent directory (the 'src' root)
    # so absolute imports work when executed directly
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pjsua_bot.account import Account
    from pjsua_bot.calls import OutCall
    from pjsua_bot.elasticsearch_client import es_logger
    from pjsua_bot.utils import get_wav_duration, pump_events, setup_logging, wait_until
else:
    from .account import Account
    from .calls import OutCall
    from .elasticsearch_client import es_logger
    from .utils import get_wav_duration, pump_events, setup_logging, wait_until


# ---------- Resource Cleanup ----------


def cleanup_resources(acc: Any) -> None:
    """Clean up all resources including ASR models, intent classifiers, and connections.

    Args:
        acc: Account instance that may contain resources to clean up
    """
    print("***Cleaning up resources...")

    # Stop all ASR threads from all calls
    try:
        calls_copy = dict(getattr(acc, "calls", {}))
        for _call_id, call in calls_copy.items():
            try:
                if hasattr(call, "_stop_asr_thread"):
                    call._stop_asr_thread()
            except Exception:
                pass
    except Exception as e:
        print(f"***ASR thread cleanup error: {e}")

    # Cleanup ASR Service
    try:
        if hasattr(acc, "_asr_service") and acc._asr_service is not None:
            print("***Cleaning up ASR service...")
            asr_service = acc._asr_service

            # Release the pipeline/model
            if hasattr(asr_service, "_pipeline") and asr_service._pipeline is not None:
                asr_service._pipeline = None
                print("***ASR: Pipeline released")

            # Clear CUDA cache if GPU was used
            if hasattr(asr_service, "_device") and asr_service._device == "cuda":
                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        # Wait for all CUDA operations to complete
                        torch.cuda.synchronize()
                        print("***ASR: CUDA cache cleared")
                except ImportError:
                    pass  # torch not available
                except Exception as e:
                    print(f"***ASR: Error clearing CUDA cache: {e}")

            # Clear the service reference
            acc._asr_service = None
            print("***ASR: Service cleaned up")
    except Exception as e:
        print(f"***ASR cleanup error: {e}")

    # Cleanup Intent Classifier
    try:
        if hasattr(acc, "_intent_classifier") and acc._intent_classifier is not None:
            print("***Cleaning up intent classifier...")
            classifier = acc._intent_classifier

            # For OllamaClassifier, clear fallback classifier if it exists
            if hasattr(classifier, "_fallback_classifier"):
                classifier._fallback_classifier = None

            # Clear the classifier reference
            acc._intent_classifier = None
            acc.enable_intent = False
            print("***Intent: Classifier cleaned up")
    except Exception as e:
        print(f"***Intent classifier cleanup error: {e}")

    # Cleanup Elasticsearch client
    try:
        if es_logger.client is not None:
            print("***Cleaning up Elasticsearch connection...")
            # Try to close the connection if the client has a close method
            if hasattr(es_logger.client, "close"):
                try:
                    es_logger.client.close()
                    print("***Elasticsearch: Connection closed")
                except Exception as e:
                    print(f"***Elasticsearch: Error closing connection: {e}")

            # Clear the client reference
            es_logger.client = None
            es_logger.connected = False
            print("***Elasticsearch: Client cleaned up")
    except Exception as e:
        print(f"***Elasticsearch cleanup error: {e}")

    print("***Resource cleanup complete")


# ---------- Main ----------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "PJSUA2 registration/call bot with proper event pumping and options."
        )
    )
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--domain",
        required=True,
        help="Registrar/realm host or domain",
    )
    parser.add_argument("--auth-user", default=None)
    parser.add_argument("--local-port", type=int, default=5060)
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=10,
        help="Time to wait for registration/connect",
    )
    parser.add_argument(
        "--stay-online",
        action="store_true",
        help="Keep endpoint running to receive calls",
    )
    parser.add_argument(
        "--auto-answer",
        action="store_true",
        help="Answer incoming calls with 200 OK (default: True)",
    )
    parser.add_argument(
        "--no-auto-answer",
        action="store_true",
        help="Disable auto-answering of incoming calls",
    )
    parser.add_argument(
        "--dest",
        default=None,
        help=("Destination SIP URI or extension (sip:1002@host or just 1002)"),
    )
    parser.add_argument(
        "--hangup-seconds",
        type=int,
        default=0,
        help=("Auto hangup after N seconds of connection; 0 to disable"),
    )
    parser.add_argument(
        "--outbound-proxy",
        default=None,
        help="Outbound proxy URI, e.g. sip:host:5060;lr",
    )
    parser.add_argument(
        "--transport",
        choices=["udp", "tcp", "tls"],
        default="udp",
        help="SIP transport",
    )
    parser.add_argument(
        "--tls-verify",
        action="store_true",
        help="Verify TLS server certificate (when --transport tls)",
    )
    parser.add_argument(
        "--log-level",
        type=int,
        default=3,
        help="Endpoint log level (0-6)",
    )
    parser.add_argument(
        "--play-file",
        default="welcome_message.wav",
        help=(
            "Path to WAV file to play to remote when call media is active "
            "(default: welcome_message.wav)"
        ),
    )
    parser.add_argument(
        "--goodbye-file",
        default="goodbye_voice.wav",
        help=(
            "Path to WAV file to play before hanging up (default: goodbye_voice.wav)"
        ),
    )
    parser.add_argument(
        "--waiting-file",
        default="waiting_voice.wav",
        help=(
            "Path to WAV file to play when VAD detects silence "
            "(default: assets/audio/waiting_voice.wav)"
        ),
    )
    parser.add_argument(
        "--hangup-delay",
        type=int,
        default=2,
        help=("Deprecated: fixed delay; overridden by VAD-based hangup if enabled"),
    )
    parser.add_argument(
        "--message-duration",
        type=int,
        default=5,
        help=("Fallback duration in seconds if WAV file cannot be read (default: 5)"),
    )
    parser.add_argument(
        "--enable-recording",
        action="store_true",
        help="Enable voice capture for incoming calls (default: False)",
    )
    parser.add_argument(
        "--recording-path",
        default=os.getenv("RECORDING_PATH", "./recordings"),
        help=(
            "Base directory for storing recorded audio files "
            "(default: ./recordings or RECORDING_PATH env var)"
        ),
    )
    parser.add_argument(
        "--enable-vad",
        action="store_true",
        help=("Enable Silero VAD-based hangup after caller silence (default: False)"),
    )
    parser.add_argument(
        "--silence-after-speech-sec",
        type=float,
        default=3.0,
        help=("Seconds of silence after last caller speech to hang up (default: 3.0)"),
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.5,
        help=("Silero VAD speech probability threshold (default: 0.5)"),
    )
    parser.add_argument(
        "--enable-asr",
        action="store_true",
        help=(
            "Enable Whisper-based ASR for live and final transcription "
            "(default: disabled)"
        ),
    )
    parser.add_argument(
        "--enable-intent",
        action="store_true",
        help="Enable intent classification from transcription (default: False)",
    )
    parser.add_argument(
        "--intent-classifier",
        choices=["rule-based", "ollama"],
        default="rule-based",
        help=(
            "Intent classifier to use: rule-based (keyword matching) "
            "or ollama (LLM-based) (default: rule-based)"
        ),
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama API base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="qwen2.5:7b",
        help=(
            "Ollama model name (default: qwen2.5:7b). "
            "For CPU usage, use smaller models: qwen2.5:0.5b, "
            "qwen2.5:1.5b, qwen2.5:3b, or qwen2.5:7b"
        ),
    )
    parser.add_argument(
        "--ollama-use-cpu",
        action="store_true",
        help="Attempt to force CPU usage for Ollama (hint only). "
        "To truly force CPU, set OLLAMA_NUM_GPU=0 before starting Ollama server",
    )
    parser.add_argument(
        "--faq-config",
        type=str,
        default=None,
        help="Path to custom FAQ JSON config file (optional)",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Test Elasticsearch connection
    print("***Testing Elasticsearch connection...")
    health = es_logger.health_check()
    if health.get("status") == "connected":
        print(f"***Elasticsearch connected: {health.get('cluster_name', 'unknown')}")
    else:
        err = health.get("error", "unknown error")
        print(f"***Elasticsearch connection failed: {err}")

    # Create and initialize the library
    ep_cfg = pj.EpConfig()
    ep_cfg.logConfig.level = args.log_level
    med = ep_cfg.medConfig
    med.clockRate = 16000
    med.sndClockRate = 16000
    med.channelCount = 1
    med.audioFramePtime = 20
    med.ptime = 20
    med.quality = 10
    med.noVad = False  # save bandwidth under loss
    med.ecTailLen = 512  # Increased from 256
    med.ecOptions = 1  # Ensure echo cancellation is enabled
    med.jbInit = 100
    med.jbMinPre = 80
    med.jbMaxPre = 300
    med.jbMax = 500
    ep = pj.Endpoint()

    ep.libCreate()
    ep.libInit(ep_cfg)

    # Graceful shutdown on SIGINT/SIGTERM
    stopping = {"flag": False, "cleanup_done": False}

    def _stop_handler(signum: int, frame: FrameType | None) -> None:
        print(f"***Signal {signum}: stopping...")
        stopping["flag"] = True

        # Set a timeout to force exit if cleanup takes too long (WSL-specific issue)
        def _force_exit() -> None:
            time.sleep(15)  # Wait 15 seconds for cleanup
            if not stopping.get("cleanup_done", False):
                print("***Force exit: cleanup taking too long, forcing exit...")
                os._exit(1)  # Force exit, bypassing cleanup

        threading.Thread(target=_force_exit, daemon=True).start()

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    try:
        # Codec configuration: PCMU (G.711) is used by default for good quality
        # PJSUA2 by default uses PCMU/PCMA which provides 64kbps @ 8kHz
        # Good quality for VoIP
        print(
            "***Codec: configured for wideband audio (16kHz), "
            "preferring Opus/G.722 over G.711"
        )

        # Create SIP transport
        sip_tp_config = pj.TransportConfig()
        sip_tp_config.port = args.local_port
        if args.transport == "udp":
            ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sip_tp_config)
            print(f"***Transport: UDP {args.local_port}")
        elif args.transport == "tcp":
            ep.transportCreate(pj.PJSIP_TRANSPORT_TCP, sip_tp_config)
            print(f"***Transport: TCP {args.local_port}")
        else:
            # TLS
            tls_cfg = pj.TlsConfig()
            tls_cfg.verifyServer = args.tls_verify
            sip_tp_config.tlsConfig = tls_cfg
            ep.transportCreate(pj.PJSIP_TRANSPORT_TLS, sip_tp_config)
            print(f"***Transport: TLS {args.local_port} verify={args.tls_verify}")

        # Configure codec priorities BEFORE starting the library
        try:
            # # Set all codecs to lowest priority first
            # for ci in ep.codecEnum():
            #     ep.codecSetPriority(ci.codecId, 0)

            # Set priorities based on what's actually available
            # Prioritize wideband codecs that ARE available
            codec_priorities = [
                # Wideband codecs (prefer these)
                ("speex/32000/1", 255),  # Ultra-wideband Speex (32kHz)
                ("speex/16000/1", 250),  # Wideband Speex (16kHz) - good quality
                ("G722/16000/1", 240),  # G.722 wideband (already working)
                ("L16/44100/1", 200),  # Uncompressed (high quality, high bandwidth)
                # Narrowband codecs (lower priority - fallbacks)
                ("PCMU/8000/1", 128),  # G.711 μ-law (narrowband)
                ("PCMA/8000/1", 120),  # G.711 A-law (narrowband)
                ("speex/8000/1", 100),  # Speex narrowband (lower than G.711)
                ("GSM/8000/1", 80),  # GSM (lowest priority)
                ("iLBC/8000/1", 70),  # iLBC (lowest priority)
            ]

            for codec_id, priority in codec_priorities:
                try:
                    ep.codecSetPriority(codec_id, priority)
                    print(f"***Codec priority set: {codec_id} to {priority}")
                except Exception:
                    pass  # Ignore if not available

            # After setting priorities, optionally disable unwanted codecs
            # This forces negotiation to prefer better codecs
            unwanted_codecs = [
                ("GSM/8000/1", 0),  # Disable GSM
                ("iLBC/8000/1", 0),  # Disable iLBC
            ]

            for codec_id, _ in unwanted_codecs:
                try:
                    ep.codecSetPriority(codec_id, 0)  # 0 = disabled
                    print(f"***Codec disabled: {codec_id}")
                except Exception:
                    pass  # Ignore if not available

        except Exception as e:
            print(f"***Codec priority config warning: {e}")

        # Start the library after codec preferences are applied
        ep.libStart()

        # Set null audio device
        ep.audDevManager().setNullDev()

        # Configure account
        acfg = pj.AccountConfig()
        acfg.idUri = f"sip:{args.user}@{args.domain}"
        acfg.regConfig.registrarUri = f"sip:{args.domain}"

        # NAT/keepalive hardening (best-effort; ignore if not available)
        try:
            acfg.sipConfig.keepAliveIntervalSec = 15  # CRLF keepalives
            acfg.natConfig.sipOutbound = 1  # RFC 5626 SIP Outbound
            acfg.natConfig.iceEnabled = True  # Enable ICE for media
        except Exception:
            pass

        # Credentials
        cred = pj.AuthCredInfo(
            "digest",
            "*",
            args.auth_user or args.user,
            0,
            args.password,
        )
        acfg.sipConfig.authCreds.append(cred)

        # Outbound proxy
        if args.outbound_proxy:
            acfg.sipConfig.proxies.append(args.outbound_proxy)

        # Create the account
        acc = Account()
        # Default to auto-answer unless explicitly disabled
        acc.auto_answer = args.auto_answer or not args.no_auto_answer
        acc.play_file = args.play_file
        acc.goodbye_file = args.goodbye_file
        acc.waiting_file = args.waiting_file
        acc.hangup_delay = args.hangup_delay
        acc.enable_recording = args.enable_recording
        acc.recording_path = args.recording_path
        acc.enable_vad = args.enable_vad
        acc.silence_after_speech_sec = args.silence_after_speech_sec
        acc.vad_threshold = args.vad_threshold
        acc.enable_asr = args.enable_asr
        # Store username and domain for logging
        acc.username = args.user
        acc.domain = args.domain

        # Get actual duration from the WAV file,
        # or use command line argument as fallback
        if args.play_file:
            actual_duration = get_wav_duration(args.play_file)
            acc.message_duration = actual_duration
            print(f"***Using actual WAV duration: {actual_duration:.2f} seconds")
        else:
            acc.message_duration = args.message_duration
        # Disable SIP Outbound & ICE temporarily
        try:
            acfg.natConfig.sipOutboundUse = pj.PJSUA_SIP_OUTBOUND_DISABLED
        except AttributeError:
            # some bindings expose it as integer; 0 == DISABLED
            acfg.natConfig.sipOutboundUse = 0

        # Also disable Contact/Via rewrite heuristics
        # that can change the Contact mid-flight
        try:
            acfg.natConfig.contactRewriteUse = pj.PJSUA_CONTACT_REWRITE_USE_DISABLED
            acfg.natConfig.viaRewriteUse = pj.PJSUA_VIA_REWRITE_USE_DISABLED
        except AttributeError:
            # fallbacks if your binding exposes them as ints
            acfg.natConfig.contactRewriteUse = 0
            acfg.natConfig.viaRewriteUse = 0

        # Do NOT force using the local source port in Contact
        try:
            acfg.natConfig.contactUseSrcPort = False
        except AttributeError:
            pass
        acc.create(acfg)

        # Initialize ASR service before registration (if enabled)
        # This loads the model once, before any calls come in
        if args.enable_asr:
            print("***ASR: initializing service before registration...")
            try:
                # Support both module and script execution
                if __package__ in (None, ""):
                    from pjsua_bot.asr import ASRService
                else:
                    from .asr import ASRService

                acc._asr_service = ASRService()
                acc._asr_available = bool(
                    acc._asr_service and acc._asr_service.available
                )
                if acc._asr_available:
                    print("***ASR: service initialized and ready")
                else:
                    load_err = getattr(acc._asr_service, "_load_error", "unknown error")
                    print(f"***ASR: unavailable - {load_err}")
            except Exception as e:
                print(f"***ASR init error: {e}")
                acc._asr_available = False

        # Initialize intent classifier before registration (if enabled)
        if args.enable_intent:
            print("***Intent: initializing classifier before registration...")
            try:
                # Support both module and script execution
                if __package__ in (None, ""):
                    from pjsua_bot.intent.classifier import RuleBasedClassifier
                    from pjsua_bot.intent.faq_config import FAQS
                    from pjsua_bot.intent.ollama_classifier import OllamaClassifier
                else:
                    from .intent.classifier import RuleBasedClassifier
                    from .intent.faq_config import FAQS
                    from .intent.ollama_classifier import OllamaClassifier

                # Load custom FAQ config if provided, otherwise use default
                faqs = FAQS
                if args.faq_config and os.path.exists(args.faq_config):
                    import json

                    with open(args.faq_config, "r", encoding="utf-8") as f:
                        faqs = json.load(f)
                    print(f"***Intent: loaded custom FAQ config from {args.faq_config}")
                else:
                    if args.faq_config:
                        print(
                            f"***Intent: warning: FAQ config file not found: "
                            f"{args.faq_config}, using default"
                        )

                # Create classifier instance based on selected type
                if args.intent_classifier == "ollama":
                    print(
                        f"***Intent: using Ollama classifier "
                        f"(model: {args.ollama_model})"
                    )
                    acc._intent_classifier = OllamaClassifier(
                        ollama_url=args.ollama_url,
                        model=args.ollama_model,
                        faqs=faqs,
                        use_cpu=getattr(args, "ollama_use_cpu", False),
                    )
                    if getattr(args, "ollama_use_cpu", False):
                        print(
                            "***Intent: CPU mode requested. "
                            "Note: Set OLLAMA_NUM_GPU=0 before starting "
                            "Ollama server for true CPU mode"
                        )
                    print(
                        f"***Intent: Ollama classifier initialized at {args.ollama_url}"
                    )
                else:
                    print("***Intent: using rule-based classifier")
                    acc._intent_classifier = RuleBasedClassifier(faqs=faqs)

                acc.enable_intent = True
                print("***Intent: classifier initialized and ready")
            except Exception as e:
                print(f"***Intent init error: {e}")
                acc._intent_classifier = None
                acc.enable_intent = False

        # Wait for registration with active event pumping
        print(f"***Waiting for registration (up to {args.wait_seconds}s)...")

        def _is_registered() -> bool:
            info: Any = acc.getInfo()
            try:
                return bool(
                    getattr(info, "regIsActive", False)
                    and getattr(info, "regStatus", 0) == 200
                )
            except Exception:
                return False

        registered = wait_until(ep, _is_registered, args.wait_seconds)
        if not registered:
            info: Any = acc.getInfo()
            active = getattr(info, "regIsActive", False)
            status = getattr(info, "regStatus", "unknown")
            print(
                f"***Warning: not registered (active={active} code={status}). "
                "Continuing..."
            )

        # Do not send registration events individually; only send one record at call end

        # Outbound call (optional)
        if args.dest:
            dest_uri = (
                args.dest
                if args.dest.startswith("sip:")
                else f"sip:{args.dest}@{args.domain}"
            )
            call = OutCall(acc)
            prm = pj.CallOpParam(True)
            print(f"***Dialing: {dest_uri}")

            # Collect outbound call attempt
            call._collect_event(
                event_type="outbound_call",
                call_state="dialing",
                remote_uri=dest_uri,
                local_uri=f"sip:{args.user}@{args.domain}",
            )

            call.makeCall(dest_uri, prm)

            # Wait for connection or timeout
            connected = wait_until(
                ep,
                lambda: call.connected,
                max(args.wait_seconds, 10),
            )
            if not connected:
                print("***Warning: call not connected within timeout")

            # Optional auto-hangup after connected
            if call.connected and args.hangup_seconds > 0:
                print(f"***Connected. Auto-hangup in {args.hangup_seconds}s")
                deadline = time.time() + args.hangup_seconds
                while time.time() < deadline and not stopping["flag"]:
                    pump_events(ep, 50)
                try:
                    call.hangup(pj.CallOpParam())
                except Exception:
                    pass

            # Ensure we process teardown
            end_deadline = time.time() + 3
            while time.time() < end_deadline:
                pump_events(ep, 50)

        # Stay online to receive calls (proper loop; no dead sleep)
        if args.stay_online and not stopping["flag"]:
            print("***Online: waiting for incoming calls (Ctrl+C to exit)")
            while not stopping["flag"]:
                pump_events(ep, 50)

                # Check for calls that should be hung up
                for call in list(acc.calls.values()):
                    if hasattr(call, "check_playback_status"):
                        call.check_playback_status()

                    if hasattr(call, "should_hangup") and call.should_hangup():
                        try:
                            if call.isActive():
                                print("***Auto-hanging up after welcome message")
                                # Hangup will trigger onCallState(DISCONNECTED)
                                # which handles cleanup
                                op = pj.CallOpParam()
                                call.hangup(op)
                        except Exception as e:
                            print(f"***Hangup error: {e}")

    finally:
        stopping["cleanup_done"] = False
        # Graceful shutdown: hang up active calls and pump events briefly
        try:
            if "acc" in locals() and isinstance(acc, Account):
                try:
                    # Unregister account FIRST before any other cleanup
                    try:
                        print("***Unregistering account...")
                        acc.setRegistration(False)  # Unregister
                        # Pump events to allow unregistration to complete
                        end_by = time.time() + 2.0
                        while time.time() < end_by and "ep" in locals():
                            try:
                                ep.libHandleEvents(50)
                            except Exception:
                                break
                    except Exception as e:
                        print(f"***Account unregistration error: {e}")

                    # Stop all ASR threads from all calls FIRST
                    print("***Stopping all ASR worker threads...")
                    calls_copy = dict(getattr(acc, "calls", {}))
                    for _call_id, call in calls_copy.items():
                        try:
                            # Stop ASR thread if it exists
                            if hasattr(call, "_stop_asr_thread"):
                                try:
                                    call._stop_asr_thread()
                                except Exception as e:
                                    print(f"***ASR: Error stopping thread: {e}")
                        except Exception:
                            pass

                    # Force stop any remaining ASR threads that didn't stop
                    for thread in threading.enumerate():
                        if thread.name == "ASRWorker" and thread.is_alive():
                            print(f"***ASR: Force stopping thread {thread.name}")
                            # Thread is daemon, but we'll wait a bit more
                            thread.join(timeout=1.0)

                    # Attempt to hang up all active calls
                    # Make a copy of the calls dict to avoid iteration issues
                    for _call_id, call in calls_copy.items():
                        try:
                            # Check if call is active; handle errors gracefully.
                            try:
                                is_active = (
                                    hasattr(call, "isActive") and call.isActive()
                                )
                            except Exception:
                                # Call might be destroyed, skip it
                                is_active = False

                            if is_active:
                                try:
                                    op = pj.CallOpParam()
                                    call.hangup(op)
                                except Exception:
                                    pass

                            # Drop strong refs to players/recorders to help teardown
                            for attr in (
                                "_player",
                                "_goodbye_player",
                                "_recorder",
                                "_outgoing_recorder",
                                "_recording_call_media",
                                "_outgoing_recording_call_media",
                            ):
                                if hasattr(call, attr):
                                    try:
                                        setattr(call, attr, None)
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                    # Clear the calls dict to help with cleanup
                    try:
                        acc.calls.clear()
                    except Exception:
                        pass
                except Exception:
                    pass

                # Pump events for a short period to let teardown complete
                end_by = time.time() + 1.0
                # Use a local alias to avoid shadowing the global name
                try:
                    from .utils import (
                        pump_events as _pump_events,  # local import to avoid cycle
                    )
                except Exception:

                    def _pump_events(ep: pj.Endpoint, ms_per_iter: int = 50) -> None:
                        try:
                            ep.libHandleEvents(ms_per_iter)
                        except Exception:
                            pass

                while time.time() < end_by and "ep" in locals():
                    try:
                        _pump_events(ep, 50)
                    except Exception:
                        break

                # Clean up resources (ASR, intent classifier, Elasticsearch, etc.)
                try:
                    cleanup_resources(acc)
                except Exception as e:
                    print(f"***Resource cleanup error: {e}")

                # Account cleanup - PJSUA2 will handle account deletion
                # when endpoint is destroyed
                # Just ensure we've unregistered and cleared references
                try:
                    print("***Account cleanup complete")
                    # Pump events to allow any pending operations to complete
                    end_by = time.time() + 0.5
                    while time.time() < end_by and "ep" in locals():
                        try:
                            _pump_events(ep, 50)
                        except Exception:
                            break
                except Exception as e:
                    print(f"***Account cleanup error: {e}")
        except Exception:
            pass

        # Destroy transports explicitly before destroying the endpoint
        try:
            if "ep" in locals():
                print("***Destroying transports...")
                # Get all transports and destroy them
                try:
                    transports = ep.transportEnum()
                    for tp in transports:
                        try:
                            ep.transportClose(tp.id)
                        except Exception:
                            pass
                    # Pump events to allow transport cleanup
                    end_by = time.time() + 0.5
                    while time.time() < end_by:
                        try:
                            ep.libHandleEvents(50)
                        except Exception:
                            break
                except Exception as e:
                    print(f"***Transport destruction error: {e}")
        except Exception:
            pass

        # Destroy endpoint - MUST be called from main thread (PJSUA2 requirement)
        # If it hangs, the force exit mechanism will kill the process after 15 seconds
        try:
            if "ep" in locals():
                print("***Destroying endpoint...")
                # Call directly from main thread - PJSUA2 requires this
                # If it blocks, the force exit timeout will handle it
                ep.libDestroy()
        except Exception as e:
            print(f"***Endpoint destruction error: {e}")

        stopping["cleanup_done"] = True
        print("***Shutdown complete")


if __name__ == "__main__":
    # Make Ctrl+C exit with a clean code path
    try:
        main()
    except KeyboardInterrupt:
        print("\n***Interrupted")
        sys.exit(130)
