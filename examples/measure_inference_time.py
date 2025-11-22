#!/usr/bin/env python3
"""
Utility for measuring omnilingual-asr inference time with detailed metrics.

Usage:
    python examples/measure_inference_time.py <audio_file> [language]

Examples:
    python examples/measure_inference_time.py recordings/test.wav
    python examples/measure_inference_time.py recordings/test.wav fas_Arab
"""

import os
import sys
import time
import wave


def measure_inference(
    audio_file: str,
    language: str = "fas_Arab",
    model_card: str = "omniASR_CTC_1B",
    device: str = "cpu",
) -> dict[str, object]:
    """
    Measure inference time for omnilingual-asr transcription.

    Args:
        audio_file: Path to audio file
        language: Language code (e.g., 'fas_Arab' for Farsi)
        model_card: Model to use
        device: 'cpu' or 'cuda'

    Returns:
        dict with timing metrics and transcription
    """
    from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

    results: dict[str, object] = {}

    # 1. Check file exists
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    # 2. Get audio duration
    try:
        with wave.open(audio_file, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            audio_duration = frames / float(rate)
            results["audio_duration_sec"] = audio_duration
            results["sample_rate"] = rate
            results["num_frames"] = frames
    except Exception as e:
        print(f"Warning: Could not read audio duration: {e}")
        results["audio_duration_sec"] = None

    # 3. Load model (measure time)
    print(f"Loading model: {model_card} on {device}...")
    load_start = time.time()
    pipeline = ASRInferencePipeline(model_card=model_card)
    load_time = time.time() - load_start
    results["model_load_time_sec"] = load_time
    print(f"  Model loaded in {load_time:.2f}s")

    # 4. Warm-up inference (first run is often slower)
    print("Running warm-up inference...")
    warmup_start = time.time()
    _ = pipeline.transcribe([audio_file], lang=[language], batch_size=1)
    warmup_time = time.time() - warmup_start
    results["warmup_time_sec"] = warmup_time
    print(f"  Warm-up completed in {warmup_time:.2f}s")

    # 5. Actual inference (measure multiple runs for accuracy)
    num_runs = 3
    print(f"Running {num_runs} inference iterations...")
    inference_times = []

    for i in range(num_runs):
        inference_start = time.time()
        transcriptions = pipeline.transcribe(
            [audio_file], lang=[language], batch_size=1
        )
        inference_time = time.time() - inference_start
        inference_times.append(inference_time)
        print(f"  Run {i + 1}/{num_runs}: {inference_time:.2f}s")

    # Calculate statistics
    avg_inference_time = sum(inference_times) / len(inference_times)
    min_inference_time = min(inference_times)
    max_inference_time = max(inference_times)

    results["inference_time_avg_sec"] = avg_inference_time
    results["inference_time_min_sec"] = min_inference_time
    results["inference_time_max_sec"] = max_inference_time
    results["inference_times_all"] = inference_times
    results["transcription"] = transcriptions[0]

    # 6. Calculate Real-Time Factor (RTF)
    audio_dur = results.get("audio_duration_sec")
    if audio_dur and isinstance(audio_dur, (int, float)):
        rtf = avg_inference_time / float(audio_dur)
        results["rtf"] = rtf
        results["rtf_interpretation"] = (
            f"{rtf:.2f}x speed (takes {rtf:.2f}s to process 1s of audio)"
        )

    return results

    return results


def print_results(results: dict) -> None:
    """Pretty print inference results."""
    print("\n" + "=" * 70)
    print("INFERENCE RESULTS")
    print("=" * 70)

    # Audio info
    if results["audio_duration_sec"]:
        print("\n📊 Audio Information:")
        print(f"  Duration: {results['audio_duration_sec']:.2f} seconds")
        print(f"  Sample rate: {results['sample_rate']} Hz")
        print(f"  Frames: {results['num_frames']:,}")

    # Model loading
    print("\n🔧 Model Loading:")
    print(f"  Load time: {results['model_load_time_sec']:.2f} seconds")
    print(f"  Warm-up time: {results['warmup_time_sec']:.2f} seconds")

    # Inference performance
    print("\n⚡ Inference Performance:")
    print(f"  Average time: {results['inference_time_avg_sec']:.3f} seconds")
    print(f"  Min time: {results['inference_time_min_sec']:.3f} seconds")
    print(f"  Max time: {results['inference_time_max_sec']:.3f} seconds")

    if "rtf" in results:
        print("\n🎯 Real-Time Factor (RTF):")
        print(f"  RTF: {results['rtf']:.2f}x")
        print(f"  {results['rtf_interpretation']}")

        if results["rtf"] < 1.0:
            print("  ✅ Faster than real-time (good for live transcription)")
        elif results["rtf"] < 2.0:
            print("  ⚠️  Slower than real-time (may struggle with live)")
        else:
            print("  ❌ Much slower than real-time (batch only)")

    # Transcription
    print("\n📝 Transcription:")
    text = results["transcription"]
    if len(text) > 200:
        print(f"  {text[:200]}...")
        print(f"  ... ({len(text)} total characters)")
    else:
        print(f"  {text}")

    print("\n" + "=" * 70)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python measure_inference_time.py <audio_file> [language]")
        print("\nExamples:")
        print("  python measure_inference_time.py recordings/test.wav")
        print("  python measure_inference_time.py recordings/test.wav fas_Arab")
        sys.exit(1)

    audio_file = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "fas_Arab"

    print(f"Audio file: {audio_file}")
    print(f"Language: {language}")
    print()

    try:
        results = measure_inference(audio_file, language)
        print_results(results)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
