# WSL Quick Start Guide - TL;DR

## Open WSL Terminal

```powershell
# From PowerShell or Command Prompt:
wsl
```

## Navigate to Project

```bash
cd "/mnt/d/Amin Raay/pjsua installation"
```

## Run Setup Script (One-Time Setup)

```bash
# Make script executable
chmod +x scripts/maintenance/setup_wsl.sh

# Run setup
./scripts/maintenance/setup_wsl.sh
```

The script will:
- ✅ Install Python 3.11
- ✅ Install uv package manager
- ✅ Create virtual environment
- ✅ Install all dependencies including omnilingual-asr

## After Setup - Daily Usage

```bash
# 1. Open WSL
wsl

# 2. Navigate to project
cd "/mnt/d/Amin Raay/pjsua installation"

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Run your code
python3 examples/omnilingual_asr_example.py
```

## Verify Installation

```bash
# Activate environment first
source .venv/bin/activate

# Test omnilingual-asr
python3 -c "import omnilingual_asr; print('✓ omnilingual-asr works!')"

# Test existing packages
python3 -c "import torch; print('✓ PyTorch works!')"
python3 -c "import transformers; print('✓ Transformers works!')"
```

## Common Commands

```bash
# Install new package
uv add package-name

# Update dependencies
uv sync

# Run tests
pytest

# Run your bot
python3 src/pjsua_bot/register_bot.py
```

## File Editing

You can edit files in Windows (using Cursor/VSCode) and they'll automatically sync to WSL!

- Windows path: `D:\Amin Raay\pjsua installation`
- WSL path: `/mnt/d/Amin Raay/pjsua installation`

## Troubleshooting

### "uv: command not found"
```bash
source $HOME/.cargo/env
```

### "Virtual environment not activated"
```bash
source .venv/bin/activate
# You should see (.venv) in your prompt
```

### "Module not found"
```bash
# Make sure you're in the right directory
pwd
# Should show: /mnt/d/Amin Raay/pjsua installation

# Make sure venv is activated
source .venv/bin/activate

# Reinstall dependencies
uv sync
```

## Performance Tip

For better performance, consider copying your project to WSL's native filesystem:

```bash
# Copy to WSL filesystem
cp -r "/mnt/d/Amin Raay/pjsua installation" ~/pjsua-installation
cd ~/pjsua-installation

# Work from here for faster I/O
```

## Need GPU Support?

If you have NVIDIA GPU and want CUDA in WSL:

```bash
# Check if GPU is available
nvidia-smi

# Install CUDA toolkit
# Follow: https://docs.nvidia.com/cuda/wsl-user-guide/
```

---

**Ready to start?** Run the setup script:

```bash
wsl
cd "/mnt/d/Amin Raay/pjsua installation"
chmod +x scripts/maintenance/setup_wsl.sh
./scripts/maintenance/setup_wsl.sh
```


