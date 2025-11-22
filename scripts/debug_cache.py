#!/usr/bin/env python3
"""Debug script to find where omnilingual-asr caches models."""

import os
import subprocess

print("=" * 70)
print("CACHE LOCATION DEBUG")
print("=" * 70)
print()

# Check environment variables
print("Environment Variables:")
env_vars = [
    "HOME",
    "HF_HOME",
    "HUGGINGFACE_HUB_CACHE",
    "TRANSFORMERS_CACHE",
    "TORCH_HOME",
    "FAIRSEQ2_CACHE",
    "XDG_CACHE_HOME",
]

for var in env_vars:
    value = os.environ.get(var, "NOT SET")
    print(f"  {var}: {value}")

print()

# Try to import omnilingual-asr and check its cache location
print("Checking omnilingual-asr cache locations...")
try:
    # Import check (not used directly, just to verify availability)
    from omnilingual_asr.models.inference.pipeline import (
        ASRInferencePipeline,  # noqa: F401
    )

    # Check fairseq2 asset directory
    try:
        import fairseq2

        version = (
            fairseq2.__version__ if hasattr(fairseq2, "__version__") else "unknown"
        )
        print(f"  fairseq2 version: {version}")
    except Exception:
        pass

    # Try to get cache directory from fairseq2
    try:
        from fairseq2.assets import (
            get_asset_store,  # type: ignore[import-untyped,attr-defined,unused-ignore]
        )

        store = get_asset_store()
        print(f"  fairseq2 asset store: {store}")
    except Exception as e:
        print(f"  Could not get fairseq2 asset store: {e}")

    print()
    print("Testing model download location...")
    print("  Creating pipeline (this will download if not cached)...")
    print("  Watch where files are being written...")

except ImportError as e:
    print(f"  Could not import omnilingual-asr: {e}")

print()

# Find all .cache directories
print("Searching for cache directories in /app and $HOME...")

for base in ["/app", os.environ.get("HOME", "/root")]:
    print(f"\nSearching in {base}:")
    try:
        result = subprocess.run(
            [
                "find",
                base,
                "-type",
                "d",
                "-name",
                ".cache",
                "-o",
                "-name",
                "hub",
                "-o",
                "-name",
                "fairseq2",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout:
            print(result.stdout)
        else:
            print("  No cache directories found")
    except Exception as e:
        print(f"  Error: {e}")

print()
print("=" * 70)
print("To find where models are downloaded, run:")
cmd = (
    "  strace -e trace=open,openat python3 test_omnilingual.py 2>&1 | "
    "grep -E '(models|cache|hub)' | head -20"
)
print(cmd)
print("=" * 70)
