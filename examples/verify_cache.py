#!/usr/bin/env python3
"""Verify cache directories and environment variables."""

import os

print("=" * 70)
print("CACHE VERIFICATION")
print("=" * 70)

# Check environment variables
print("\n📌 Environment Variables:")
env_vars = [
    "HF_HOME",
    "HUGGINGFACE_HUB_CACHE",
    "TRANSFORMERS_CACHE",
    "TORCH_HOME",
    "FAIRSEQ2_CACHE",
]

for var in env_vars:
    value = os.environ.get(var, "NOT SET")
    print(f"  {var}: {value}")

# Check if directories exist
print("\n📁 Cache Directories:")
cache_paths = [
    "/app/.cache",
    "/app/.cache/huggingface",
    "/app/.cache/huggingface/hub",
    "/app/.cache/huggingface/transformers",
    "/app/.cache/torch",
    "/app/.cache/fairseq2",
]

for path in cache_paths:
    exists = os.path.exists(path)
    writable = os.access(path, os.W_OK) if exists else False
    status = "✓ EXISTS" if exists else "✗ MISSING"
    write_status = " (writable)" if writable else " (not writable)" if exists else ""
    print(f"  {status}{write_status}: {path}")

# Check what's in the cache
print("\n💾 Cache Contents:")
cache_root = "/app/.cache"
if os.path.exists(cache_root):
    try:
        total_size = 0
        file_count = 0
        for root, _dirs, files in os.walk(cache_root):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except Exception:
                    pass

        size_mb = total_size / (1024 * 1024)
        size_gb = total_size / (1024 * 1024 * 1024)

        print(f"  Files: {file_count}")
        print(f"  Total size: {size_mb:.2f} MB ({size_gb:.2f} GB)")

        if file_count == 0:
            print("  ⚠️  Cache is empty - models not downloaded yet")
        else:
            print("  ✓ Cache contains data")
    except Exception as e:
        print(f"  Error reading cache: {e}")
else:
    print("  ✗ Cache directory doesn't exist!")

print("\n" + "=" * 70)
print("To download models, run: python3 test_omnilingual.py")
print("=" * 70)
