# Docker Quick Start - TL;DR

## Prerequisites

✅ Docker Desktop installed and running

## Three Commands to Get Started

### 1. Build

```powershell
.\docker-build.ps1
```

⏱️ Takes 10-20 minutes (one-time)

### 2. Test

```powershell
.\docker-run.ps1 -TestASR
```

Expected output:
```
✓ omnilingual-asr works!
✓ ASR class loaded!
```

### 3. Run

```powershell
.\docker-run.ps1
```

Runs the omnilingual-asr example with your recordings.

---

## Common Commands

### Interactive Shell

```powershell
.\docker-run.ps1 -Shell
```

Inside container:
```bash
python3
>>> from omnilingual_asr import ASR
>>> asr = ASR(device='cpu')
>>> # Use omnilingual-asr here
```

### Run Specific Script

```powershell
.\docker-run.ps1 -Command "examples/omnilingual_asr_example.py"
```

### Use Docker Compose (Service Mode)

```powershell
# Start
docker-compose -f docker-compose.omnilingual.yml up

# Start in background
docker-compose -f docker-compose.omnilingual.yml up -d

# View logs
docker-compose -f docker-compose.omnilingual.yml logs -f

# Stop
docker-compose -f docker-compose.omnilingual.yml down
```

### Rebuild Image

```powershell
# Quick rebuild (uses cache)
.\docker-build.ps1

# Clean rebuild (no cache)
.\docker-build.ps1 -NoCache
```

---

## Troubleshooting

### Docker not running?

1. Open Docker Desktop
2. Wait for green icon in system tray
3. Try again

### Image not found?

```powershell
# Build it first
.\docker-build.ps1
```

### Out of space?

```powershell
# Clean up
docker system prune -a
```

---

## Directory Structure

Your files in Windows are accessible in the container:

| Windows | Container |
|---------|-----------|
| `.\recordings\` | `/app/recordings/` |
| `.\assets\` | `/app/assets/` |
| `.\examples\` | `/app/examples/` |
| `.\src\` | `/app/src/` |

Edit files in Windows → They update in container automatically!

---

## Development Workflow

1. **Edit code** in Windows (Cursor/VSCode)
2. **Restart container** to pick up changes:
   ```powershell
   docker-compose -f docker-compose.omnilingual.yml restart
   ```
3. **Test** your changes:
   ```powershell
   .\docker-run.ps1 -Command "your_script.py"
   ```

---

## Next Steps

After successful build and test:

1. **Review examples:**
   ```powershell
   .\docker-run.ps1
   ```

2. **Integrate into your bot:**
   - Update `src/pjsua_bot/asr.py`
   - Use omnilingual-asr instead of Whisper

3. **Deploy:**
   ```powershell
   docker-compose -f docker-compose.omnilingual.yml up -d
   ```

---

## Complete Documentation

- **Full Docker guide:** `DOCKER_SETUP_GUIDE.md`
- **Compare options:** `OMNILINGUAL_ASR_OPTIONS.md`
- **WSL alternative:** `WSL_SETUP_GUIDE.md`

---

**Ready? Run this:**

```powershell
.\docker-build.ps1
```


