# Multi-stage build for PJSUA2 SIP Bot - Optimized Version
# Stage 1: Build PJSIP/PJSUA2 from source
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    automake \
    autoconf \
    libtool \
    pkg-config \
    wget \
    libssl-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libgsm1-dev \
    libasound2-dev \
    python3-dev \
    swig \
    && rm -rf /var/lib/apt/lists/*

# Download and build PJSIP with optimized flags
WORKDIR /tmp
ENV PJSIP_VERSION=2.14

RUN wget -q https://github.com/pjsip/pjproject/archive/refs/tags/${PJSIP_VERSION}.tar.gz \
    && tar -xzf ${PJSIP_VERSION}.tar.gz \
    && cd pjproject-${PJSIP_VERSION} \
    && ./configure \
    --enable-shared \
    --disable-video \
    --disable-opencore-amr \
    --disable-libyuv \
    --disable-libwebrtc \
    --disable-v4l2 \
    --disable-sdl \
    --disable-ffmpeg \
    --disable-openh264 \
    --with-external-speex \
    --with-external-gsm \
    CFLAGS="-O2 -DNDEBUG -DPJ_AUTOCONF=1" \
    && make dep \
    && make \
    && make install \
    && ldconfig \
    && cd /tmp/pjproject-${PJSIP_VERSION}/pjsip-apps/src/swig/python \
    && make && python3 setup.py install \
    && cd /tmp \
    && rm -rf pjproject-${PJSIP_VERSION} ${PJSIP_VERSION}.tar.gz

# Install Python dependencies in builder stage
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && find /usr/local/lib/python3.11/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11/site-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Stage 2: Runtime image (minimal)
FROM python:3.11-slim

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    libopus0 \
    libspeex1 \
    libspeexdsp1 \
    libgsm1 \
    libasound2 \
    libsndfile1 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy only necessary PJSIP libraries
COPY --from=builder /usr/local/lib/libpj*.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/python3.11/site-packages/pjsua2* /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/lib/python3.11/site-packages/_pjsua2* /usr/local/lib/python3.11/site-packages/

# Copy Python dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Update library cache
RUN ldconfig

# Create minimal ALSA config
RUN mkdir -p /etc/alsa && \
    echo 'pcm.!default { type plug slave.pcm "null" }' > /etc/alsa/asound.conf

# Set working directory
WORKDIR /app

# Copy application code (only necessary files)
COPY --chown=1000:1000 src/ ./src/
COPY --chown=1000:1000 assets/ ./assets/

# Create necessary directories
RUN mkdir -p /app/data/recordings /app/logs \
    && useradd -m -u 1000 -s /bin/false voicebot \
    && chown -R voicebot:voicebot /app

# Switch to non-root user
USER voicebot

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib \
    AUDIODEV=null \
    PYTHONOPTIMIZE=2

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import pjsua2; print('OK')" || exit 1

# Volumes for persistent data
VOLUME ["/app/data/recordings", "/app/assets/audio"]

# Expose SIP ports
EXPOSE 5060/udp 10000-20000/udp

# Run the voicebot
CMD ["python3", "-O", "/app/src/pjsua_bot/register_bot.py", \
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