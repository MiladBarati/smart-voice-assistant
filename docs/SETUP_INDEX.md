# Setup Documentation Index

## 🎯 Start Here

**Want to use omnilingual-asr on Windows?**

👉 **Read this first:** `OMNILINGUAL_ASR_SUMMARY.md`

Then choose your solution and follow the corresponding guide.

---

## 📚 Documentation Structure

```
OMNILINGUAL_ASR_SUMMARY.md          ← START HERE! Complete overview
│
├── OMNILINGUAL_ASR_OPTIONS.md      ← Compare all options (Docker/WSL/Windows)
│
├── 🐳 Docker Solution (RECOMMENDED)
│   ├── DOCKER_QUICK_START.md       ← 3 commands to get started
│   └── DOCKER_SETUP_GUIDE.md       ← Complete Docker guide
│
├── 🐧 WSL Solution
│   ├── WSL_QUICK_START.md          ← Quick command reference
│   ├── WSL_SETUP_GUIDE.md          ← Complete WSL guide
│   └── DUAL_ENVIRONMENT_GUIDE.md   ← Managing Windows + WSL
│
└── 📖 Additional Resources
    ├── OMNILINGUAL_ASR_SETUP.md    ← Original overview
    └── examples/omnilingual_asr_example.py  ← Code examples
```

---

## 🚀 Quick Links by Goal

### "I just want to get omnilingual-asr working NOW"

→ **Docker Quick Start:** `DOCKER_QUICK_START.md`

```powershell
.\docker-build.ps1
.\docker-run.ps1 -TestASR
```

---

### "I want to understand my options first"

→ **Options Comparison:** `OMNILINGUAL_ASR_OPTIONS.md`

Compares Docker vs WSL vs Windows with pros/cons.

---

### "I want to use Docker"

→ **Docker Setup Guide:** `DOCKER_SETUP_GUIDE.md`

Complete guide with:
- Building images
- Running containers
- docker-compose usage
- GPU support
- Production deployment
- Troubleshooting

---

### "I want to use WSL"

→ **WSL Setup Guide:** `WSL_SETUP_GUIDE.md`

Complete guide with:
- WSL installation
- Python setup
- Dependency installation
- Running the bot
- Troubleshooting

---

### "How do I manage both Windows and WSL?"

→ **Dual Environment Guide:** `DUAL_ENVIRONMENT_GUIDE.md`

Explains:
- Why they're separate
- How to switch between them
- Best practices
- Virtual environment management

---

### "Show me example code"

→ **Example Script:** `examples/omnilingual_asr_example.py`

Includes:
- Basic transcription
- Batch processing
- Language detection
- Model comparison

---

## 📋 Decision Tree

```
Do you want omnilingual-asr?
│
├─ YES → Choose environment
│   │
│   ├─ I want easiest setup
│   │  └─ Use Docker → DOCKER_SETUP_GUIDE.md
│   │
│   ├─ I prefer native Linux
│   │  └─ Use WSL → WSL_SETUP_GUIDE.md
│   │
│   └─ Not sure which?
│      └─ Read → OMNILINGUAL_ASR_OPTIONS.md
│
└─ NO → Keep Windows environment
    └─ Run → setup_windows.ps1
```

---

## 🎓 Recommended Reading Order

### If You're New to This:

1. **OMNILINGUAL_ASR_SUMMARY.md** - Understand what was created
2. **OMNILINGUAL_ASR_OPTIONS.md** - Compare your choices
3. **DOCKER_QUICK_START.md** - Try Docker (easiest)
4. **DOCKER_SETUP_GUIDE.md** - If you want more details

### If You're Experienced:

1. **DOCKER_QUICK_START.md** - Just the commands
2. **examples/omnilingual_asr_example.py** - See the code
3. Done!

---

## 📂 File Reference

### Setup Scripts

| File | Purpose | Platform |
|------|---------|----------|
| `scripts/maintenance/setup_wsl.sh` | Automated WSL setup | WSL/Linux |
| `setup_windows.ps1` | Windows environment | Windows |
| `docker-build.ps1` | Build Docker image | Windows |
| `docker-run.ps1` | Run Docker container | Windows |

### Docker Files

| File | Purpose |
|------|---------|
| `Dockerfile.omnilingual` | Image definition |
| `docker-compose.omnilingual.yml` | Service config |

### Documentation

| File | Content |
|------|---------|
| `OMNILINGUAL_ASR_SUMMARY.md` | Complete overview |
| `OMNILINGUAL_ASR_OPTIONS.md` | Option comparison |
| `OMNILINGUAL_ASR_SETUP.md` | Original setup doc |
| `DOCKER_SETUP_GUIDE.md` | Docker complete guide |
| `DOCKER_QUICK_START.md` | Docker quick ref |
| `WSL_SETUP_GUIDE.md` | WSL complete guide |
| `WSL_QUICK_START.md` | WSL quick ref |
| `DUAL_ENVIRONMENT_GUIDE.md` | Windows + WSL management |
| `SETUP_INDEX.md` | This file |

### Examples

| File | Content |
|------|---------|
| `examples/omnilingual_asr_example.py` | Usage examples |
| `examples/asr_usage_example.py` | Whisper examples (existing) |

---

## 🎯 By Role

### I'm a Developer

**Read:**
1. `OMNILINGUAL_ASR_SUMMARY.md` - Overview
2. `DOCKER_SETUP_GUIDE.md` - Best for development
3. `examples/omnilingual_asr_example.py` - Code examples

**Run:**
```powershell
.\docker-build.ps1
.\docker-run.ps1 -Shell
```

---

### I'm a DevOps Engineer

**Read:**
1. `DOCKER_SETUP_GUIDE.md` - Complete Docker guide
2. Check production section
3. Review docker-compose.omnilingual.yml

**Deploy:**
```bash
docker-compose -f docker-compose.omnilingual.yml up -d
```

---

### I'm a Data Scientist

**Read:**
1. `OMNILINGUAL_ASR_OPTIONS.md` - Understand options
2. `examples/omnilingual_asr_example.py` - See the API
3. `DOCKER_SETUP_GUIDE.md` - GPU support section

**Run:**
```powershell
.\docker-run.ps1 -Shell
# Then experiment with ASR models
```

---

### I'm a Manager / Decision Maker

**Read:**
1. `OMNILINGUAL_ASR_SUMMARY.md` - Overview and options
2. `OMNILINGUAL_ASR_OPTIONS.md` - Compare solutions
3. Feature matrix and cost/time comparison

---

## ❓ FAQ

### Q: Which solution should I use?

**A:** Docker (see `OMNILINGUAL_ASR_OPTIONS.md` for details)

### Q: How long does setup take?

**A:** 
- Docker: 10-20 minutes
- WSL: 30+ minutes
- Windows (no omnilingual): 5 minutes

### Q: Can I use my Windows editor?

**A:** Yes! All solutions support editing in Windows.

### Q: Do I need a GPU?

**A:** No, CPU works fine. GPU speeds up transcription.

### Q: Will this break my existing environment?

**A:**
- Docker: No (fully isolated)
- WSL: No (separate from Windows)
- Windows: Only if you use setup_windows.ps1

### Q: Can I use both Windows and Docker?

**A:** Yes! They're completely independent.

---

## 🆘 Need Help?

1. **Check the troubleshooting section** in your chosen guide
2. **Verify prerequisites** (Docker running, WSL installed, etc.)
3. **Review the specific guide** for your solution

**Common issues are covered in:**
- `DOCKER_SETUP_GUIDE.md` - Troubleshooting section
- `WSL_SETUP_GUIDE.md` - Troubleshooting section

---

## ✅ Quick Validation

After setup, verify everything works:

### Docker
```powershell
.\docker-run.ps1 -TestASR
```

Expected: `✓ omnilingual-asr works!`

### WSL
```bash
source .venv/bin/activate
python -c "import omnilingual_asr; print('Success!')"
```

Expected: `Success!`

---

## 🎉 Ready to Start?

Choose your path:

### 🐳 **Docker** (Recommended)
```powershell
.\docker-build.ps1
```
→ Continue with `DOCKER_SETUP_GUIDE.md`

### 🐧 **WSL**
```bash
wsl
./scripts/maintenance/setup_wsl.sh
```
→ Continue with `WSL_SETUP_GUIDE.md`

### 🪟 **Windows** (No omnilingual-asr)
```powershell
.\setup_windows.ps1
```
→ Use existing Whisper ASR

---

**Still deciding?** → Read `OMNILINGUAL_ASR_SUMMARY.md` first!


