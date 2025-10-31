# Multi-stage build for PJSUA2 SIP Bot
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
    libv4l-dev \
    libsdl2-dev \
    python3-dev \
    swig \
    && rm -rf /var/lib/apt/lists/*

# Download and build PJSIP
WORKDIR /tmp
ENV PJSIP_VERSION=2.14

RUN wget https://github.com/pjsip/pjproject/archive/refs/tags/${PJSIP_VERSION}.tar.gz \
    && tar -xzf ${PJSIP_VERSION}.tar.gz \
    && cd pjproject-${PJSIP_VERSION} \
    && ./configure \
    --enable-shared \
    --disable-video \
    --disable-opencore-amr \
    --with-external-speex \
    --with-external-gsm \
    --enable-libsamplerate \
    CFLAGS="-O2 -DNDEBUG -DPJ_AUTOCONF=1" \
    && make dep \
    && make \
    && make install \
    && ldconfig

# Build Python bindings
WORKDIR /tmp/pjproject-${PJSIP_VERSION}/pjsip-apps/src/swig/python
RUN make && python3 setup.py install

# Stage 2: Runtime image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    libopus0 \
    libspeex1 \
    libspeexdsp1 \
    libgsm1 \
    libasound2 \
    libasound2-plugins \
    alsa-utils \
    libsndfile1 \
    libportaudio2 \
    portaudio19-dev \
    ffmpeg \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

# Copy ALL PJSIP libraries from builder stage
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/include/ /usr/local/include/
COPY --from=builder /usr/local/lib/python3.11/site-packages/pjsua2* /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/lib/python3.11/site-packages/_pjsua2* /usr/local/lib/python3.11/site-packages/

# Update library cache
RUN ldconfig

# Create ALSA config for null device
RUN mkdir -p /etc/alsa && \
    echo 'pcm.!default { type plug slave.pcm "null" }' > /etc/alsa/asound.conf

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install uv and Python dependencies
RUN pip install --no-cache-dir uv \
    && uv pip install --system -e .

# Copy application code
COPY main.py register_bot.py ./
COPY src/ ./src/
COPY assets/ ./assets/

# Create necessary directories
RUN mkdir -p /app/data/recordings /app/logs

# Create non-root user
RUN useradd -m -u 1000 voicebot \
    && chown -R voicebot:voicebot /app

# Switch to non-root user
USER voicebot

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH \
    AUDIODEV=null

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import pjsua2; print('OK')" || exit 1

# Volumes for persistent data
VOLUME ["/app/data/recordings", "/app/assets/audio"]

# Expose SIP ports
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