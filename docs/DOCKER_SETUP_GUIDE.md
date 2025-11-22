# Docker Setup Guide for omnilingual-asr

## Why Docker? ✨

Docker solves **all** the environment problems:

| Issue | WSL Solution | Docker Solution |
|-------|-------------|-----------------|
| Windows compatibility | Need WSL2 | ✅ Native Docker for Windows |
| Environment conflicts | Separate .venv | ✅ Isolated container |
| Setup complexity | Manual installation | ✅ One-command build |
| Portability | WSL-only | ✅ Run anywhere |
| Reproducibility | Manual steps | ✅ Automated via Dockerfile |

## Prerequisites

1. **Docker Desktop** installed on Windows
   - Download: https://www.docker.com/products/docker-desktop/
   - Make sure it's running (system tray icon)

2. **(Optional) GPU Support**
   - For CUDA acceleration: Install NVIDIA Container Toolkit
   - Not required - CPU works fine for most use cases

## Quick Start (3 Commands)

### Step 1: Build the Docker Image

```powershell
.\docker-build.ps1
```

**Time:** 10-20 minutes on first build (downloads and compiles everything)

### Step 2: Test omnilingual-asr

```powershell
.\docker-run.ps1 -TestASR
```

**Output:**
```
✓ omnilingual-asr works!
✓ ASR class loaded!
```

### Step 3: Run Examples

```powershell
.\docker-run.ps1
```

This runs the omnilingual-asr example with your recordings.

## Detailed Usage

### Building the Image

**Basic build:**
```powershell
.\docker-build.ps1
```

**Build without cache (clean build):**
```powershell
.\docker-build.ps1 -NoCache
```

**Build with verbose output:**
```powershell
.\docker-build.ps1 -Verbose
```

**Custom tag:**
```powershell
.\docker-build.ps1 -Tag "mybot:v1.0"
```

### Running the Container

**Run omnilingual-asr example:**
```powershell
.\docker-run.ps1
```

**Test installation:**
```powershell
.\docker-run.ps1 -TestASR
```

**Interactive shell:**
```powershell
.\docker-run.ps1 -Shell
```

**Run custom Python script:**
```powershell
.\docker-run.ps1 -Command "examples/omnilingual_asr_example.py"
```

**Run with specific image:**
```powershell
.\docker-run.ps1 -Image "mybot:v1.0"
```

### Using Docker Compose (Recommended for Services)

**Start the service:**
```powershell
docker-compose -f docker-compose.omnilingual.yml up
```

**Start in background:**
```powershell
docker-compose -f docker-compose.omnilingual.yml up -d
```

**View logs:**
```powershell
docker-compose -f docker-compose.omnilingual.yml logs -f
```

**Stop the service:**
```powershell
docker-compose -f docker-compose.omnilingual.yml down
```

**Rebuild and restart:**
```powershell
docker-compose -f docker-compose.omnilingual.yml up --build
```

## What's Inside the Container?

The Docker image includes:

✅ **Ubuntu Linux** (latest stable)  
✅ **Python 3.12**  
✅ **PJSUA2** (compiled from source)  
✅ **PyTorch** + **torchaudio**  
✅ **transformers** (Hugging Face)  
✅ **omnilingual-asr** ⭐  
✅ **All project dependencies**  
✅ **Your application code**

## Directory Structure

```
Container filesystem:
/app/
  ├── src/                    ← Your bot code
  ├── examples/               ← Example scripts
  ├── recordings/             ← Mounted from host
  ├── assets/                 ← Mounted from host
  ├── logs/                   ← Application logs
  └── .cache/huggingface/     ← Model cache (persistent)
```

**Mounted volumes** (shared with Windows):
- `./recordings` ↔ `/app/recordings` (call recordings)
- `./assets` ↔ `/app/assets` (audio files)
- `./examples` ↔ `/app/examples` (example scripts)
- Model cache is persistent in Docker volume

## Common Tasks

### Task 1: Transcribe Your Recordings

```powershell
# Run the example (auto-detects recordings)
.\docker-run.ps1
```

### Task 2: Interactive Python Session

```powershell
# Start shell
.\docker-run.ps1 -Shell

# Inside container:
python3
>>> from omnilingual_asr import ASR
>>> asr = ASR(device='cpu')
>>> result = asr.transcribe('recordings/test.wav', src_lang='fas', tgt_lang='eng')
>>> print(result['text'])
```

### Task 3: Run Your Bot

**Method 1: Docker run**
```powershell
docker run --rm -it `
  -v ${PWD}/recordings:/app/recordings `
  -p 5060:5060/udp `
  pjsua-bot-omnilingual:latest `
  python3 -m pjsua_bot.register_bot --enable-asr
```

**Method 2: Docker Compose**
```powershell
docker-compose -f docker-compose.omnilingual.yml up
```

### Task 4: Test Specific Audio File

```powershell
.\docker-run.ps1 -Shell

# Inside container:
python3 -c "
from omnilingual_asr import ASR
asr = ASR(device='cpu')
result = asr.transcribe('recordings/2025-11-02/call_20251102_180619_1001/20251102_180619_1001_incoming.wav', src_lang='fas', tgt_lang='eng')
print(result)
"
```

### Task 5: Update Code Without Rebuilding

Edit your code in Windows, then:

```powershell
# Source code is mounted, just restart
docker-compose -f docker-compose.omnilingual.yml restart
```

## GPU Support (Optional)

To use NVIDIA GPU for faster transcription:

1. **Install NVIDIA Container Toolkit:**
   - https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

2. **Uncomment GPU sections in `docker-compose.omnilingual.yml`:**
   ```yaml
   environment:
     - NVIDIA_VISIBLE_DEVICES=all
   
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

3. **Run:**
   ```powershell
   docker-compose -f docker-compose.omnilingual.yml up
   ```

4. **Verify GPU inside container:**
   ```bash
   nvidia-smi
   python3 -c "import torch; print(torch.cuda.is_available())"
   ```

## Troubleshooting

### Issue: "Docker is not running"

**Solution:**
- Open Docker Desktop
- Wait for it to fully start (green icon in system tray)

### Issue: Build fails with network errors

**Solution:**
```powershell
# Retry build
.\docker-build.ps1
```

### Issue: Container can't access recordings

**Solution:**
```powershell
# Make sure you're in the project directory
cd "D:\Amin Raay\pjsua installation"

# Check volume mounts
docker run --rm -v ${PWD}/recordings:/app/recordings pjsua-bot-omnilingual:latest ls -la /app/recordings
```

### Issue: Out of disk space

**Solution:**
```powershell
# Clean up old images and containers
docker system prune -a

# Remove unused volumes
docker volume prune
```

### Issue: Build is very slow

**Solution:**
- First build takes 10-20 minutes (normal)
- Subsequent builds are much faster (uses cache)
- Make sure Docker Desktop has enough resources:
  - Settings → Resources → Advanced
  - Increase CPUs and Memory if needed

### Issue: "omnilingual_asr not found"

**Solution:**
```powershell
# Rebuild without cache
.\docker-build.ps1 -NoCache
```

## Advantages Over WSL

| Feature | WSL | Docker |
|---------|-----|--------|
| Setup time | 30+ minutes | 10-20 minutes (automated) |
| Isolation | Shared with WSL | Fully isolated |
| Portability | WSL only | Any Docker host |
| GPU support | Complex | Simple (if toolkit installed) |
| Updates | Manual | Rebuild image |
| Cleanup | Manual | `docker system prune` |
| Production ready | Partial | ✅ Yes |

## Development Workflow

### Option 1: Edit in Windows, Run in Docker (Recommended)

1. **Edit files** in Windows using Cursor/VSCode
2. **No rebuild needed** (code is mounted)
3. **Restart container** to pick up changes:
   ```powershell
   docker-compose -f docker-compose.omnilingual.yml restart
   ```

### Option 2: Interactive Development

```powershell
# Start shell
.\docker-run.ps1 -Shell

# Inside container, edit and test
python3 examples/omnilingual_asr_example.py
```

### Option 3: Full Rebuild (For Dependency Changes)

```powershell
# After changing pyproject.toml or requirements
.\docker-build.ps1 -NoCache
```

## Production Deployment

### Build Production Image

```powershell
.\docker-build.ps1 -Tag "pjsua-bot:production"
```

### Push to Registry

```powershell
# Tag for your registry
docker tag pjsua-bot:production myregistry.com/pjsua-bot:latest

# Push
docker push myregistry.com/pjsua-bot:latest
```

### Deploy

```bash
# On production server
docker pull myregistry.com/pjsua-bot:latest
docker-compose up -d
```

## Files Created

| File | Purpose |
|------|---------|
| `Dockerfile.omnilingual` | Docker image definition with omnilingual-asr |
| `docker-compose.omnilingual.yml` | Service orchestration |
| `docker-build.ps1` | Build script for PowerShell |
| `docker-run.ps1` | Run script for PowerShell |
| `DOCKER_SETUP_GUIDE.md` | This file |

## Next Steps

1. **Build the image:**
   ```powershell
   .\docker-build.ps1
   ```

2. **Test it works:**
   ```powershell
   .\docker-run.ps1 -TestASR
   ```

3. **Run examples:**
   ```powershell
   .\docker-run.ps1
   ```

4. **Integrate into your bot:**
   - Update `src/pjsua_bot/asr.py` to use omnilingual-asr
   - Test with docker-compose
   - Deploy to production

## Summary

✅ **No WSL required**  
✅ **One-command setup**  
✅ **Fully isolated environment**  
✅ **Production ready**  
✅ **GPU support available**  
✅ **Works on Windows, Linux, macOS**  

**Ready to start?**

```powershell
.\docker-build.ps1
```


