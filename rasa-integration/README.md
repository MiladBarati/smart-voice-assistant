# Rasa Integration Directory

This directory contains the standalone Rasa project for intent classification.

## Python Version Requirement

**Important:** Rasa 3.6.x requires Python 3.8-3.10 (Python 3.11+ is NOT supported). The system currently has Python 3.12.

### Option 1: Install Python 3.10 (Recommended)

If you have `pyenv` installed:
```bash
pyenv install 3.10.13
pyenv local 3.10.13
python3.10 -m venv venv
source venv/bin/activate
pip install rasa
```

### Option 2: Use Docker (See Phase 7)

Rasa can be run in Docker, which will handle the Python version automatically.

### Option 3: Install Python 3.10 via System Package Manager (Ubuntu/Debian)

For Ubuntu 24.04, Python 3.10 is available in the default repositories:

```bash
# Quick install script
./install-python3.10.sh

# Or manually:
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# Then create venv and install Rasa
python3.10 -m venv venv
source venv/bin/activate
pip install rasa
```

## Setup Instructions

Once you have Python 3.10 available:

1. Create and activate virtual environment:
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate
   ```

2. Install Rasa:
   ```bash
   pip install rasa
   ```

3. Initialize Rasa project:
   ```bash
   rasa init --no-prompt
   ```

4. Verify installation:
   ```bash
   rasa --version
   rasa shell  # Test with "hello"
   ```

## Next Steps

After completing Phase 1 setup, proceed to Phase 2: Create Persian NLU Training Data.

