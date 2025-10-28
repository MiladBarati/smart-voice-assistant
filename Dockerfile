# Base image
FROM python:3.11-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For PJSIP/PJSUA2
    libpjproject-dev \
    pjsua2 \
    python3-pjsua2 \
    # For audio processing
    libsndfile1 \
    libportaudio2 \
    ffmpeg \
    alsa-utils \
    # For building packages
    gcc \
    g++ \
    make \
    pkg-config \
    # Network tools (debugging)
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd -m -u 1000 voicebot && \
    mkdir -p /app/data/recordings /app/assets/audio && \
    chown -R voicebot:voicebot /app

WORKDIR /app

# Copy dependency files
COPY --chown=voicebot:voicebot pyproject.toml uv.lock* ./

# Install uv and dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e .

# Copy project code
COPY --chown=voicebot:voicebot . .

# Set permissions for recordings directory
RUN chmod -R 755 /app/data

# Switch to voicebot user
USER voicebot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pjsua2; print('OK')" || exit 1

# Volumes
VOLUME ["/app/data/recordings", "/app/assets/audio"]

# Expose port range for SIP
EXPOSE 5060/udp 10000-20000/udp

# Run the voicebot with full command
CMD ["python", "register_bot.py", \
    "--user", "1003", \
    "--auth-user", "1003", \
    "--password", "2bcf1720c35d88bae068d0e2cfb721a1", \
    "--domain", "178.239.151.95", \
    "--transport", "udp", \
    "--local-port", "0", \
    "--wait-seconds", "20", \
    "--stay-online", \
    "--auto-answer", \
    "--play-file", "assets/audio/welcome_message.wav", \
    "--message-duration", "8", \
    "--hangup-delay", "2", \
    "--enable-recording"]