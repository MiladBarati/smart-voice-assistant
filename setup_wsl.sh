#!/bin/bash
# WSL Setup Script for PJSUA Bot with omnilingual-asr
# Run this script in WSL Ubuntu terminal

set -e  # Exit on error

echo "=========================================="
echo "PJSUA Bot WSL Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in WSL
if ! grep -qi microsoft /proc/version; then
    print_error "This script must be run in WSL (Windows Subsystem for Linux)"
    exit 1
fi

print_info "Running in WSL - Good!"
echo ""

# Update system packages
print_info "Updating system packages..."
sudo apt update

# Detect available Python version
print_info "Detecting available Python version..."
PYTHON_CMD=""
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    PYTHON_VERSION="3.12"
    print_info "Found Python 3.12 (default in Ubuntu 24.04)"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION="3.11"
    print_info "Found Python 3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$($PYTHON_CMD --version | grep -oP '\d+\.\d+')
    print_info "Found Python $PYTHON_VERSION"
fi

# Install Python and development tools
if [ -z "$PYTHON_CMD" ]; then
    print_info "Installing Python 3.12 and development tools..."
    sudo apt install -y \
        python3.12 \
        python3.12-dev \
        python3.12-venv \
        python3-pip \
        build-essential \
        git \
        curl \
        wget \
        libssl-dev \
        pkg-config
    PYTHON_CMD="python3.12"
    PYTHON_VERSION="3.12"
else
    print_info "Installing Python development tools..."
    sudo apt install -y \
        ${PYTHON_CMD}-dev \
        ${PYTHON_CMD}-venv \
        python3-pip \
        build-essential \
        git \
        curl \
        wget \
        libssl-dev \
        pkg-config
fi

# Verify Python installation
if ! command -v $PYTHON_CMD &> /dev/null; then
    print_error "Python installation failed"
    exit 1
fi

print_info "Python installed: $($PYTHON_CMD --version)"

# Check if version meets requirements (>= 3.11)
VERSION_CHECK=$($PYTHON_CMD -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)")
if [ "$VERSION_CHECK" -eq 0 ]; then
    print_error "Python 3.11+ required, but found $($PYTHON_CMD --version)"
    exit 1
fi

print_info "Python version check: OK (requires >= 3.11)"
echo ""

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    print_info "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source cargo env
    source $HOME/.cargo/env
    
    # Add to bashrc for persistence
    if ! grep -q 'source $HOME/.cargo/env' ~/.bashrc; then
        echo 'source $HOME/.cargo/env' >> ~/.bashrc
        print_info "Added uv to ~/.bashrc"
    fi
else
    print_info "uv already installed: $(uv --version)"
fi

echo ""

# Navigate to project directory
PROJECT_DIR="/mnt/d/Amin Raay/pjsua installation"
if [ ! -d "$PROJECT_DIR" ]; then
    print_error "Project directory not found: $PROJECT_DIR"
    print_warning "Please update PROJECT_DIR variable in this script"
    exit 1
fi

cd "$PROJECT_DIR"
print_info "Working directory: $(pwd)"
echo ""

# Create virtual environment
print_info "Creating virtual environment with Python $PYTHON_VERSION..."
if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists, skipping creation"
else
    uv venv --python $PYTHON_VERSION
    print_info "Virtual environment created at .venv"
fi
echo ""

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate

# Sync dependencies
print_info "Installing project dependencies (this may take a few minutes)..."
print_warning "This will install omnilingual-asr and all dependencies"
uv sync

echo ""
print_info "Verifying omnilingual-asr installation..."
if $PYTHON_CMD -c "import omnilingual_asr" 2>/dev/null; then
    print_info "✓ omnilingual-asr successfully installed!"
else
    print_error "✗ omnilingual-asr installation verification failed"
    print_warning "Try running: uv add omnilingual-asr"
fi

echo ""
echo "=========================================="
print_info "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Test your setup:"
echo "     python -c 'import omnilingual_asr; print(\"Success!\")'"
echo ""
echo "  3. Run your bot:"
echo "     python src/pjsua_bot/register_bot.py"
echo ""
echo "  4. Run example:"
echo "     python examples/omnilingual_asr_example.py"
echo ""
echo "  5. See WSL_SETUP_GUIDE.md for more details"
echo ""
print_info "Python version: $($PYTHON_CMD --version)"
print_warning "Note: If you're using PJSUA2, you'll need to compile it for Linux"
print_warning "See the 'Install PJSUA2 Library in WSL' section in WSL_SETUP_GUIDE.md"
echo ""

