"""Example usage of ASR service for transcribing audio files.

This example demonstrates how to use the ASR service to transcribe
audio recordings, including VAD chunks and complete call recordings.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure 'src' is on sys.path to import the package-style layout
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pjsua_bot.asr import ASRConfig, ASRService, TranscriptionResult


def transcribe_single_file(audio_path: str) -> Optional[TranscriptionResult]:
    """Transcribe a single audio file."""
    print(f"\n=== Transcribing {audio_path} ===")

    # Create ASR service with default configuration
    asr = ASRService()

    if not asr.available:
        print(f"ASR service not available: {asr._load_error}")
        return None

    # Transcribe audio
    result = asr.transcribe(audio_path)

    if result:
        print(f"Transcription: {result.text}")
        print(f"Language: {result.language}")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Processing time: {result.processing_time:.2f}s")
        return result
    else:
        print("Transcription failed")
        return None


def transcribe_vad_chunks(
    chunks_dir: str,
) -> Optional[list[TranscriptionResult]]:
    """Transcribe all VAD chunks in a directory."""
    print(f"\n=== Transcribing VAD chunks from {chunks_dir} ===")

    # Create ASR service
    asr = ASRService()

    if not asr.available:
        print(f"ASR service not available: {asr._load_error}")
        return None

    # Find all WAV files in the directory
    chunk_files = sorted(Path(chunks_dir).glob("*.wav"))

    if not chunk_files:
        print(f"No WAV files found in {chunks_dir}")
        return None

    print(f"Found {len(chunk_files)} chunk files")

    # Transcribe each chunk
    results: list[TranscriptionResult] = []
    for i, chunk_file in enumerate(chunk_files, 1):
        print(f"\nProcessing chunk {i}/{len(chunk_files)}: {chunk_file.name}")
        result = asr.transcribe(str(chunk_file))

        if result:
            results.append(result)
            print(f"  Text: {result.text[:100]}...")  # Print first 100 chars
            print(f"  Duration: {result.duration:.2f}s")
        else:
            print(f"  Failed to transcribe {chunk_file.name}")

    # Print summary
    print("\n=== Summary ===")
    print(f"Successfully transcribed: {len(results)}/{len(chunk_files)} chunks")

    if results:
        full_text = " ".join([r.text for r in results])
        total_duration = sum(r.duration for r in results)
        total_processing_time = sum(r.processing_time for r in results)

        print("\nFull transcription:")
        print(f"{full_text}")
        print(f"\nTotal audio duration: {total_duration:.2f}s")
        print(f"Total processing time: {total_processing_time:.2f}s")

    return results


def transcribe_with_custom_config(
    audio_path: str,
) -> Optional[TranscriptionResult]:
    """Transcribe with custom ASR configuration."""
    print("\n=== Transcribing with custom config ===")

    # Create custom configuration
    config = ASRConfig(
        model_name="vhdm/whisper-large-fa-v1",  # Persian/Farsi model
        device="auto",  # Use GPU if available
        language="fa",  # Persian/Farsi
        task="transcribe",  # Transcribe (not translate)
        max_retries=5,  # More retries
        retry_delay=2.0,  # Longer delay between retries
    )

    # Create ASR service with custom config
    asr = ASRService(config=config)

    if not asr.available:
        print(f"ASR service not available: {asr._load_error}")
        return None

    # Get model info
    info = asr.get_model_info()
    print(f"Model info: {info}")

    # Transcribe
    result = asr.transcribe(audio_path)

    if result:
        print(f"Transcription: {result.text}")
        return result
    else:
        print("Transcription failed")
        return None


if __name__ == "__main__":
    # Example 1: Transcribe a single audio file
    # Replace with path to your audio file
    audio_file = "recordings/2025-11-01/call_20251101_174059_1001/incoming.wav"

    if os.path.exists(audio_file):
        transcribe_single_file(audio_file)
    else:
        print(f"Audio file not found: {audio_file}")
        print("Please update the audio_file path in this script")

    # Example 2: Transcribe VAD chunks
    # Replace with path to your chunks directory
    chunks_directory = "recordings/2025-11-01/call_20251101_174059_1001/"

    if os.path.exists(chunks_directory):
        transcribe_vad_chunks(chunks_directory)
    else:
        print(f"Chunks directory not found: {chunks_directory}")
        print("Please update the chunks_directory path in this script")

    # Example 3: Transcribe with custom configuration
    if os.path.exists(audio_file):
        transcribe_with_custom_config(audio_file)
