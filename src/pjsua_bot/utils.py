"""Utility functions for PJSUA2 bot operations."""

import logging
import os
import shutil
import subprocess
import time
import uuid
import wave
from datetime import datetime
from typing import Callable, Optional

import pjsua2 as pj

logger = logging.getLogger(__name__)


def generate_unique_id() -> str:
    """Generate a unique call ID."""
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
        if "<" in s and ">" in s:
            s = s[s.find("<") + 1 : s.find(">")]
        if s.startswith("sip:"):
            s = s[4:]
        if "@" in s:
            s = s.split("@", 1)[0]
        # strip quotes and whitespace
        return s.strip().strip('"')
    except Exception:
        return uri


def setup_logging(log_level: int = 3) -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )

    # Set PJSUA2 log level
    pj_logger = logging.getLogger("pjsua2")
    pj_logger.setLevel(logging.INFO)


def get_wav_duration(file_path: str) -> float:
    """Get the duration of a WAV file in seconds."""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File {file_path} not found, using default duration")
            return 5.0  # Default fallback

        with wave.open(file_path, "rb") as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            duration = frames / float(sample_rate)
            logger.debug(f"WAV file duration: {duration:.2f} seconds")
            return duration
    except Exception as e:
        logger.error(f"Error reading WAV file duration: {e}, using default duration")
        return 5.0  # Default fallback


def ensure_recording_directory(base_path: str, call_id: Optional[str] = None) -> str:
    """Ensure recording directory exists and return the full path.

    Creates directory structure:
    - If call_id is provided: {base_path}/YYYY-MM-DD/{call_id}/
    - Otherwise: {base_path}/YYYY-MM-DD/

    Args:
        base_path: Base directory for recordings
        call_id: Optional unique call identifier to create a subdirectory for the call

    Returns:
        Full path to the recording directory
    """
    try:
        # Convert to absolute path to avoid relative path issues
        base_path = os.path.abspath(base_path)

        # Ensure base directory exists first
        try:
            os.makedirs(base_path, exist_ok=True)
        except PermissionError as e:
            logger.error(
                f"Permission denied creating base recording directory "
                f"{base_path}: {e}"
            )
            logger.info(
                f"Hint: Ensure the directory exists and is writable by the "
                f"current user (UID {os.getuid()})"
            )
            raise
        except OSError as e:
            logger.error(f"Error creating base recording directory {base_path}: {e}")
            raise

        # Create date-specific subdirectory directly under base_path
        current_date = datetime.now().strftime("%Y-%m-%d")
        date_dir = os.path.join(base_path, current_date)

        # If call_id is provided, create a call-specific subdirectory
        if call_id:
            call_dir = os.path.join(date_dir, call_id)
            try:
                os.makedirs(call_dir, exist_ok=True, mode=0o755)
                logger.debug(f"Recording directory: {call_dir}")
                return call_dir
            except PermissionError as e:
                logger.error(
                    f"Permission denied creating call recording directory "
                    f"{call_dir}: {e}"
                )
                raise
        else:
            try:
                os.makedirs(date_dir, exist_ok=True, mode=0o755)
                logger.debug(f"Recording directory: {date_dir}")
                return date_dir
            except PermissionError as e:
                logger.error(
                    f"Permission denied creating date recording directory "
                    f"{date_dir}: {e}"
                )
                raise
    except PermissionError:
        # Re-raise permission errors as-is
        raise
    except Exception as e:
        logger.error(f"Error creating recording directory: {e}")
        # Fallback to base path if date directory creation fails
        # (but only if it's not a permission error)
        return base_path


def convert_recording_path_to_url(
    local_path: str,
    base_url: Optional[str] = None,
) -> str:
    """Convert a local recording file path to a URL.

    Normalizes common Windows/relative paths and avoids duplicating the
    'recordings' path segment when the base_url already contains it.

    Args:
        local_path: Local file path (can include backslashes, ./ prefix, etc.)
        base_url: Base URL for recordings (defaults to https://recordings.aminraay.ir/recordings)

    Returns:
        URL string with normalized path separators
    """
    if not local_path:
        return ""

    if base_url is None:
        # Load from environment variable or use default
        base_url = os.getenv(
            "RECORDING_BASE_URL", "https://recordings.aminraay.ir/recordings"
        )

    # Normalize the local path
    # Remove ./ prefix if present
    normalized_path = local_path.replace("./", "").lstrip("/")

    # Replace backslashes with forward slashes (for Windows paths)
    normalized_path = normalized_path.replace("\\", "/")

    # Remove leading slashes
    normalized_path = normalized_path.lstrip("/")

    # Remove base URL trailing slash if present
    base_url = base_url.rstrip("/")

    # Remove extra path segments that shouldn't be in the URL:
    # - Remove 'recordings/app/recordings/' if present (common issue)
    # - Remove 'app/recordings/' if present
    # - Remove a single leading 'recordings/' from the path if present,
    #   since base_url typically already points to the recordings root.
    if normalized_path.startswith("recordings/app/recordings/"):
        normalized_path = normalized_path[len("recordings/app/recordings/") :]
    elif normalized_path.startswith("app/recordings/"):
        normalized_path = normalized_path[len("app/recordings/") :]
    elif normalized_path.startswith("recordings/"):
        normalized_path = normalized_path[len("recordings/") :]

    return f"{base_url}/{normalized_path}"


def convert_wav_to_mp3(wav_path: str, delete_source: bool = True) -> Optional[str]:
    """Convert a WAV file to MP3 using ffmpeg if available.

    Returns the path to the generated MP3 on success, or None on failure.
    If delete_source is True and conversion succeeds, the source WAV file is removed.
    """
    if not wav_path or not os.path.exists(wav_path):
        return None

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        logger.warning("Audio convert: ffmpeg not found in PATH; keeping WAV file")
        return None

    base, _ = os.path.splitext(wav_path)
    mp3_path = base + ".mp3"

    try:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            wav_path,
            "-vn",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            mp3_path,
        ]
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        if os.path.exists(mp3_path):
            logger.info(f"Audio convert: created {mp3_path}")
            if delete_source:
                try:
                    os.remove(wav_path)
                    logger.debug(f"Audio convert: removed source WAV {wav_path}")
                except Exception as e:
                    logger.warning(f"Audio convert: failed to remove source WAV: {e}")
            return mp3_path
        else:
            logger.warning("Audio convert: ffmpeg reported success but MP3 not found")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio convert: ffmpeg failed with code {e.returncode}")
        return None
    except Exception as e:
        logger.error(f"Audio convert: unexpected error: {e}")
        return None


def pump_events(ep: pj.Endpoint, ms_per_iter: int = 50) -> None:
    """Pump the PJSUA2 event loop once."""
    try:
        ep.libHandleEvents(ms_per_iter)
    except Exception as e:
        logger.error(f"EventLoop error: {e}")


def wait_until(
    ep: pj.Endpoint,
    predicate: Callable[[], bool],
    timeout_s: float,
) -> bool:
    """Pump events until predicate() is True or timeout (in seconds) elapses."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        pump_events(ep, 50)
        if predicate():
            return True
    return False
