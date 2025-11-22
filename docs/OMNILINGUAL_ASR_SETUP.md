# Setting Up the Project in WSL for omnilingual-asr

## Overview
This guide will help you set up your PJSUA Bot project in WSL (Ubuntu) to use `omnilingual-asr`, which is not compatible with native Windows.

## Prerequisites
- WSL2 with Ubuntu installed ✅ (You already have this!)
- Your project files accessible from WSL

## Step 1: Access Your Project in WSL

Your Windows files are accessible from WSL at `/mnt/d/`:

```bash
# Open WSL terminal (or run: wsl)
cd "/mnt/d/Amin Raay/pjsua installation"
```

**Important Note:** While you can access Windows files from `/mnt/`, for better performance with Python packages, consider copying your project to WSL's native filesystem (e.g., `~/projects/pjsua-installation`).

## Step 2: Install Python 3.11+ in WSL

```bash
# Update package lists
sudo apt update

# Install Python 3.11 and dev tools
sudo apt install -y python3.11 python3.11-dev python3.11-venv python3-pip

# Install build essentials (needed for compiling some packages)
sudo apt install -y build-essential git curl wget

# Verify installation
python3.11 --version
```

## Step 3: Install uv in WSL

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add this to ~/.bashrc for persistence)
source $HOME/.cargo/env

# Verify installation
uv --version
```

## Step 4: Modify pyproject.toml for Linux

You need to update `pyproject.toml` to work with Linux. The key changes:

1. **Remove Windows-specific constraints** in `[tool.uv]` section
2. **Update torch/torchaudio dependencies** to work on Linux
3. **Add omnilingual-asr** as a dependency

## Step 5: Install Dependencies

```bash
# Navigate to project directory in WSL
cd "/mnt/d/Amin Raay/pjsua installation"

# Create virtual environment with Python 3.11
uv venv --python 3.11

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (after updating pyproject.toml)
uv sync

# Add omnilingual-asr
uv add omnilingual-asr
```

## Step 6: Install PJSUA2 Library in WSL

PJSIP/PJSUA needs to be compiled for Linux:

```bash
# Install PJSIP dependencies
sudo apt install -y \
    libasound2-dev \
    libssl-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libgsm1-dev \
    uuid-dev

# Download and build PJSIP (this takes 10-20 minutes)
cd ~
wget https://github.com/pjsip/pjproject/archive/refs/tags/2.14.tar.gz
tar -xzf 2.14.tar.gz
cd pjproject-2.14

# Configure with Python bindings
./configure --enable-shared CFLAGS="-fPIC"
make dep
make

# Build Python bindings
cd pjsip-apps/src/swig/python
make

# Install Python module
sudo make install

# Return to project directory
cd "/mnt/d/Amin Raay/pjsua installation"
```

## Step 7: Test omnilingual-asr Installation

```bash
# Activate your virtual environment
source .venv/bin/activate

# Test import
python3 -c "import omnilingual_asr; print('Success!')"
```

## Important Considerations

### Audio Device Access
- WSL2 has limited audio support
- For **recording/playback**, you may need PulseAudio or PipeWire setup
- For **file processing only** (transcribing existing recordings), no audio setup needed

### File Paths
- Windows paths: `D:\Amin Raay\pjsua installation`
- WSL paths: `/mnt/d/Amin Raay/pjsua installation`
- When running scripts, use WSL-style paths

### Performance Tips
1. **Best Performance**: Copy project to WSL filesystem (`~/projects/`)
2. **Convenience**: Run from `/mnt/d/` (slower I/O but easier file sharing)

### Running Your Bot in WSL

```bash
# Activate environment
source .venv/bin/activate

# Run your bot
python3 -m pjsua_bot.register_bot
# or
python3 src/pjsua_bot/register_bot.py
```

## GPU Support (Optional - For CUDA)

If you have an NVIDIA GPU and want GPU acceleration in WSL:

```bash
# Install NVIDIA CUDA Toolkit for WSL
# Follow: https://docs.nvidia.com/cuda/wsl-user-guide/index.html

# Verify CUDA
nvidia-smi
```

## Hybrid Approach (Development on Windows, Execution in WSL)

You can edit files in Windows (using Cursor/VSCode) and run them in WSL:

1. Edit files in Windows as normal
2. Open WSL terminal: `wsl`
3. Run scripts from WSL environment
4. Files sync automatically (same physical location)

## Troubleshooting

### Issue: uv command not found
```bash
source $HOME/.cargo/env
# Or add to ~/.bashrc
```

### Issue: Permission denied
```bash
# Make sure files are accessible
chmod +x path/to/script
```

### Issue: Module not found
```bash
# Ensure virtual environment is activated
source .venv/bin/activate
```

### Issue: omnilingual-asr still fails
```bash
# Check Python version (must be 3.11+)
python3 --version

# Try with explicit Python version
uv venv --python 3.12
```

## Next Steps

After setup, you'll need to:
1. Update your ASR code to use omnilingual-asr instead of transformers
2. Configure the model settings
3. Test with your audio recordings

Need help with any of these steps? Let me know!


