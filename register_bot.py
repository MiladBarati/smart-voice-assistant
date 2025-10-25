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
from elasticsearch_client import es_logger

import uuid


# ---------- Helpers ----------

def generate_unique_id() -> str:
    """Generate a unique call ID."""
    return str(uuid.uuid4())

def _parse_sip_user(uri: str) -> str:
    """Extract user/extension from a SIP URI or display-formatted URI.
    Examples:
      'sip:1001@host' -> '1001'
      '"Alice" <sip:1002@host>' -> '1002'
    """
    if not uri:
        return ""
    try:
        s = uri
        if '<' in s and '>' in s:
            s = s[s.find('<')+1:s.find('>')]
        if s.startswith('sip:'):
            s = s[4:]
        if '@' in s:
            s = s.split('@', 1)[0]
        # strip quotes and whitespace
        return s.strip().strip('"')
    except Exception:
        return uri

def setup_logging(log_level: int = 3) -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Set PJSUA2 log level
    pj_logger = logging.getLogger('pjsua2')
    pj_logger.setLevel(logging.INFO)

def get_wav_duration(file_path: str) -> float:
    """Get the duration of a WAV file in seconds."""
    try:
        if not os.path.exists(file_path):
            print(f"***Warning: File {file_path} not found, using default duration")
            return 5.0  # Default fallback
        
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            duration = frames / float(sample_rate)
            print(f"***WAV file duration: {duration:.2f} seconds")
            return duration
    except Exception as e:
        print(f"***Error reading WAV file duration: {e}, using default duration")
        return 5.0  # Default fallback

def pump_events(ep: pj.Endpoint, ms_per_iter: int = 50) -> None:
    """Pump the PJSUA2 event loop once."""
    try:
        ep.libHandleEvents(ms_per_iter)
    except Exception as e:
        print(f"***EventLoop error: {e}")


def wait_until(ep: pj.Endpoint, predicate, timeout_s: float) -> bool:
    """Pump events until predicate() is True or timeout (in seconds) elapses."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        pump_events(ep, 50)
        if predicate():
            return True
    return False


# ---------- PJSUA2 classes ----------

class Account(pj.Account):
    def __init__(self):
        super().__init__()
        self.auto_answer = False
        self.calls = {}  # keep strong refs to live calls
        self.play_file = None  # optional WAV file to play on connect
        # Batch logging - collect events during account lifetime
        self._collected_events = []

    def _collect_event(self, event_type: str, **kwargs):
        """Collect an event for batch logging."""
        event = {
            "event_type": event_type,
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "call_id": generate_unique_id(),
            **kwargs
        }
        self._collected_events.append(event)

    def onRegState(self, prm):
        print(f"***OnRegState: {prm.reason}")
        info = self.getInfo()
        print(f"***RegStatus: active={info.regIsActive} code={info.regStatus}")
        
        # Collect registration event
        event_type = "registration_success" if (info.regIsActive and info.regStatus == 200) else "registration_failed"
        self._collect_event(
            event_type=event_type,
            user=getattr(self, 'username', 'unknown'),
            domain=getattr(self, 'domain', 'unknown'),
            status=prm.reason,
            code=info.regStatus,
            active=info.regIsActive,
            reason=prm.reason
        )
        
        if info.regIsActive and info.regStatus == 200:
            print("***Registered successfully")

    def onIncomingCall(self, prm):
        print("***IncomingCall: ringing")
        try:
            call = AnyCall(self, prm.callId)
            self.calls[prm.callId] = call  # <-- keep it!
            
            # Collect incoming call event
            self._collect_event(
                event_type="incoming_call",
                call_id=str(prm.callId),
                call_state="ringing",
                auto_answer=self.auto_answer
            )
            
            op = pj.CallOpParam()
            if self.auto_answer:
                op.statusCode = 200
                call.answer(op)
                print("***IncomingCall: auto-answered 200 OK")
                
                # Collect call answered event
                self._collect_event(
                    event_type="call_answered",
                    call_id=str(prm.callId),
                    call_state="answered",
                    call_code=200
                )
            else:
                op.statusCode = 180
                call.answer(op)
                print("***IncomingCall: sent 180 Ringing")
                
                # Collect call ringing event
                self._collect_event(
                    event_type="call_ringing",
                    call_id=str(prm.callId),
                    call_state="ringing",
                    call_code=180
                )
        except Exception as e:
            print(f"***IncomingCall error: {e}")
            # Collect error event
            self._collect_event(
                event_type="call_error",
                call_id=str(prm.callId),
                call_state="error",
                error=str(e)
            )


class OutCall(pj.Call):
    def __init__(self, acc: pj.Account):
        super().__init__(acc)
        self.connected = False
        self._acc_ref = acc
        self._player = None
        # Batch logging - collect events during call
        self._collected_events = []

    def _collect_event(self, event_type: str, **kwargs):
        """Collect an event for batch logging at the end of the call."""
        event = {
            "event_type": event_type,
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "call_id": str(self.getId()) if hasattr(self, 'getId') else "unknown",
            **kwargs
        }
        self._collected_events.append(event)

    def onCallState(self, prm):
        ci = self.getInfo()
        print(f"***CallState: state={ci.stateText} code={ci.lastStatusCode}")
        
        # Collect call state change event
        self._collect_event(
            event_type="call_state_change",
            call_state=ci.stateText,
            call_code=ci.lastStatusCode,
            state=ci.state,
            state_text=ci.stateText,
            last_status_code=ci.lastStatusCode
        )
        
        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            self.connected = True
        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.connected = False
            
            # drop player reference so it can be cleaned up
            self._player = None

    def onCallMediaState(self, prm):
        ci = self.getInfo()
        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                try:
                    # Collect media active event
                    self._collect_event(
                        event_type="media_active",
                        media_type="audio",
                        media_status="active"
                    )
                    
                    call_media = self.getAudioMedia(mi.index)
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    # If a play file is configured, play it to the remote side
                    if getattr(self._acc_ref, "play_file", None):
                        try:
                            self._player = pj.AudioMediaPlayer()
                            # Create player with loop=False to play only once
                            self._player.createPlayer(self._acc_ref.play_file, False)
                            self._player.startTransmit(call_media)  # file -> remote
                            call_media.startTransmit(playback)      # remote -> local speakers (monitor)
                            print(f"***Media: playing file to remote: {self._acc_ref.play_file}")
                            
                            # Collect playback started event
                            self._collect_event(
                                event_type="playback_started",
                                media_type="audio",
                                file_played=self._acc_ref.play_file
                            )
                        except Exception as e:
                            print(f"***Media player error: {e}")
                            # Collect media error event
                            self._collect_event(
                                event_type="media_error",
                                media_type="audio",
                                error=str(e)
                            )
                    else:
                        capture = adm.getCaptureDevMedia()
                        # Bridge call <-> sound device
                        call_media.startTransmit(playback)   # remote -> speakers
                        capture.startTransmit(call_media)     # mic -> remote
                        print("***Media: audio bridged to sound device")
                        
                        # Collect audio bridge event
                        self._collect_event(
                            event_type="audio_bridged",
                            media_type="audio",
                            media_status="bridged"
                        )
                except Exception as e:
                    print(f"***Media error: {e}")
                    # Collect media error event
                    self._collect_event(
                        event_type="media_error",
                        media_type="audio",
                        error=str(e)
                    )


class AnyCall(pj.Call):
    def __init__(self, acc: pj.Account, call_id: int):
        super().__init__(acc, call_id)
        self._acc_ref = acc  # keep backref for settings
        self.unique_call_id = generate_unique_id()
        self._player = None
        self._playback_started = False
        self._playback_finished = False
        self._hangup_time = None
        self._stop_player_time = None
        self._call_media = None
        # Call record tracking
        self._start_time_utc = None
        self._end_time_utc = None
        self._direction = None  # inbound/outbound
        self._caller_number = None
        self._callee_ext = None
        # Batch logging - collect events during call
        self._collected_events = []

    def _collect_event(self, event_type: str, **kwargs):
        """Collect an event for batch logging at the end of the call."""
        event = {
            "event_type": event_type,
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "call_id": str(self.getId()) if hasattr(self, 'getId') else "unknown",
            **kwargs
        }
        self._collected_events.append(event)

    def onCallState(self, prm):
        ci = self.getInfo()
        print(f"***CallState: state={ci.stateText} code={ci.lastStatusCode}")
        
        # Collect call state change event
        self._collect_event(
            event_type="call_state_change",
            call_state=ci.stateText,
            call_code=ci.lastStatusCode,
            state=ci.state,
            state_text=ci.stateText,
            last_status_code=ci.lastStatusCode
        )
        
        # Mark start when early state observed
        if self._start_time_utc is None and ci.connectDuration.sec == 0:
            self._start_time_utc = datetime.utcnow()

        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED and self._start_time_utc is None:
            self._start_time_utc = datetime.utcnow()

        # Fill caller/callee and direction from call info
        try:
            remote_uri = ci.remoteUri
            local_uri = ci.localUri
            self._caller_number = _parse_sip_user(remote_uri)
            self._callee_ext = _parse_sip_user(local_uri)
            # If this account auto-answers incoming -> inbound
            self._direction = "inbound"
        except Exception:
            pass

        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            # Build call record and send as a single log
            try:
                self._end_time_utc = datetime.utcnow()
                start_iso = self._start_time_utc.isoformat() + "Z" if self._start_time_utc else None
                end_iso = self._end_time_utc.isoformat() + "Z"
                duration_sec = None
                if self._start_time_utc:
                    duration_sec = int((self._end_time_utc - self._start_time_utc).total_seconds())

                call_record = {
                    "event_type": "call_record",
                    "call_id": generate_unique_id(),
                    "caller_number": self._caller_number,
                    "callee_ext": self._callee_ext,
                    "start_time": start_iso,
                    "end_time": end_iso,
                    "duration_sec": duration_sec,
                    "status": "disconnected",
                    "direction": self._direction or "inbound",
                    "media": {
                        "file_played": getattr(self._acc_ref, 'play_file', None),
                        "playback_started": self._playback_started,
                        "playback_finished": self._playback_finished
                    },
                    "bot": {
                        "auto_answer": getattr(self._acc_ref, 'auto_answer', False),
                        "domain": getattr(self._acc_ref, 'domain', None),
                        "user": getattr(self._acc_ref, 'username', None)
                    },
                    "host": socket.gethostname(),
                    "ingest_ts": datetime.utcnow().isoformat() + "Z"
                }
                es_logger.log_call_record(call_record)
                
            except Exception as e:
                print(f"***Error sending single call record: {e}")
            
            # cleanup: drop strong reference so GC can collect safely now
            try:
                del self._acc_ref.calls[ci.id]   # id is the call-id index in pjsua2
            except Exception:
                # some bindings use self.getId() or store the key from onIncomingCall
                # safe fallback: clear everything if unknown
                self._acc_ref.calls = {k:v for k,v in self._acc_ref.calls.items() if v is not self}
            # also release any active player
            self._player = None

    def onCallMediaState(self, prm):
        ci = self.getInfo()
        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                try:
                    call_media = self.getAudioMedia(mi.index)
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    # If a play file is configured, play it to the remote side
                    if getattr(self._acc_ref, "play_file", None):
                        try:
                            self._player = pj.AudioMediaPlayer()
                            # Create player with loop=False to play only once
                            self._player.createPlayer(self._acc_ref.play_file, False)
                            self._player.startTransmit(call_media)  # file -> remote
                            call_media.startTransmit(playback)      # remote -> local speakers (monitor)
                            print(f"***Media: playing file to remote: {self._acc_ref.play_file}")
                            
                            # Mark playback as started and set a timer to stop transmission
                            if not self._playback_started:
                                self._playback_started = True
                                print("***Welcome message playback started")
                                
                                # Collect playback started event
                                self._collect_event(
                                    event_type="playback_started",
                                    media_type="audio",
                                    file_played=self._acc_ref.play_file
                                )
                                
                                # Set a timer to stop the player transmission after actual duration
                                message_duration = getattr(self._acc_ref, 'message_duration', 5)
                                self._stop_player_time = time.time() + message_duration
                                print(f"***Will stop player after {message_duration:.2f} seconds")
                                # Store the call media for later use
                                self._call_media = call_media
                        except Exception as e:
                            print(f"***Media player error: {e}")
                    else:
                        capture = adm.getCaptureDevMedia()
                        call_media.startTransmit(playback)
                        capture.startTransmit(call_media)
                        print("***Media: audio bridged to sound device")
                except Exception as e:
                    print(f"***Media error: {e}")
    
    def check_playback_status(self):
        """Check if playback has finished and set hangup time if needed."""
        if not self._playback_started or self._playback_finished:
            return
            
        current_time = time.time()
        
        # Check if it's time to stop the player transmission
        if self._stop_player_time and current_time >= self._stop_player_time:
            if self._player and self._call_media:
                try:
                    # Stop the transmission from player to call media
                    self._player.stopTransmit(self._call_media)
                    print("***Stopped player transmission to prevent looping")
                    
                    # Also stop the call media to playback transmission to break the audio path
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    self._call_media.stopTransmit(playback)
                    print("***Stopped call media to playback transmission")
                    
                    # Destroy the player completely
                    self._player = None
                    print("***Destroyed player")
                    
                except Exception as e:
                    print(f"***Error stopping player transmission: {e}")
            
            # Set hangup time
            if not self._hangup_time:
                hangup_delay = getattr(self._acc_ref, 'hangup_delay', 2)
                self._hangup_time = time.time() + hangup_delay
                print(f"***Welcome message finished. Will hang up in {hangup_delay} seconds")
                
                # Collect playback finished event
                self._collect_event(
                    event_type="playback_finished",
                    media_type="audio",
                    file_played=getattr(self._acc_ref, 'play_file', None)
                )
                
                self._playback_finished = True
    
    def _set_hangup_time(self):
        """Set the time when the call should be hung up (2 seconds after playback finishes)."""
        hangup_delay = getattr(self._acc_ref, 'hangup_delay', 2)
        self._hangup_time = time.time() + hangup_delay
        print(f"***Welcome message finished. Will hang up in {hangup_delay} seconds")
    
    def should_hangup(self):
        """Check if it's time to hang up the call."""
        if self._hangup_time and time.time() >= self._hangup_time:
            return True
        return False


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
    parser.add_argument("--hangup-delay", type=int, default=2, help="Seconds to wait after welcome message before hanging up (default: 2)")
    parser.add_argument("--message-duration", type=int, default=5, help="Fallback duration in seconds if WAV file cannot be read (default: 5)")
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
    ep = pj.Endpoint()

    # Graceful shutdown on SIGINT/SIGTERM
    stopping = {"flag": False}

    def _stop_handler(signum, frame):
        print(f"***Signal {signum}: stopping...")
        stopping["flag"] = True

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    try:
        ep.libCreate()
        ep.libInit(ep_cfg)

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

        # Start the library
        ep.libStart()

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
        acc.hangup_delay = args.hangup_delay
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