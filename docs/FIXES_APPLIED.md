# Fixes Applied for Docker Container Issues

## Problems Identified

1. **Recording Directory Permissions**: Container couldn't write to `./artifacts/recordings` directory
2. **ASR Model Loading Failure**: Model checkpoint couldn't be loaded after download

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

