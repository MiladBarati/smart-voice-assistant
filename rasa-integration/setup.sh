#!/bin/bash
# Setup script for Rasa integration
# This script sets up Rasa in a virtual environment

set -e

echo "=== Rasa Integration Setup ==="
echo ""

# Check Python version (Rasa 3.6.x requires Python 3.8-3.10, not 3.11+)
PYTHON_CMD=""
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo "Found Python 3.10 (compatible with Rasa 3.6.x)"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
    echo "Found Python 3.9 (compatible with Rasa 3.6.x)"
elif command -v python3.8 &> /dev/null; then
    PYTHON_CMD="python3.8"
    echo "Found Python 3.8 (compatible with Rasa 3.6.x)"
else
    echo "ERROR: Rasa 3.6.x requires Python 3.8-3.10 (not 3.11+)"
    echo "Current Python version: $(python3 --version)"
    echo ""
    echo "Please install Python 3.10:"
    echo ""
    echo "For Ubuntu/Debian:"
    echo "  sudo apt update"
    echo "  sudo apt install -y python3.10 python3.10-venv python3.10-dev"
    echo ""
    echo "Or use pyenv:"
    echo "  pyenv install 3.10.13"
    echo "  pyenv local 3.10.13"
    exit 1
fi

# Check if venv exists and uses correct Python version
if [ -d "venv" ]; then
    # Check what Python version the venv is using
    VENV_PYTHON=$(venv/bin/python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    REQUIRED_PYTHON=$($PYTHON_CMD --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    
    if [ "$VENV_PYTHON" != "$REQUIRED_PYTHON" ]; then
        echo "WARNING: Existing venv uses Python $VENV_PYTHON, but we need Python $REQUIRED_PYTHON"
        echo "Removing old venv and creating a new one..."
        rm -rf venv
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Rasa (specify version 3.6.x which supports Python 3.8-3.10)
echo "Installing Rasa 3.6.x..."
pip install "rasa>=3.6.0,<3.7.0"

# Initialize Rasa project if not already initialized
if [ ! -f "config.yml" ]; then
    echo "Initializing Rasa project..."
    rasa init --no-prompt
    echo ""
    echo "Rasa project initialized successfully!"
else
    echo "Rasa project already initialized."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the virtual environment in the future:"
echo "  source venv/bin/activate"
echo ""
echo "To verify installation:"
echo "  rasa --version"
echo "  rasa shell  # Test with 'hello'"
echo ""

