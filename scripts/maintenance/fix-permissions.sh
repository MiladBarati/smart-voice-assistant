#!/bin/bash
# Script to fix permissions for Docker volumes
# This ensures the container user (UID 1000) can write to mounted directories

set -e

echo "Fixing permissions for Docker volumes..."

RECORDINGS_DIR="./artifacts/recordings"

# Fix recordings directory
if [ -d "$RECORDINGS_DIR" ]; then
    echo "Setting permissions for $RECORDINGS_DIR..."
    sudo chown -R 1000:1000 "$RECORDINGS_DIR"
    sudo chmod -R 755 "$RECORDINGS_DIR"
else
    echo "Creating $RECORDINGS_DIR directory..."
    mkdir -p "$RECORDINGS_DIR"
    sudo chown -R 1000:1000 "$RECORDINGS_DIR"
    sudo chmod -R 755 "$RECORDINGS_DIR"
fi

# Fix logs directory
if [ -d "./logs" ]; then
    echo "Setting permissions for ./logs..."
    sudo chown -R 1000:1000 ./logs
    sudo chmod -R 755 ./logs
else
    echo "Creating ./logs directory..."
    mkdir -p ./logs
    sudo chown -R 1000:1000 ./logs
    sudo chmod -R 755 ./logs
fi

# Fix cache directory (for ASR models)
if [ -d "./cache" ]; then
    echo "Setting permissions for ./cache..."
    sudo chown -R 1000:1000 ./cache
    sudo chmod -R 755 ./cache
else
    echo "Creating ./cache directory..."
    mkdir -p ./cache
    sudo chown -R 1000:1000 ./cache
    sudo chmod -R 755 ./cache
fi

echo "Permissions fixed successfully!"
echo ""
echo "Note: If ASR model loading still fails, you may need to clear the cache:"
echo "  sudo rm -rf ./cache/*"
echo "  sudo chown -R 1000:1000 ./cache"



