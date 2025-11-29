#!/bin/bash
# Helper script to install Python 3.10 on Ubuntu/Debian
# Rasa 3.6.x requires Python 3.8-3.10 (not 3.11+)

set -e

echo "=== Installing Python 3.10 for Rasa ==="
echo "Note: Rasa 3.6.x requires Python 3.8-3.10 (Python 3.11+ is not supported)"
echo ""

# Check if running on Ubuntu/Debian
if ! command -v apt &> /dev/null; then
    echo "ERROR: This script is for Ubuntu/Debian systems"
    echo "For other systems, please install Python 3.10 manually or use pyenv"
    exit 1
fi

echo "Step 1: Updating package lists..."
sudo apt update

echo ""
echo "Step 2: Installing Python 3.10..."
sudo apt install -y python3.10 python3.10-venv python3.10-dev

echo ""
echo "=== Python 3.10 Installation Complete ==="
echo ""
echo "Verify installation:"
python3.10 --version
echo ""
echo "Now you can run ./setup.sh to complete Rasa installation"

