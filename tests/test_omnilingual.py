#!/usr/bin/env python3
"""Test script for omnilingual-asr in Docker"""

print("Testing omnilingual-asr installation...")
print()

try:
    import omnilingual_asr
    print("[OK] omnilingual-asr imported successfully")
except ImportError as e:
    print(f"[ERROR] Failed to import omnilingual-asr: {e}")
    exit(1)

try:
    from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
    print("[OK] ASRInferencePipeline imported successfully")
except ImportError as e:
    print(f"[ERROR] Failed to import ASRInferencePipeline: {e}")
    exit(1)

try:
    import time
    import os
    
    print()
    print("Loading ASR pipeline (omniASR_CTC_1B)...")
    print("This will download the model on first run (~1-2GB)")
    
    # Measure model loading time
    load_start = time.time()
    pipeline = ASRInferencePipeline(model_card="omniASR_CTC_300M")
    load_time = time.time() - load_start
    
    print(f"[OK] ASR pipeline loaded successfully")
    print(f"    Model load time: {load_time:.2f} seconds")
    
    # Test with an audio file if it exists
    audio_file = "recordings/2025-11-16/call_20251116_160635_1001/chunk_0002_1763309224.mp3"
    if os.path.exists(audio_file):
        print()
        print(f"Testing transcription with {audio_file}...")
        
        # Get audio duration for metrics
        try:
            import wave
            with wave.open(audio_file, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                audio_duration = frames / float(rate)
                print(f"    Audio duration: {audio_duration:.2f} seconds")
        except:
            audio_duration = None
        
        # Measure transcription time
        lang = ["fas_Arab"]  # Farsi/Persian
        
        inference_start = time.time()
        transcriptions = pipeline.transcribe([audio_file], lang=lang, batch_size=1)
        inference_time = time.time() - inference_start
        
        print(f"[OK] Transcription successful!")
        print(f"    Inference time: {inference_time:.2f} seconds")
        
        if audio_duration:
            rtf = inference_time / audio_duration
            print(f"    Real-Time Factor (RTF): {rtf:.2f}x")
            print(f"    ({rtf:.2f}x means it takes {rtf:.2f} seconds to process 1 second of audio)")
        
        print()
        print(f"    Transcription result:")
        result_text = transcriptions[0]
        if len(result_text) > 150:
            print(f"    {result_text[:150]}...")
        else:
            print(f"    {result_text}")
    else:
        print(f"[INFO] Test audio file not found at {audio_file}, skipping transcription test")
        
except Exception as e:
    print(f"[ERROR] Failed to load/test ASR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()
print("SUCCESS! omnilingual-asr is ready to use!")

print()

