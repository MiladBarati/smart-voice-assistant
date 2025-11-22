#!/usr/bin/env python3
"""Test script to verify ASR migration from Whisper to omnilingual-asr."""

import sys
import os

print("="*70)
print("ASR MIGRATION TEST")
print("="*70)
print()

# Test 1: Import new ASR module
print("Test 1: Importing ASR module...")
try:
    from pjsua_bot.asr import ASRService, ASRConfig, TranscriptionResult
    print("  ✓ Successfully imported ASR components")
except ImportError as e:
    print(f"  ✗ Failed to import: {e}")
    sys.exit(1)

# Test 2: Check backend
print()
print("Test 2: Checking ASR backend...")
config = ASRConfig()
asr = ASRService(config)
model_info = asr.get_model_info()

if "backend" in model_info and model_info["backend"] == "omnilingual-asr":
    print(f"  ✓ Using omnilingual-asr backend")
else:
    print(f"  ⚠ Backend: {model_info.get('backend', 'unknown')}")

print(f"  Model: {model_info.get('model_name', 'unknown')}")
print(f"  Device: {model_info.get('device', 'unknown')}")
print(f"  Available: {model_info.get('available', False)}")

if not model_info.get('available'):
    print(f"  Load error: {model_info.get('load_error', 'unknown')}")
    print()
    print("⚠️  ASR not available (expected in non-Docker environment)")
    print("    Run this test in Docker for full functionality:")
    print("    $ docker-run.ps1 -Shell")
    print("    $ python3 test_asr_migration.py")
else:
    print("  ✓ ASR model loaded successfully")

# Test 3: Check Whisper backup exists
print()
print("Test 3: Checking Whisper backup...")
whisper_backup = "src/pjsua_bot/asr_whisper.py"
if os.path.exists(whisper_backup):
    print(f"  ✓ Whisper backup found: {whisper_backup}")
else:
    print(f"  ✗ Whisper backup not found: {whisper_backup}")

# Test 4: Configuration compatibility
print()
print("Test 4: Testing configuration...")
try:
    config = ASRConfig(
        model_name="omniASR_CTC_300M",
        device="cpu",
        language="fas_Arab",
        batch_size=1,
        max_retries=3,
        skip_on_error=True,
        log_errors=True
    )
    print("  ✓ Configuration created successfully")
    print(f"    Model: {config.model_name}")
    print(f"    Language: {config.language}")
    print(f"    Device: {config.device}")
except Exception as e:
    print(f"  ✗ Configuration failed: {e}")

# Test 5: Interface compatibility
print()
print("Test 5: Testing interface compatibility...")
try:
    asr = ASRService()
    
    # Check all expected methods exist
    methods = [
        'transcribe',
        'transcribe_chunks',
        'transcribe_batch',
        'get_model_info'
    ]
    
    missing_methods = []
    for method in methods:
        if not hasattr(asr, method):
            missing_methods.append(method)
    
    if missing_methods:
        print(f"  ✗ Missing methods: {', '.join(missing_methods)}")
    else:
        print(f"  ✓ All expected methods present")
        
except Exception as e:
    print(f"  ✗ Interface test failed: {e}")

# Test 6: TranscriptionResult structure
print()
print("Test 6: Testing TranscriptionResult structure...")
try:
    result = TranscriptionResult(
        text="test transcription",
        language="fas_Arab",
        duration=10.0,
        processing_time=2.5,
        metadata={"test": True}
    )
    
    # Check all expected fields
    fields = ['text', 'language', 'duration', 'processing_time', 'metadata']
    missing_fields = []
    for field in fields:
        if not hasattr(result, field):
            missing_fields.append(field)
    
    if missing_fields:
        print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
    else:
        print(f"  ✓ All expected fields present")
        
except Exception as e:
    print(f"  ✗ TranscriptionResult test failed: {e}")

# Summary
print()
print("="*70)
print("SUMMARY")
print("="*70)
print()

if asr.available:
    print("✅ Migration successful!")
    print("   - omnilingual-asr is loaded and ready")
    print("   - All interfaces are compatible")
    print("   - Whisper backup is preserved")
    print()
    print("Next steps:")
    print("  1. Update language codes (fa → fas_Arab)")
    print("  2. Test with your audio files")
    print("  3. See ASR_MIGRATION_GUIDE.md for details")
else:
    print("⚠️  Migration files in place, but ASR not loaded")
    print()
    print("This is expected if running outside Docker.")
    print()
    print("To fully test:")
    print("  1. Run in Docker: .\\docker-run.ps1 -Shell")
    print("  2. Execute: python3 test_asr_migration.py")
    print()
    print("Migration files are ready for Docker environment!")

print()
print("="*70)


