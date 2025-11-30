#!/bin/bash
set -e

# Fix permissions for mounted volumes
# This ensures that /app/recordings and /app/logs are writable by UID 1000
if [ -d "/app/recordings" ]; then
    chown -R 1000:1000 /app/recordings 2>/dev/null || true
    chmod -R 755 /app/recordings 2>/dev/null || true
fi

if [ -d "/app/logs" ]; then
    chown -R 1000:1000 /app/logs 2>/dev/null || true
    chmod -R 755 /app/logs 2>/dev/null || true
fi

if [ -d "/app/.cache" ]; then
    chown -R 1000:1000 /app/.cache 2>/dev/null || true
    chmod -R 755 /app/.cache 2>/dev/null || true
fi

# Ensure base directories exist
mkdir -p /app/recordings /app/logs /app/.cache
chown -R 1000:1000 /app/recordings /app/logs /app/.cache 2>/dev/null || true
chmod -R 755 /app/recordings /app/logs /app/.cache 2>/dev/null || true

# Ensure ALSA config exists for voicebot user
mkdir -p /home/voicebot/.config/alsa
if [ ! -f /home/voicebot/.config/alsa/asound.conf ]; then
    echo 'pcm.!default { type plug slave.pcm "null" }' > /home/voicebot/.config/alsa/asound.conf
fi
chown -R 1000:1000 /home/voicebot/.config 2>/dev/null || true

# Switch to voicebot user and execute the command
exec gosu 1000:1000 "$@"

