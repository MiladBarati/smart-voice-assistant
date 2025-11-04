import argparse
import signal
import sys
import time
import wave
import os
import logging
import socket
from datetime import datetime

import pjsua2 as pj

# Support running both as a module and as a script
if __package__ in (None, ""):
    import os
    # Add parent directory (the 'src' root) so absolute imports work when executed directly
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pjsua_bot.utils import setup_logging, get_wav_duration, pump_events, wait_until
    from pjsua_bot.account import Account
    from pjsua_bot.calls import OutCall
    from pjsua_bot.elasticsearch_client import es_logger
else:
    from .utils import setup_logging, get_wav_duration, pump_events, wait_until
    from .account import Account
    from .calls import OutCall
    from .elasticsearch_client import es_logger


# ---------- Main ----------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="PJSUA2 registration/call bot with proper event pumping and options."
    )
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--domain", required=True, help="Registrar/realm host or domain")
    parser.add_argument("--auth-user", default=None)
    parser.add_argument("--local-port", type=int, default=5060)
    parser.add_argument("--wait-seconds", type=int, default=10, help="Time to wait for registration/connect")
    parser.add_argument("--stay-online", action="store_true", help="Keep endpoint running to receive calls")
    parser.add_argument("--auto-answer", action="store_true", help="Answer incoming calls with 200 OK (default: True)")
    parser.add_argument("--no-auto-answer", action="store_true", help="Disable auto-answering of incoming calls")
    parser.add_argument("--dest", default=None, help="Destination SIP URI or extension (sip:1002@host or just 1002)")
    parser.add_argument("--hangup-seconds", type=int, default=0, help="Auto hangup after N seconds of connection; 0 to disable")
    parser.add_argument("--outbound-proxy", default=None, help="Outbound proxy URI, e.g. sip:host:5060;lr")
    parser.add_argument("--transport", choices=["udp", "tcp", "tls"], default="udp", help="SIP transport")
    parser.add_argument("--tls-verify", action="store_true", help="Verify TLS server certificate (when --transport tls)")
    parser.add_argument("--log-level", type=int, default=3, help="Endpoint log level (0-6)")
    parser.add_argument("--play-file", default="welcome_message.wav", help="Path to WAV file to play to remote when call media is active (default: welcome_message.wav)")
    parser.add_argument("--goodbye-file", default="goodbye_voice.wav", help="Path to WAV file to play before hanging up (default: goodbye_voice.wav)")
    parser.add_argument("--hangup-delay", type=int, default=2, help="Deprecated: fixed delay; overridden by VAD-based hangup if enabled")
    parser.add_argument("--message-duration", type=int, default=5, help="Fallback duration in seconds if WAV file cannot be read (default: 5)")
    parser.add_argument("--enable-recording", action="store_true", help="Enable voice capture for incoming calls (default: False)")
    parser.add_argument("--recording-path", default="./recordings", help="Base directory for storing recorded audio files (default: ./recordings)")
    parser.add_argument("--enable-vad", action="store_true", help="Enable Silero VAD-based hangup after caller silence (default: False)")
    parser.add_argument("--silence-after-speech-sec", type=float, default=3.0, help="Seconds of silence after last caller speech to hang up (default: 3.0)")
    parser.add_argument("--vad-threshold", type=float, default=0.5, help="Silero VAD speech probability threshold (default: 0.5)")
    parser.add_argument("--enable-asr", action="store_true", help="Enable Whisper-based ASR for live and final transcription (default: disabled)")
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    
    # Test Elasticsearch connection
    print("***Testing Elasticsearch connection...")
    health = es_logger.health_check()
    if health.get("status") == "connected":
        print(f"***Elasticsearch connected: {health.get('cluster_name', 'unknown')}")
    else:
        print(f"***Elasticsearch connection failed: {health.get('error', 'unknown error')}")

    # Create and initialize the library
    ep_cfg = pj.EpConfig()
    ep_cfg.logConfig.level = args.log_level
    med = ep_cfg.medConfig
    med.clockRate       = 16000
    med.sndClockRate    = 16000
    med.channelCount    = 1
    med.audioFramePtime = 20
    med.ptime           = 20
    med.quality         = 10
    med.noVad           = False        # save bandwidth under loss
    med.ecTailLen       = 512  # Increased from 256
    med.ecOptions       = 1    # Ensure echo cancellation is enabled
    med.jbInit          = 100
    med.jbMinPre        = 80
    med.jbMaxPre        = 300
    med.jbMax           = 500
    ep = pj.Endpoint()
    

    ep.libCreate()
    ep.libInit(ep_cfg)

    # Graceful shutdown on SIGINT/SIGTERM
    stopping = {"flag": False}

    def _stop_handler(signum, frame):
        print(f"***Signal {signum}: stopping...")
        stopping["flag"] = True

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    try:
        
        
        # Codec configuration: PCMU (G.711) is used by default for good quality
        # PJSUA2 by default uses PCMU/PCMA which provides 64kbps @ 8kHz - good quality for VoIP
        print("***Codec: configured for wideband audio (16kHz), preferring Opus/G.722 over G.711")

        # Create SIP transport
        sipTpConfig = pj.TransportConfig()
        sipTpConfig.port = args.local_port
        if args.transport == "udp":
            ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sipTpConfig)
            print(f"***Transport: UDP {args.local_port}")
        elif args.transport == "tcp":
            ep.transportCreate(pj.PJSIP_TRANSPORT_TCP, sipTpConfig)
            print(f"***Transport: TCP {args.local_port}")
        else:
            # TLS
            tls_cfg = pj.TlsConfig()
            tls_cfg.verifyServer = args.tls_verify
            sipTpConfig.tlsConfig = tls_cfg
            ep.transportCreate(pj.PJSIP_TRANSPORT_TLS, sipTpConfig)
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
                ("speex/32000/1", 255),    # Ultra-wideband Speex (32kHz)
                ("speex/16000/1", 250),    # Wideband Speex (16kHz) - good quality
                ("G722/16000/1", 240),     # G.722 wideband (already working)
                ("L16/44100/1", 200),      # Uncompressed (high quality, high bandwidth)
                
                # Narrowband codecs (lower priority - fallbacks)
                ("PCMU/8000/1", 128),      # G.711 μ-law (narrowband)
                ("PCMA/8000/1", 120),       # G.711 A-law (narrowband)
                ("speex/8000/1", 100),      # Speex narrowband (lower than G.711)
                ("GSM/8000/1", 80),         # GSM (lowest priority)
                ("iLBC/8000/1", 70),        # iLBC (lowest priority)
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
                ("GSM/8000/1", 0),          # Disable GSM
                ("iLBC/8000/1", 0),         # Disable iLBC
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
            acfg.sipConfig.keepAliveIntervalSec = 15      # CRLF keepalives
            acfg.natConfig.sipOutbound = 1                # RFC 5626 SIP Outbound
            acfg.natConfig.iceEnabled = True              # Enable ICE for media
        except Exception:
            pass

        # Credentials
        cred = pj.AuthCredInfo("digest", "*", args.auth_user or args.user, 0, args.password)
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
        
        # Get actual duration from the WAV file, or use command line argument as fallback
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

        # Also disable Contact/Via rewrite heuristics that can change the Contact mid-flight
        try:
            acfg.natConfig.contactRewriteUse = pj.PJSUA_CONTACT_REWRITE_USE_DISABLED
            acfg.natConfig.viaRewriteUse     = pj.PJSUA_VIA_REWRITE_USE_DISABLED
        except AttributeError:
            # fallbacks if your binding exposes them as ints
            acfg.natConfig.contactRewriteUse = 0
            acfg.natConfig.viaRewriteUse     = 0

        # Do NOT force using the local source port in Contact
        try:
            acfg.natConfig.contactUseSrcPort = False
        except AttributeError:
            pass
        acc.create(acfg)

        # Wait for registration with active event pumping
        print(f"***Waiting for registration (up to {args.wait_seconds}s)...")
        registered = wait_until(
            ep,
            lambda: (lambda info=acc.getInfo(): info.regIsActive and info.regStatus == 200)(),
            args.wait_seconds,
        )
        if not registered:
            info = acc.getInfo()
            print(f"***Warning: not registered (active={info.regIsActive} code={info.regStatus}). Continuing...")
        
        # Do not send registration events individually; only send one record at call end

        # Outbound call (optional)
        if args.dest:
            dest_uri = args.dest if args.dest.startswith("sip:") else f"sip:{args.dest}@{args.domain}"
            call = OutCall(acc)
            prm = pj.CallOpParam(True)
            print(f"***Dialing: {dest_uri}")
            
            # Collect outbound call attempt
            call._collect_event(
                event_type="outbound_call",
                call_state="dialing",
                remote_uri=dest_uri,
                local_uri=f"sip:{args.user}@{args.domain}"
            )
            
            call.makeCall(dest_uri, prm)

            # Wait for connection or timeout
            connected = wait_until(ep, lambda: call.connected, max(args.wait_seconds, 10))
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
                    if hasattr(call, 'check_playback_status'):
                        call.check_playback_status()
                    
                    if hasattr(call, 'should_hangup') and call.should_hangup():
                        try:
                            if call.isActive():
                                print("***Auto-hanging up after welcome message")
                                # Hangup will trigger onCallState(DISCONNECTED) which handles cleanup
                                op = pj.CallOpParam()
                                call.hangup(op)
                        except Exception as e:
                            print(f"***Hangup error: {e}")

    finally:
        try:
            ep.libDestroy()
        except Exception:
            pass
        print("***Shutdown complete")


if __name__ == "__main__":
    # Make Ctrl+C exit with a clean code path
    try:
        main()
    except KeyboardInterrupt:
        print("\n***Interrupted")
        sys.exit(130)