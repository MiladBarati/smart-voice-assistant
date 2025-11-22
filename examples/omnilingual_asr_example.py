"""Example: Using omnilingual-asr for multilingual speech recognition.

This example demonstrates how to use omnilingual-asr with the PJSUA bot
for transcribing audio recordings in multiple languages.

omnilingual-asr features:
- Supports 100+ languages
- Uses SeamlessM4T v2 model from Meta
- Provides language detection
- High accuracy for multilingual content
"""

import os
from pathlib import Path
from typing import Optional

try:
    from omnilingual_asr import ASR

    OMNILINGUAL_AVAILABLE = True
except ImportError:
    print(
        "Warning: omnilingual-asr not available. Install with: uv add omnilingual-asr"
    )
    OMNILINGUAL_AVAILABLE = False


def transcribe_with_omnilingual(
    audio_path: str, source_language: Optional[str] = None, target_language: str = "eng"
) -> Optional[dict]:
    """Transcribe audio using omnilingual-asr.

    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)
        source_language: Source language code (e.g., 'fas' for Farsi/Persian).
                        If None, language will be auto-detected.
        target_language: Target language for transcription (default: 'eng' for English)

    Returns:
        Dictionary with transcription results or None on error

    Language codes (ISO 639-3):
        - 'eng': English
        - 'fas': Farsi/Persian
        - 'ara': Arabic
        - 'spa': Spanish
        - 'fra': French
        - 'deu': German
        - 'tur': Turkish
        - 'urd': Urdu
        - And 100+ more...
    """
    if not OMNILINGUAL_AVAILABLE:
        print("Error: omnilingual-asr is not installed")
        return None

    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found: {audio_path}")
        return None

    try:
        print("Loading omnilingual ASR model...")
        # Initialize ASR model
        # device can be 'cpu' or 'cuda' for GPU
        asr = ASR(device="cpu")  # Change to 'cuda' if you have GPU in WSL

        print(f"Transcribing: {audio_path}")
        if source_language:
            print(f"Source language: {source_language}")
        else:
            print("Language: auto-detect")
        print(f"Target language: {target_language}")

        # Transcribe audio
        result = asr.transcribe(
            audio_path,
            src_lang=source_language,  # None for auto-detection
            tgt_lang=target_language,
        )

        # Result structure:
        # {
        #     'text': 'transcribed text',
        #     'src_lang': 'detected/specified source language',
        #     'tgt_lang': 'target language'
        # }

        return result  # type: ignore[no-any-return]

    except Exception as e:
        print(f"Error during transcription: {e}")
        return None


def transcribe_call_recording(call_dir: str) -> None:
    """Transcribe both incoming and outgoing recordings from a call.

    Args:
        call_dir: Path to call directory
            (e.g., 'recordings/2025-11-15/call_20251115_120000_1001')
    """
    call_path = Path(call_dir)

    if not call_path.exists():
        print(f"Error: Call directory not found: {call_dir}")
        return

    # Find incoming and outgoing WAV files
    incoming_files = list(call_path.glob("*_incoming.wav"))
    outgoing_files = list(call_path.glob("*_outgoing.wav"))

    print(f"\n{'=' * 60}")
    print(f"Processing call: {call_path.name}")
    print(f"{'=' * 60}\n")

    # Transcribe incoming audio (caller)
    if incoming_files:
        print("\n--- Incoming (Caller) ---")
        for audio_file in incoming_files:
            result = transcribe_with_omnilingual(
                str(audio_file),
                source_language="fas",  # Assuming Farsi caller
                target_language="eng",
            )

            if result:
                src_lang = result.get("src_lang", "unknown")
                text = result.get("text", "")
                print(f"\nOriginal ({src_lang}): {text}")
                tgt_lang = result.get("tgt_lang", "eng")
                print(f"Translated to {tgt_lang}: {text}")

    # Transcribe outgoing audio (bot)
    if outgoing_files:
        print("\n--- Outgoing (Bot) ---")
        for audio_file in outgoing_files:
            result = transcribe_with_omnilingual(
                str(audio_file),
                source_language="fas",  # Assuming Farsi bot
                target_language="eng",
            )

            if result:
                src_lang = result.get("src_lang", "unknown")
                text = result.get("text", "")
                print(f"\nOriginal ({src_lang}): {text}")
                tgt_lang = result.get("tgt_lang", "eng")
                print(f"Translated to {tgt_lang}: {text}")

    print(f"\n{'=' * 60}\n")


def batch_transcribe_recordings(recordings_dir: str = "recordings") -> None:
    """Transcribe all recordings in the recordings directory.

    Args:
        recordings_dir: Path to recordings directory
    """
    recordings_path = Path(recordings_dir)

    if not recordings_path.exists():
        print(f"Error: Recordings directory not found: {recordings_dir}")
        return

    # Find all call directories
    call_dirs = [d for d in recordings_path.rglob("call_*") if d.is_dir()]

    print(f"Found {len(call_dirs)} call recordings")

    for i, call_dir in enumerate(call_dirs, 1):
        print(f"\n[{i}/{len(call_dirs)}] Processing: {call_dir.name}")
        transcribe_call_recording(str(call_dir))


def compare_with_whisper(audio_path: str) -> None:
    """Compare omnilingual-asr with Whisper transcription.

    Args:
        audio_path: Path to audio file
    """
    print(f"\n{'=' * 60}")
    print("Comparing ASR Models")
    print(f"{'=' * 60}\n")
    print(f"Audio: {audio_path}\n")

    # Omnilingual ASR
    print("1. omnilingual-asr (SeamlessM4T v2):")
    omnilingual_result = transcribe_with_omnilingual(
        audio_path, source_language="fas", target_language="eng"
    )
    if omnilingual_result:
        print(f"   Text: {omnilingual_result.get('text', '')}\n")

    # Whisper ASR (from existing asr.py)
    print("2. Whisper (vhdm/whisper-large-fa-v1):")
    try:
        from pjsua_bot.asr import ASRConfig, ASRService

        config = ASRConfig(model_name="vhdm/whisper-large-fa-v1", language="fa")
        whisper_asr = ASRService(config)

        if whisper_asr.available:
            whisper_result = whisper_asr.transcribe(audio_path)
            if whisper_result:
                print(f"   Text: {whisper_result.text}\n")
        else:
            print("   Whisper not available\n")
    except Exception as e:
        print(f"   Error: {e}\n")

    print(f"{'=' * 60}\n")


# Example usage
if __name__ == "__main__":
    # Example 1: Transcribe a single audio file
    example_audio = (
        "recordings/2025-11-02/call_20251102_180619_1001/"
        "20251102_180619_1001_incoming.wav"
    )

    if os.path.exists(example_audio):
        print("\n=== Example 1: Single File Transcription ===")
        result = transcribe_with_omnilingual(
            example_audio,
            source_language="fas",  # Farsi/Persian
            target_language="eng",  # English
        )

        if result:
            print(f"\nTranscription: {result.get('text', '')}")
            print(f"Source Language: {result.get('src_lang', 'unknown')}")
            print(f"Target Language: {result.get('tgt_lang', 'unknown')}")

    # Example 2: Transcribe a complete call
    example_call = "recordings/2025-11-02/call_20251102_180619_1001"

    if os.path.exists(example_call):
        print("\n\n=== Example 2: Complete Call Transcription ===")
        transcribe_call_recording(example_call)

    # Example 3: Batch transcribe all recordings
    # Uncomment to run (this will take a long time!)
    # print("\n\n=== Example 3: Batch Transcription ===")
    # batch_transcribe_recordings("recordings")

    # Example 4: Compare models
    if os.path.exists(example_audio):
        print("\n\n=== Example 4: Model Comparison ===")
        compare_with_whisper(example_audio)

    print("\n=== Done! ===\n")
