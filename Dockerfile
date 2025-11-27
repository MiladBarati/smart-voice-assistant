FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ARG PJSIP_VERSION=2.14

# Set timezone and non-interactive mode
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    build-essential \
    ca-certificates \
    libssl-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libgsm1-dev \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    swig && \
    rm -rf /var/lib/apt/lists/*

# Set python3.11 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Download and extract PJSIP
WORKDIR /tmp
RUN wget -q https://github.com/pjsip/pjproject/archive/refs/tags/${PJSIP_VERSION}.tar.gz && \
    tar -xzf ${PJSIP_VERSION}.tar.gz && \
    rm ${PJSIP_VERSION}.tar.gz

# Configure and build PJSIP
WORKDIR /tmp/pjproject-${PJSIP_VERSION}
RUN ./configure \
    --prefix=/usr/local \
    --enable-shared \
    --disable-video \
    --disable-v4l2 \
    --disable-sdl \
    --disable-libyuv \
    --disable-opencore-amr \
    --with-external-speex \
    --with-external-gsm \
    CFLAGS="-O2 -DNDEBUG -DPJ_AUTOCONF=1" \
    CXXFLAGS="-O2 -DNDEBUG" && \
    make dep && \
    make -j$(nproc) && \
    make install && \
    ldconfig

# Build Python bindings (system-wide)
WORKDIR /tmp/pjproject-${PJSIP_VERSION}/pjsip-apps/src/swig/python
RUN make && python3.11 setup.py install

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies with uv (system Python)
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --python python3.11 -r pyproject.toml

# Copy application code
COPY src/ ./src/
COPY assets/ ./assets/

# Create necessary directories
RUN mkdir -p /app/data/recordings /app/logs

# Create non-root user
RUN useradd -m -u 1000 voicebot && \
    chown -R voicebot:voicebot /app

USER voicebot

# ALSA null device config
RUN mkdir -p ~/.config/alsa && \
    echo 'pcm.!default { type plug slave.pcm "null" }' > ~/.config/alsa/asound.conf

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH \
    AUDIODEV=null

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3.11 -c "import pjsua2; print('OK')" || exit 1

# Persistent volumes
VOLUME ["/app/data/recordings", "/app/assets/audio"]

# SIP and RTP ports
EXPOSE 5060/udp 10000-20000/udp

# Run the voicebot
CMD ["python3.11", "/app/src/pjsua_bot/register_bot.py", "--user", "1004", "--auth-user", "1004", "--password", "05e858b1bbd57d5b1f42fbdbdf5c7616", "--domain", "178.239.151.95", "--transport", "udp", "--local-port", "0", "--wait-seconds", "20", "--stay-online", "--auto-answer", "--play-file", "/app/assets/audio/welcome_message.wav", "--message-duration", "8", "--hangup-delay", "2", "--enable-recording", "--enable-vad", "--silence-after-speech-sec", "3.0", "--vad-threshold", "0.5", "--goodbye-file", "/app/assets/audio/goodbye_voice.wav"]