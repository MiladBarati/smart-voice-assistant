# Docker Interactive Development Guide

## Quick Start: Get an Interactive Shell

```powershell
.\docker-run.ps1 -Shell
```

This opens a **bash terminal inside the Docker container** with:
- ✅ omnilingual-asr ready to use
- ✅ All Python packages installed
- ✅ Your files mounted and accessible
- ✅ No venv needed (packages are system-wide)

---

## Understanding the Environment

### No Virtual Environment Needed! 🎉

In Docker, packages are installed **system-wide**. Unlike your local development:

| Your Windows | Inside Docker |
|--------------|---------------|
| Need to activate `.venv` | ❌ No venv needed |
| `source .venv/bin/activate` | ✅ Just use `python3` |
| Limited to venv packages | ✅ All packages available globally |

**Just run `python3` and everything works!**

### What's Available

```bash
# Inside the container, you have:
- omnilingual-asr ✅
- PyTorch + torchaudio ✅
- transformers ✅
- PJSUA2 ✅
- All your project dependencies ✅
```

---

## Interactive Python Session

### Start Python REPL

```bash
# Inside container
python3
```

### Use omnilingual-asr

```python
>>> from omnilingual_asr import ASR
>>> asr = ASR(device='cpu')
>>> 
>>> # Transcribe a file
>>> result = asr.transcribe(
...     'recordings/2025-11-02/call_20251102_180619_1001/20251102_180619_1001_incoming.wav',
...     src_lang='fas',  # Farsi/Persian
...     tgt_lang='eng'   # English
... )
>>> 
>>> print(result['text'])
>>> exit()
```

### IPython (Enhanced REPL)

```bash
# Install IPython (optional, for better interactive experience)
pip install ipython

# Use IPython
ipython
```

---

## Running Your Scripts

### Run Example Scripts

```bash
# Inside container
python3 examples/omnilingual_asr_example.py
```

### Run Your Bot

```bash
python3 -m pjsua_bot.register_bot
```

### Run Custom Code

```bash
# Create a test script
cat > /tmp/test.py << 'EOF'
from omnilingual_asr import ASR

asr = ASR(device='cpu')
print("omnilingual-asr loaded successfully!")
print(f"Model ready on device: {asr.device}")
EOF

# Run it
python3 /tmp/test.py
```

---

## File System Layout

### Your Files (Mounted from Windows)

```bash
# Inside container, your Windows files are here:
/app/recordings/     ← Windows: .\recordings\
/app/assets/         ← Windows: .\assets\
/app/src/            ← Windows: .\src\
/app/examples/       ← Windows: .\examples\
```

**Changes you make in Windows are immediately visible in Docker!**

### Navigate Around

```bash
# List recordings
ls -la /app/recordings/

# Go to examples
cd /app/examples/

# Check your source code
cd /app/src/pjsua_bot/
ls -la
```

---

## Development Workflow

### Workflow 1: Edit in Windows, Run in Docker

1. **Edit files** in Windows (Cursor/VSCode)
2. **Save changes**
3. **Run in Docker** (changes are immediate - no rebuild!)

```powershell
# Open shell
.\docker-run.ps1 -Shell

# Inside container, run your modified code
python3 examples/my_new_script.py
```

### Workflow 2: Quick Tests

```powershell
# Run specific script without entering shell
.\docker-run.ps1 -Command "examples/omnilingual_asr_example.py"
```

### Workflow 3: Iterative Development

```bash
# Inside container shell
while true; do
    python3 my_script.py
    read -p "Run again? (y/n) " yn
    case $yn in
        [Yy]* ) continue;;
        [Nn]* ) break;;
        * ) break;;
    esac
done
```

---

## Useful Commands Inside Container

### Check Installation

```bash
# Test omnilingual-asr
python3 -c "import omnilingual_asr; print('✓ omnilingual-asr works!')"

# Check version
python3 -c "import omnilingual_asr; print(omnilingual_asr.__version__)"

# List all packages
pip list

# Find specific package
pip show omnilingual-asr
```

### System Information

```bash
# Check Python version
python3 --version

# Check available memory
free -h

# Check CPU info
lscpu | grep "Model name"

# Check disk space
df -h
```

### Working with Audio Files

```bash
# List all recordings
find /app/recordings/ -name "*.wav" | head -20

# Get file info
file /app/recordings/2025-11-02/call_20251102_180619_1001/20251102_180619_1001_incoming.wav

# Count recordings
find /app/recordings/ -name "*.wav" | wc -l
```

---

## Advanced Usage

### Install Additional Packages (Temporary)

```bash
# Install in current session (lost when container stops)
pip install ipython jupyter

# Use it
ipython
```

**Note:** These packages are **not persistent**. To make them permanent, add to `Dockerfile.omnilingual` and rebuild.

### Run Jupyter Notebook (Advanced)

```bash
# Inside container
pip install jupyter
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

Then access from Windows browser: `http://localhost:8888`

### GPU Usage (If Available)

```bash
# Check if GPU is available
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Use GPU in omnilingual-asr
python3 -c "from omnilingual_asr import ASR; asr = ASR(device='cuda'); print('GPU ready!')"
```

---

## Debugging

### Check Environment Variables

```bash
echo $PYTHONUNBUFFERED
echo $LD_LIBRARY_PATH
echo $HF_HOME
```

### Check Python Path

```bash
python3 -c "import sys; print('\n'.join(sys.path))"
```

### Find Where Package is Installed

```bash
python3 -c "import omnilingual_asr; print(omnilingual_asr.__file__)"
```

### Check Logs

```bash
# If your bot creates logs
tail -f /app/logs/*.log
```

---

## Common Tasks

### Task 1: Test omnilingual-asr with One File

```bash
# Inside container
python3 << 'EOF'
from omnilingual_asr import ASR

asr = ASR(device='cpu')
result = asr.transcribe(
    'recordings/2025-11-02/call_20251102_180619_1001/20251102_180619_1001_incoming.wav',
    src_lang='fas',
    tgt_lang='eng'
)
print("Transcription:", result['text'])
EOF
```

### Task 2: Batch Process Recordings

```bash
python3 examples/omnilingual_asr_example.py
```

### Task 3: Interactive Model Testing

```bash
python3
>>> from omnilingual_asr import ASR
>>> asr = ASR(device='cpu')
>>> 
>>> # Test with different languages
>>> for lang in ['fas', 'ara', 'tur']:
...     result = asr.transcribe('test.wav', src_lang=lang, tgt_lang='eng')
...     print(f"{lang}: {result['text']}")
```

---

## Tips & Tricks

### 1. Keep Shell Open

Keep the Docker shell open in one terminal while you edit in Windows:

```powershell
# Terminal 1: Keep this open
.\docker-run.ps1 -Shell

# Terminal 2: Edit in Cursor/VSCode
# Files sync automatically!
```

### 2. Command History

```bash
# Search command history
Ctrl+R

# List history
history

# Run previous command
!!
```

### 3. Create Aliases

```bash
# Inside container, add to ~/.bashrc
echo 'alias asr="python3 -c \"from omnilingual_asr import ASR; print('\\''Ready!'\\'')\"" ' >> ~/.bashrc
source ~/.bashrc

# Now just type:
asr
```

### 4. Quick Python Tests

```bash
# One-liner to test
python3 -c "from omnilingual_asr import ASR; print('Works!')"
```

---

## Exiting the Container

### Exit Shell

```bash
# Any of these:
exit
Ctrl+D
logout
```

### Container Cleanup

```bash
# Container is automatically removed when you exit
# (because we use --rm flag)
```

---

## Multi-Terminal Setup

### Terminal 1: Interactive Shell

```powershell
.\docker-run.ps1 -Shell
```

Keep this open for interactive work.

### Terminal 2: Run Commands

```powershell
# Run quick tests
.\docker-run.ps1 -Command "examples/test.py"
```

### Terminal 3: View Logs

```powershell
# If using docker-compose
docker-compose -f docker-compose.omnilingual.yml logs -f
```

---

## Persistent Changes

### What Persists:

✅ **Files in mounted directories:**
- `/app/recordings/` → Persists (mounted)
- `/app/assets/` → Persists (mounted)
- `/app/src/` → Persists (mounted)
- Any changes to these are permanent

### What Doesn't Persist:

❌ **Changes inside container:**
- Installed packages (unless added to Dockerfile)
- Files created outside mounted directories
- Configuration changes
- Shell history

**To make changes permanent:** Edit `Dockerfile.omnilingual` and rebuild.

---

## Quick Reference

| Task | Command |
|------|---------|
| **Open shell** | `.\docker-run.ps1 -Shell` |
| **Run Python** | `python3` |
| **Test ASR** | `python3 -c "from omnilingual_asr import ASR; print('OK')"` |
| **Run script** | `python3 examples/my_script.py` |
| **List files** | `ls -la /app/recordings/` |
| **Exit** | `exit` or `Ctrl+D` |
| **Check packages** | `pip list` |
| **Find files** | `find /app -name "*.wav"` |

---

## Next Steps

1. **Open shell:**
   ```powershell
   .\docker-run.ps1 -Shell
   ```

2. **Test omnilingual-asr:**
   ```bash
   python3 -c "from omnilingual_asr import ASR; print('Ready!')"
   ```

3. **Run your code:**
   ```bash
   python3 examples/omnilingual_asr_example.py
   ```

4. **Develop:**
   - Edit files in Windows
   - Run them in Docker shell
   - Iterate quickly!

---

## Summary

✅ **No venv needed** - packages are system-wide  
✅ **Just use `python3`** - everything is ready  
✅ **Edit in Windows, run in Docker** - files sync automatically  
✅ **Fast iteration** - no rebuild needed for code changes  
✅ **Full Linux environment** - all tools available  

**Ready to code?**

```powershell
.\docker-run.ps1 -Shell
```


