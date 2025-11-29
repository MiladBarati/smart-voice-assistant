#!/bin/bash
# Script to fix permissions for Docker volumes
# This ensures the container user (UID 1000) can write to mounted directories

set -e

echo "Fixing permissions for Docker volumes..."

# Fix recordings directory
if [ -d "./recordings" ]; then
    echo "Setting permissions for ./recordings..."
    sudo chown -R 1000:1000 ./recordings
    sudo chmod -R 755 ./recordings
else
    echo "Creating ./recordings directory..."
    mkdir -p ./recordings
    sudo chown -R 1000:1000 ./recordings
    sudo chmod -R 755 ./recordings
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


