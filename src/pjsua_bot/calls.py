"""Call classes for PJSUA2 SIP call handling."""

import os
import time
import socket
from datetime import datetime
import pjsua2 as pj

from .utils import generate_unique_id, parse_sip_user, ensure_recording_directory
from .elasticsearch_client import es_logger


class OutCall(pj.Call):
    """Outbound call handler with media playback support."""
    
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
        """Handle call state changes."""
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
        """Handle call media state changes."""
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
    """Generic call handler with recording and playback capabilities."""
    
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
        # Voice recording infrastructure
        self._recorder = None
        self._recording_file = None
        self._recording_enabled = False
        self._recording_call_media = None
        self._recording_start_time = None  # Track when recording started
        self._recording_duration = 0  # Track recording duration in seconds
        # Outgoing audio recording infrastructure
        self._outgoing_recorder = None
        self._outgoing_recording_file = None
        self._outgoing_recording_call_media = None
        self._outgoing_recording_start_time = None  # Track when outgoing recording started
        self._outgoing_recording_duration = 0  # Track outgoing recording duration in seconds
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
        """Handle call state changes."""
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
            self._caller_number = parse_sip_user(remote_uri)
            self._callee_ext = parse_sip_user(local_uri)
            # If this account auto-answers incoming -> inbound
            self._direction = "inbound"
        except Exception:
            pass

        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            # Clean up recording early to avoid media disconnect issues
            self._cleanup_recording()
            
            # Build call record and send as a single log
            try:
                self._end_time_utc = datetime.utcnow()
                start_iso = self._start_time_utc.isoformat() + "Z" if self._start_time_utc else None
                end_iso = self._end_time_utc.isoformat() + "Z"
                duration_sec = None
                if self._start_time_utc:
                    duration_sec = int((self._end_time_utc - self._start_time_utc).total_seconds())

                # Determine voice capture status and details
                has_incoming_recording = self._recording_file and os.path.exists(self._recording_file)
                has_outgoing_recording = self._outgoing_recording_file and os.path.exists(self._outgoing_recording_file)
                voice_captured = has_incoming_recording or has_outgoing_recording
                
                # Get primary audio file path (prefer incoming, fallback to outgoing)
                audio_file_path = self._recording_file if has_incoming_recording else (self._outgoing_recording_file if has_outgoing_recording else None)
                
                # Calculate total capture duration
                total_capture_duration = 0
                if has_incoming_recording and self._recording_duration:
                    total_capture_duration += self._recording_duration
                if has_outgoing_recording and self._outgoing_recording_duration:
                    total_capture_duration += self._outgoing_recording_duration
                
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
                    "recording": getattr(self, '_recording_metadata', None),
                    "voice_captured": voice_captured,
                    "audio_file_path": audio_file_path,
                    "capture_duration": round(total_capture_duration, 2) if total_capture_duration > 0 else 0,
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
            
            # Cleanup recording
            self._cleanup_recording()
            
            # Add recording metadata to call record
            recording_metadata = {}
            
            # Add incoming recording metadata
            if self._recording_file and os.path.exists(self._recording_file):
                incoming_file_size = os.path.getsize(self._recording_file)
                recording_metadata["incoming"] = {
                    "file_path": self._recording_file,
                    "file_size_bytes": incoming_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "audio_file_path": self._recording_file,
                    "capture_duration": round(self._recording_duration, 2) if self._recording_duration else 0
                }
                
                # Collect incoming recording finished event
                self._collect_event(
                    event_type="recording_finished",
                    media_type="audio",
                    recording_file=self._recording_file,
                    file_size_bytes=incoming_file_size,
                    direction="incoming",
                    capture_duration=round(self._recording_duration, 2) if self._recording_duration else 0
                )
            
            # Add outgoing recording metadata
            if self._outgoing_recording_file and os.path.exists(self._outgoing_recording_file):
                outgoing_file_size = os.path.getsize(self._outgoing_recording_file)
                recording_metadata["outgoing"] = {
                    "file_path": self._outgoing_recording_file,
                    "file_size_bytes": outgoing_file_size,
                    "recorded": True,
                    "voice_captured": True,
                    "audio_file_path": self._outgoing_recording_file,
                    "capture_duration": round(self._outgoing_recording_duration, 2) if self._outgoing_recording_duration else 0
                }
                
                # Collect outgoing recording finished event
                self._collect_event(
                    event_type="outgoing_recording_finished",
                    media_type="audio",
                    recording_file=self._outgoing_recording_file,
                    file_size_bytes=outgoing_file_size,
                    direction="outgoing",
                    capture_duration=round(self._outgoing_recording_duration, 2) if self._outgoing_recording_duration else 0
                )
            
            # Store recording metadata for call record
            if recording_metadata:
                self._recording_metadata = recording_metadata

    def onCallMediaState(self, prm):
        """Handle call media state changes."""
        ci = self.getInfo()
        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                try:
                    call_media = self.getAudioMedia(mi.index)
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    
                    # Voice recording setup (if enabled)
                    if getattr(self._acc_ref, 'enable_recording', False):
                        try:
                            recording_dir = ensure_recording_directory(
                                getattr(self._acc_ref, 'recording_path', './recordings')
                            )
                            # Try to get caller number if still unknown
                            caller_id = self._caller_number or 'unknown'
                            if caller_id == 'unknown':
                                try:
                                    call_info = self.getInfo()
                                    remote_uri = call_info.remoteUri
                                    caller_id = parse_sip_user(remote_uri) or 'unknown'
                                    self._caller_number = caller_id
                                    print(f"***Recording: caller identified as {caller_id}")
                                except Exception as e:
                                    print(f"***Recording: could not parse caller info: {e}")
                            
                            filename = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}_incoming.wav"
                            self._recording_file = os.path.join(recording_dir, filename)
                            
                            # Debug: Check directory and permissions
                            print(f"***Recording: directory exists: {os.path.exists(recording_dir)}")
                            print(f"***Recording: directory writable: {os.access(recording_dir, os.W_OK)}")
                            print(f"***Recording: full file path: {self._recording_file}")
                            
                            # Test: Create a simple test file to verify permissions
                            test_file = os.path.join(recording_dir, "test_permissions.tmp")
                            try:
                                with open(test_file, 'w') as f:
                                    f.write("test")
                                os.remove(test_file)
                                print(f"***Recording: directory permissions OK")
                            except Exception as e:
                                print(f"***Recording: ERROR - directory permission test failed: {e}")
                            
                            self._recorder = pj.AudioMediaRecorder()
                            # Try different encoding options
                            try:
                                # Try with WAV format explicitly
                                self._recorder.createRecorder(self._recording_file, 0, 0)  # 0 = WAV, 0 = no size limit
                                print(f"***Recording: createRecorder succeeded with WAV format")
                            except Exception as e:
                                print(f"***Recording: createRecorder failed: {e}")
                                # Try fallback approach
                                try:
                                    self._recorder.createRecorder(self._recording_file, 0, "")  # Original approach
                                    print(f"***Recording: createRecorder succeeded with fallback")
                                except Exception as e2:
                                    print(f"***Recording: createRecorder failed with fallback: {e2}")
                                    raise e2
                            call_media.startTransmit(self._recorder)  # remote → recorder
                            self._recording_call_media = call_media  # Store reference for cleanup
                            self._recording_start_time = datetime.utcnow()  # Track recording start time
                            print(f"***Recording: started capturing to {self._recording_file}")
                            
                            # Verify recorder was created successfully
                            if self._recorder:
                                print(f"***Recording: AudioMediaRecorder created successfully")
                                # Check if file was created immediately
                                if os.path.exists(self._recording_file):
                                    print(f"***Recording: file created immediately: {self._recording_file}")
                                else:
                                    print(f"***Recording: file not created yet (normal for PJSUA2)")
                            else:
                                print(f"***Recording: ERROR - AudioMediaRecorder creation failed")
                            
                            # Collect recording started event
                            self._collect_event(
                                event_type="recording_started",
                                media_type="audio",
                                recording_file=self._recording_file
                            )
                        except Exception as e:
                            print(f"***Recording setup error: {e}")
                            # Collect recording error event
                            self._collect_event(
                                event_type="recording_error",
                                media_type="audio",
                                error=str(e)
                            )
                    
                    # If a play file is configured, play it to the remote side
                    if getattr(self._acc_ref, "play_file", None):
                        try:
                            self._player = pj.AudioMediaPlayer()
                            # Create player with loop=False to play only once
                            self._player.createPlayer(self._acc_ref.play_file, False)
                            self._player.startTransmit(call_media)  # file -> remote
                            call_media.startTransmit(playback)      # remote -> local speakers (monitor)
                            print(f"***Media: playing file to remote: {self._acc_ref.play_file}")
                            
                            # Record outgoing audio (bot's welcome message) if recording is enabled
                            if getattr(self._acc_ref, 'enable_recording', False):
                                try:
                                    recording_dir = ensure_recording_directory(
                                        getattr(self._acc_ref, 'recording_path', './recordings')
                                    )
                                    # Use the same caller_id that was determined for incoming recording
                                    outgoing_filename = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}_outgoing.wav"
                                    self._outgoing_recording_file = os.path.join(recording_dir, outgoing_filename)
                                    
                                    self._outgoing_recorder = pj.AudioMediaRecorder()
                                    self._outgoing_recorder.createRecorder(self._outgoing_recording_file, 0, 0)
                                    self._player.startTransmit(self._outgoing_recorder)  # player -> outgoing recorder
                                    self._outgoing_recording_call_media = self._player
                                    self._outgoing_recording_start_time = datetime.utcnow()  # Track outgoing recording start time
                                    print(f"***Recording: started capturing outgoing audio to {self._outgoing_recording_file}")
                                    
                                    # Collect outgoing recording started event
                                    self._collect_event(
                                        event_type="outgoing_recording_started",
                                        media_type="audio",
                                        recording_file=self._outgoing_recording_file
                                    )
                                except Exception as e:
                                    print(f"***Outgoing recording setup error: {e}")
                                    self._collect_event(
                                        event_type="outgoing_recording_error",
                                        media_type="audio",
                                        error=str(e)
                                    )
                            
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
    
    def _cleanup_recording(self):
        """Clean up recording resources safely."""
        # Clean up incoming recording
        if self._recorder:
            try:
                # Stop recording transmission using stored reference
                if self._recording_call_media and self._recorder:
                    try:
                        print(f"***Recording: stopping incoming transmission from call media")
                        self._recording_call_media.stopTransmit(self._recorder)
                        print(f"***Recording: incoming transmission stopped successfully")
                    except Exception as e:
                        print(f"***Recording: incoming stopTransmit failed (media may already be disconnected): {e}")
                else:
                    print(f"***Recording: WARNING - no incoming call media reference or recorder for cleanup")
                
                # Destroy the recorder to ensure file is properly closed
                if self._recorder:
                    try:
                        print(f"***Recording: destroying incoming recorder")
                        # Try to destroy the recorder explicitly if the method exists
                        if hasattr(self._recorder, 'destroy'):
                            self._recorder.destroy()
                        self._recorder = None
                        print(f"***Recording: incoming recorder destroyed successfully")
                    except Exception as e:
                        print(f"***Recording: incoming recorder destruction failed: {e}")
                        self._recorder = None
                
                self._recording_call_media = None
                
                # Calculate recording duration
                if self._recording_start_time:
                    self._recording_duration = (datetime.utcnow() - self._recording_start_time).total_seconds()
                    print(f"***Recording: incoming audio captured for {self._recording_duration:.2f} seconds")
                
                print(f"***Recording: incoming audio stopped and saved to {self._recording_file}")
                
                # Check if file actually exists
                if self._recording_file:
                    if os.path.exists(self._recording_file):
                        print(f"***Recording: incoming file confirmed to exist at {self._recording_file}")
                    else:
                        print(f"***Recording: WARNING - incoming file not found at {self._recording_file}")
                        # Wait a moment and check again (PJSUA2 might need time to flush)
                        import time
                        time.sleep(0.5)
                        if os.path.exists(self._recording_file):
                            print(f"***Recording: incoming file found after delay at {self._recording_file}")
                        else:
                            print(f"***Recording: incoming file still not found after delay")
                            
            except Exception as e:
                print(f"***Recording cleanup error: {e}")
                # Collect recording cleanup error event
                self._collect_event(
                    event_type="recording_cleanup_error",
                    media_type="audio",
                    error=str(e)
                )
        
        # Clean up outgoing recording
        if self._outgoing_recorder:
            try:
                # Stop outgoing recording transmission using stored reference
                if self._outgoing_recording_call_media and self._outgoing_recorder:
                    try:
                        print(f"***Recording: stopping outgoing transmission from player")
                        self._outgoing_recording_call_media.stopTransmit(self._outgoing_recorder)
                        print(f"***Recording: outgoing transmission stopped successfully")
                    except Exception as e:
                        print(f"***Recording: outgoing stopTransmit failed (player may already be disconnected): {e}")
                else:
                    print(f"***Recording: WARNING - no outgoing player reference or recorder for cleanup")
                
                # Destroy the outgoing recorder to ensure file is properly closed
                if self._outgoing_recorder:
                    try:
                        print(f"***Recording: destroying outgoing recorder")
                        # Try to destroy the recorder explicitly if the method exists
                        if hasattr(self._outgoing_recorder, 'destroy'):
                            self._outgoing_recorder.destroy()
                        self._outgoing_recorder = None
                        print(f"***Recording: outgoing recorder destroyed successfully")
                    except Exception as e:
                        print(f"***Recording: outgoing recorder destruction failed: {e}")
                        self._outgoing_recorder = None
                
                self._outgoing_recording_call_media = None
                
                # Calculate outgoing recording duration
                if self._outgoing_recording_start_time:
                    self._outgoing_recording_duration = (datetime.utcnow() - self._outgoing_recording_start_time).total_seconds()
                    print(f"***Recording: outgoing audio captured for {self._outgoing_recording_duration:.2f} seconds")
                
                print(f"***Recording: outgoing audio stopped and saved to {self._outgoing_recording_file}")
                
                # Check if outgoing file actually exists
                if self._outgoing_recording_file:
                    if os.path.exists(self._outgoing_recording_file):
                        print(f"***Recording: outgoing file confirmed to exist at {self._outgoing_recording_file}")
                    else:
                        print(f"***Recording: WARNING - outgoing file not found at {self._outgoing_recording_file}")
                        # Wait a moment and check again (PJSUA2 might need time to flush)
                        import time
                        time.sleep(0.5)
                        if os.path.exists(self._outgoing_recording_file):
                            print(f"***Recording: outgoing file found after delay at {self._outgoing_recording_file}")
                        else:
                            print(f"***Recording: outgoing file still not found after delay")
                            
            except Exception as e:
                print(f"***Outgoing recording cleanup error: {e}")
                # Collect outgoing recording cleanup error event
                self._collect_event(
                    event_type="outgoing_recording_cleanup_error",
                    media_type="audio",
                    error=str(e)
                )

