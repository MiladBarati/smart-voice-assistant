# Fixes Applied

## Problems Identified

### Docker Container Issues

1. **Recording Directory Permissions**: Container couldn't write to `./artifacts/recordings` directory
2. **ASR Model Loading Failure**: Model checkpoint couldn't be loaded after download

### VAD WavInfo Iteration Bug

3. **WavInfo Iteration Error**: `'WavInfo' object is not iterable` error in VAD chunk processing

## Fixes Applied

### 1. Docker Compose Configuration (`docker-compose.yml`)
- Added `user: "1000:1000"` to ensure container runs as the correct user
- Added cache volume mount: `./cache:/app/.cache` to persist ASR model downloads

### 2. Permission Fix Script (`scripts/maintenance/fix-permissions.sh`)
- Created script to fix permissions on host directories
- Sets ownership to UID 1000 (voicebot user) for:
  - `./artifacts/recordings`
  - `./logs`
  - `./cache`

### 3. Improved ASR Error Handling (`src/pjsua_bot/asr.py`)
- Added better error diagnostics for checkpoint loading failures
- Provides helpful troubleshooting messages

## Next Steps

### 1. Fix Permissions (Run on Host)
```bash
./scripts/maintenance/fix-permissions.sh
```

Or manually:
```bash
sudo chown -R 1000:1000 ./artifacts/recordings ./logs ./cache
sudo chmod -R 755 ./artifacts/recordings ./logs ./cache
```

### 2. Clear ASR Cache (If Model Still Fails)
If the ASR model still fails to load after restarting:
```bash
sudo rm -rf ./cache/*
sudo chown -R 1000:1000 ./cache
```

### 3. Restart Container
```bash
docker-compose down
docker-compose up -d
```

### 4. Monitor Logs
```bash
docker logs -f sipbot
```

## Expected Behavior After Fixes

- ✅ Recordings should be saved successfully to `./artifacts/recordings/YYYY-MM-DD/call_*/`
- ✅ ASR model should load (may take 1-2 minutes on first run to download)
- ✅ No more "Permission denied" errors
- ✅ Better error messages if ASR model fails

## Troubleshooting

### If recordings still fail:
1. Check directory exists: `ls -la ./artifacts/recordings`
2. Verify permissions: `ls -ld ./artifacts/recordings` (should show owner 1000)
3. Check container user: `docker exec sipbot id` (should show uid=1000)

### If ASR model still fails:
1. Check cache directory: `ls -la ./cache`
2. Verify cache permissions: `ls -ld ./cache` (should show owner 1000)
3. Clear cache and restart (see step 2 above)
4. Check available disk space: `df -h`

## VAD WavInfo Iteration Bug Fix

### Problem
The `ChunkManager._save_chunk_audio_manual()` method attempted to iterate over a `WavInfo` dataclass and unpack it as a tuple, causing `'WavInfo' object is not iterable` errors during VAD processing.

### Root Cause
- `WavInfo` is a dataclass (not iterable) defined in `src/pjsua_bot/vad/audio_reader.py`
- Code incorrectly tried: `if any(x is None for x in info):` (iteration)
- Code incorrectly tried: `n_channels, sampwidth, framerate, data_offset = cast(Tuple[int, int, int, int], info)` (tuple unpacking)

### Fix Applied (`src/pjsua_bot/vad/chunk_manager.py`)
- Removed iteration attempt
- Replaced tuple unpacking with direct attribute access:
  ```python
  n_channels = info.channels
  sampwidth = info.sampwidth
  framerate = info.framerate
  data_offset = info.data_offset
  ```

### Impact
- ✅ Resolves `'WavInfo' object is not iterable` errors
- ✅ VAD chunk processing works correctly with manual WAV parsing
- ✅ No functional changes, only corrects dataclass usage

### Files Modified
- `src/pjsua_bot/vad/chunk_manager.py` (lines 270-276)

