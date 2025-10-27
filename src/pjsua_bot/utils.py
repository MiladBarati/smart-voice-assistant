"""Utility functions for PJSUA2 bot operations."""

import os
import time
import wave
import logging
from datetime import datetime
import pjsua2 as pj


def generate_unique_id() -> str:
    """Generate a unique call ID."""
    import uuid
    return str(uuid.uuid4())


def parse_sip_user(uri: str) -> str:
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


def ensure_recording_directory(base_path: str) -> str:
    """Ensure recording directory exists and return the full path for current date.
    
    Creates directory structure: {base_path}/YYYY-MM-DD/
    Returns the full path for the current date.
    """
    try:
        # Create date-specific subdirectory directly under base_path
        current_date = datetime.now().strftime("%Y-%m-%d")
        date_dir = os.path.join(base_path, current_date)
        os.makedirs(date_dir, exist_ok=True)
        
        print(f"***Recording directory: {date_dir}")
        return date_dir
    except Exception as e:
        print(f"***Error creating recording directory: {e}")
        # Fallback to base path if date directory creation fails
        return base_path


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

