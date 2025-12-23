# Setting Up omnilingual-asr with WSL

## ✅ What I've Done For You

I've configured your project to use `omnilingual-asr` in WSL:

1. **Updated `pyproject.toml`**:
   - Changed from Windows to Linux environment
   - Removed platform-specific torch constraints
   - Added `omnilingual-asr>=0.1.0` as a dependency

2. **Created Setup Files**:
   - `scripts/maintenance/setup_wsl.sh` - Automated setup script
   - `WSL_SETUP_GUIDE.md` - Detailed documentation
   - `WSL_QUICK_START.md` - Quick reference
   - `examples/omnilingual_asr_example.py` - Usage examples

3. **Verified WSL**:
   - You have WSL2 with Ubuntu installed ✅
   - Setup script is ready to run ✅

## 🚀 How to Get Started (3 Simple Steps)

### Step 1: Open WSL Terminal

In PowerShell (already open) or Command Prompt:

```powershell
wsl
```

### Step 2: Navigate and Run Setup

```bash
cd "/mnt/d/Amin Raay/pjsua installation"
./scripts/maintenance/setup_wsl.sh
```

This will:
- Install Python 3.11
- Install uv package manager
- Create virtual environment
- Install all dependencies including omnilingual-asr

**Time:** ~5-10 minutes (depending on internet speed)

### Step 3: Test Installation

```bash
source .venv/bin/activate
python3 -c "import omnilingual_asr; print('Success! omnilingual-asr is ready!')"
```

## 📋 What Changed in Your Project

### `pyproject.toml` Changes

**Before (Windows-only):**
```toml
required-environments = ["sys_platform == 'win32'"]
torch>=2.1.0 ; platform_machine != 'x86' or sys_platform != 'win32'
```

**After (Linux/WSL):**
```toml
required-environments = ["sys_platform == 'linux'"]
torch>=2.1.0
omnilingual-asr>=0.1.0
```

## 🎯 Using omnilingual-asr in Your Code

### Quick Example

```python
from omnilingual_asr import ASR

# Initialize ASR
asr = ASR(device='cpu')  # or 'cuda' for GPU

# Transcribe audio
result = asr.transcribe(
    "path/to/audio.wav",
    src_lang='fas',  # Farsi/Persian
    tgt_lang='eng'   # English translation
)

print(result['text'])
```

### Full Example

See `examples/omnilingual_asr_example.py` for:
- Single file transcription
- Complete call transcription (incoming + outgoing)
- Batch processing
- Comparison with Whisper

## 🔄 Workflow: Edit in Windows, Run in WSL

This is the recommended workflow:

1. **Edit files** in Windows using Cursor/VSCode
2. **Run code** in WSL terminal
3. **Files sync automatically** (same physical location)

No need to copy files back and forth!

## 📊 omnilingual-asr vs Your Current Whisper

| Feature | Your Whisper | omnilingual-asr |
|---------|-------------|-----------------|
| Model | Whisper Large | SeamlessM4T v2 |
| Languages | ~99 | 100+ |
| Translation | No | Yes (built-in) |
| Language Detection | Limited | Automatic |
| Platform | Windows/Linux | Linux only |
| Best For | Persian transcription | Multilingual + translation |

## 🎨 Integration Options

### Option 1: Replace Current ASR (Recommended)

Modify `src/pjsua_bot/asr.py` to use omnilingual-asr instead of Whisper.

### Option 2: Dual ASR Support (Flexible)

Keep both and choose based on:
- Use Whisper for Windows development
-.Use omnilingual-asr for production in WSL
- Switch based on language needs

### Option 3: Hybrid Approach

Use omnilingual-asr for transcription, Whisper as fallback.

## 🐛 Troubleshooting

### Issue: Setup script fails

```bash
# Run manually:
sudo apt update
sudo apt install -y python3.11 python3.11-dev build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv venv --python 3.11
source .venv/bin/activate
uv sync
```

### Issue: "No module named 'omnilingual_asr'"

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Install explicitly
uv add omnilingual-asr

# Verify
python3 -c "import omnilingual_asr"
```

### Issue: CUDA not available

```bash
# Check GPU
nvidia-smi

# If no GPU, use CPU (it's fine!)
asr = ASR(device='cpu')
```

## 📈 Next Steps After Setup

1. **Test with example:**
   ```bash
   python3 examples/omnilingual_asr_example.py
   ```

2. **Integrate into your bot:**
   - Update `src/pjsua_bot/asr.py` or create new module
   - Add omnilingual transcription to call handling
   - Test with your recordings

3. **Optimize performance:**
   - Use GPU if available (change device='cuda')
   - Adjust batch size for your hardware
   - Consider copying project to WSL filesystem for better I/O

## 📚 Documentation Files

- **WSL_QUICK_START.md** - Quick reference commands
- **WSL_SETUP_GUIDE.md** - Detailed setup instructions
- **examples/omnilingual_asr_example.py** - Code examples
- **This file** - Overview and getting started

## 🆘 Need Help?

If you encounter any issues:

1. Check error messages carefully
2. Verify Python version: `python3 --version` (should be 3.11+)
3. Ensure venv is activated: look for `(.venv)` in prompt
4. Check installation: `uv sync` to reinstall dependencies

## ✨ Summary

You're all set! Just run:

```bash
wsl
cd "/mnt/d/Amin Raay/pjsua installation"
./scripts/maintenance/setup_wsl.sh
```

And you'll have omnilingual-asr running on your system! 🎉


