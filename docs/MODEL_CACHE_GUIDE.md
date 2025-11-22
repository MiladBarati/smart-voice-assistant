# Model Cache Persistence Guide

## Problem Solved ✅

**Before:** Models downloaded every time the container runs  
**After:** Models cached on your Windows filesystem and reused

## How It Works

### Cache Directory Structure

```
D:\Amin Raay\pjsua installation\
├── .cache/                          ← New directory (persistent)
│   └── huggingface/                 ← HuggingFace models cache
│       ├── hub/                     ← Downloaded models
│       └── transformers/            ← Tokenizers, configs, etc.
├── recordings/
├── src/
└── ...
```

### What Gets Cached

When you use omnilingual-asr, it downloads:
- **Models** (~1-2GB for omniASR_CTC_1B)
-.Tokenizers
- **Configuration files**
- **Model metadata**

All of this goes to `.cache/huggingface/` inside the container, which is now **mounted from your Windows directory**.

## Usage

### First Run (Downloads Models)

```powershell
# First run - will download models
.\docker-run.ps1 -TestASR
```

**Output:**
```
Loading ASR pipeline (omniASR_CTC_1B)...
This will download the model on first run (~1-2GB)
Downloading model... ⏳ (takes 5-10 minutes)
[OK] ASR pipeline loaded successfully
```

**After first run:** Models are in `D:\Amin Raay\pjsua installation\.cache\`

### Subsequent Runs (Uses Cache)

```powershell
# Second and later runs - instant!
.\docker-run.ps1 -TestASR
```

**Output:**
```
Loading ASR pipeline (omniASR_CTC_1B)...
[OK] ASR pipeline loaded successfully  ⚡ (instant!)
```

No downloads! Uses cached models.

## Cache Location

### On Windows (Host)
```
D:\Amin Raay\pjsua installation\.cache\
```

### In Docker (Container)
```
/app/.cache/
```

They're the **same directory** (mounted volume).

## Checking Cache

### See What's Cached

```powershell
# Windows PowerShell
ls .cache\huggingface\hub\

# Or in Docker shell
.\docker-run.ps1 -Shell
ls -lh /app/.cache/huggingface/hub/
```

### Check Cache Size

```powershell
# Windows PowerShell
Get-ChildItem .cache -Recurse | Measure-Object -Property Length -Sum | Select-Object @{Name="SizeGB";Expression={[math]::Round($_.Sum / 1GB, 2)}}

# Or in Docker shell
du -sh /app/.cache/
```

## Managing Cache

### Clear Cache (Free Up Space)

```powershell
# Delete all cached models
Remove-Item .cache\huggingface\hub\* -Recurse -Force

# Next run will re-download
```

### Clear Specific Model

```powershell
# List models
ls .cache\huggingface\hub\

# Delete specific model
Remove-Item ".cache\huggingface\hub\models--<model-name>" -Recurse -Force
```

### Exclude from Git

The `.cache/` directory is already in `.gitignore`, so cached models won't be committed to your repository.

## Docker Compose

If using docker-compose, the cache is also mounted:

```yaml
volumes:
  - ./.cache:/app/.cache  # ✅ Cache persists
```

```powershell
# Use with compose
docker-compose -f docker-compose.omnilingual.yml up
```

## Benefits

### 1. **Faster Iterations** ⚡
- First run: ~5-10 minutes (download)
- Subsequent runs: Instant (cached)

### 2. **Offline Work** 📡
- Once downloaded, works without internet
- Great for development on the go

### 3. **Multiple Containers** 🔄
- All containers share the same cache
- Download once, use everywhere

### 4. **Easy Backup** 💾
- Cache is on Windows filesystem
- Back up `.cache/` to save models

## File Structure

```
.cache/
└── huggingface/
    ├── hub/
    │   ├── models--facebook--seamless-m4t-v2-large/
    │   ├── models--vhdm--whisper-large-fa-v1/
    │   └── models--omnilingual--omniASR_CTC_1B/
    ├── transformers/
    │   └── [tokenizers and configs]
    └── datasets/
        └── [cached datasets if used]
```

## Troubleshooting

### Issue: Models Still Re-downloading

**Check mount:**
```powershell
# Verify cache directory exists
Test-Path .cache
```

**Rebuild if needed:**
```powershell
# Recreate container with new mount
.\docker-run.ps1 -Shell
```

### Issue: Permission Errors

**Fix permissions:**
```powershell
# Windows - no action needed (uses your user)

# Linux/Mac (if applicable)
chmod -R 777 .cache/
```

### Issue: Corrupted Cache

**Clear and re-download:**
```powershell
Remove-Item .cache\huggingface\hub\* -Recurse -Force
.\docker-run.ps1 -TestASR  # Re-downloads clean
```

## Best Practices

### 1. **First-Time Setup**
Run test script once to download models:
```powershell
.\docker-run.ps1 -TestASR
```

### 2. **Regular Development**
Models are cached, no extra steps needed!

### 3. **Switching Models**
Different models cache separately:
```python
# Each model downloads once
pipeline1 = ASRInferencePipeline(model_card="omniASR_CTC_1B")
pipeline2 = ASRInferencePipeline(model_card="omniASR_CTC_350M")
```

### 4. **Disk Space Management**
Monitor cache size periodically:
```powershell
du -sh .cache/  # In Docker
# Or
Get-ChildItem .cache -Recurse | Measure-Object -Property Length -Sum
```

## Summary

✅ **Cache mounted** from Windows to Docker  
✅ **Models persist** between container runs  
✅ **No re-downloads** after first run  
✅ **Faster development** workflow  
✅ **Works offline** after initial download  

**Location:** `.cache/` in your project directory  
**Size:** ~1-2GB per model  
**Lifetime:** Until manually deleted  

## Quick Reference

| Task | Command |
|------|---------|
| **Check cache** | `ls .cache\huggingface\hub\` |
| **Check size** | `du -sh .cache/` |
| **Clear cache** | `Remove-Item .cache\huggingface\* -Recurse` |
| **Run with cache** | `.\docker-run.ps1 -Shell` |
| **Test** | `.\docker-run.ps1 -TestASR` |

---

**Your models are now cached! First run will download, subsequent runs will be instant.** 🚀


