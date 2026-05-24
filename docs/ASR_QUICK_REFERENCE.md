# ASR Quick Reference Card

## ✅ Migration Complete!

Your ASR module now uses **omnilingual-asr** instead of Whisper.

---

## 🚀 Quick Test

```powershell
.\docker-run.ps1 -Shell
python3 test_asr_migration.py
```

---

## 💻 Basic Usage (No Changes Needed!)

```python
from pjsua_bot.asr import ASRService

# Use exactly as before
asr = ASRService()
if asr.available:
    result = asr.transcribe("audio.wav")
    print(result.text)
```

---

## 🔧 Configuration

### Current (omnilingual-asr)

```python
from pjsua_bot.asr import ASRConfig

config = ASRConfig(
    model_name="omniASR_CTC_1B",  # or "omniASR_CTC_300M"
    language="fas_Arab",           # Farsi/Persian
    device="auto",                 # or "cpu" / "cuda"
    batch_size=1
)
```

### Language Codes Changed

| Old (Whisper) | New (omnilingual) |
|---------------|-------------------|
| `fa` | `fas_Arab` |
| `en` | `eng_Latn` |
| `ar` | `ara_Arab` |
| `tr` | `tur_Latn` |
| `ur` | `urd_Arab` |

---

## 📁 Files

| File | Description |
|------|-------------|
| `src/pjsua_bot/asr.py` | **Active**: omnilingual-asr |
| `src/pjsua_bot/asr_whisper.py` | **Backup**: Whisper (if needed) |
| `ASR_MIGRATION_GUIDE.md` | **Complete guide** |

---

## 🔄 Switch Back to Whisper (If Needed)

```python
# Option 1: In your code
from pjsua_bot.asr_whisper import ASRService

# Option 2: System-wide
# Copy asr_whisper.py → asr.py
```

---

## 🎯 New Features

### Batch Processing

```python
results = asr.transcribe_batch(
    ["file1.wav", "file2.wav", "file3.wav"],
    languages=["fas_Arab", "fas_Arab", "fas_Arab"]
)
```

### RTF Metrics

```
***ASR: Real-Time Factor: 1.45x
```

Means: Takes 1.45 seconds to process 1 second of audio.

---

## 🐛 Troubleshooting

### "omnilingual-asr not available"

**Solution**: Run in Docker:
```powershell
.\docker-run.ps1 -Shell
```

### Models re-downloading

**Solution**: Rebuild Docker with cache:
```powershell
.\docker-build.ps1
```

### Want Whisper back

**Solution**:
```python
from pjsua_bot.asr_whisper import ASRService
```

---

## 📊 Comparison

| Feature | Whisper | omnilingual-asr |
|---------|---------|-----------------|
| Languages | 99 | 100+ |
| Translation | No | Yes |
| Windows | ✅ Yes | Docker only |
| Accuracy | High | High |

---

## 📚 Documentation

- **Complete Guide**: `ASR_MIGRATION_GUIDE.md`
- **Docker Setup**: `DOCKER_SETUP_GUIDE.md`
- **Examples**: `examples/omnilingual_asr_example.py`

---

## ✨ Summary

- ✅ Interface unchanged - your code works as-is
- ✅ Better multilingual support (100+ languages)
- ✅ Whisper backup available (`asr_whisper.py`)
- ✅ Easy to test: `python3 test_asr_migration.py`
- ✅ Easy to rollback if needed

**Your ASR is now powered by omnilingual-asr!** 🎉


