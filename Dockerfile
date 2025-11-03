# Multi-stage build for PJSUA2 SIP Bot - Optimized for size and build speed
# Stage 1: Build PJSIP from source
FROM python:3.11-slim AS builder

ARG PJSIP_VERSION=2.14

# Install build dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    ca-certificates \
    libssl-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libgsm1-dev \
    libasound2-dev \
    python3-dev \
    swig

# Download and extract PJSIP
WORKDIR /tmp
RUN wget -q https://github.com/pjsip/pjproject/archive/refs/tags/${PJSIP_VERSION}.tar.gz && \
    tar -xzf ${PJSIP_VERSION}.tar.gz && \
    rm ${PJSIP_VERSION}.tar.gz

# Configure and build PJSIP with optimizations
# Disabled: video, v4l2, SDL, libyuv, opencore-amr (not needed for VoIP bot)
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

# Build Python bindings
WORKDIR /tmp/pjproject-${PJSIP_VERSION}/pjsip-apps/src/swig/python
RUN make && python3 setup.py install

# Stage 2: Build Python dependencies separately for better layer caching
FROM python:3.11-slim AS python-builder

WORKDIR /app
COPY requirements.txt .

# Install Python dependencies with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

# Stage 3: Final runtime image
FROM python:3.11-slim

# Install only runtime dependencies (no build tools)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    libopus0 \
    libspeex1 \
    libspeexdsp1 \
    libgsm1 \
    libasound2 \
    libasound2-plugins \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy ALL PJSIP libraries from builder (including libilbccodec)
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/lib/python3.11/site-packages/pjsua2* /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/lib/python3.11/site-packages/_pjsua2* /usr/local/lib/python3.11/site-packages/

# Copy Python packages from python-builder stage
COPY --from=python-builder /install /usr/local

# Update library cache
RUN ldconfig

# Create ALSA config for null audio device (headless operation)
RUN mkdir -p /etc/alsa && \
    echo 'pcm.!default { type plug slave.pcm "null" }' > /etc/alsa/asound.conf

WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY assets/ ./assets/

# Create necessary directories
RUN mkdir -p /app/data/recordings /app/logs

# Create non-root user for security
RUN useradd -m -u 1000 voicebot && \
    chown -R voicebot:voicebot /app

USER voicebot

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH \
    AUDIODEV=null

# Health check to verify PJSUA2 is working
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import pjsua2; print('OK')" || exit 1

# Persistent volumes
VOLUME ["/app/data/recordings", "/app/assets/audio"]

# SIP and RTP ports
EXPOSE 5060/udp 10000-20000/udp

# Run the voicebot
CMD ["python3", "/app/src/pjsua_bot/register_bot.py", \
    "--user", "1004", \
    "--auth-user", "1004", \
    "--password", "05e858b1bbd57d5b1f42fbdbdf5c7616", \
    "--domain", "178.239.151.95", \
    "--transport", "udp", \
    "--local-port", "0", \
    "--wait-seconds", "20", \
    "--stay-online", \
    "--auto-answer", \
    "--play-file", "/app/assets/audio/welcome_message.wav", \
    "--message-duration", "8", \
    "--hangup-delay", "2", \
    "--enable-recording"]