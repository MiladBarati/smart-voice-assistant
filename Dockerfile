FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

ARG PJSIP_VERSION=2.14

# Set timezone and non-interactive mode
ENV PYTORCH_JIT=0
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
    libsndfile1 \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    swig \
    && rm -rf /var/lib/apt/lists/*

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

# Install soundfile with bundled libsndfile first
RUN uv pip install --system --python python3.11 soundfile>=0.12.1

# Install other dependencies
RUN uv pip install --system --python python3.11 -r pyproject.toml

# Copy application code
COPY src/ ./src/
COPY assets/ ./assets/

# Create necessary directories
RUN mkdir -p /app/recordings /app/logs

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
    AUDIODEV=null \
    PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PYTORCH_JIT=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3.11 -c "import pjsua2; print('OK')" || exit 1

# Persistent volumes
VOLUME ["/app/recordings", "/app/assets/audio"]

# SIP and RTP ports
EXPOSE 5060/udp 10000-20000/udp

# Run the voicebot
# SIP credentials and domain must be provided via environment variables
CMD ["sh", "-c", "python3.11 /app/src/pjsua_bot/register_bot.py \
    --user \"${SIP_USER}\" \
    --auth-user \"${SIP_AUTH_USER:-${SIP_USER}}\" \
    --password \"${SIP_PASSWORD}\" \
    --domain \"${SIP_DOMAIN}\" \
    --transport \"${SIP_TRANSPORT:-udp}\" \
    --local-port \"${SIP_LOCAL_PORT:-0}\" \
    --wait-seconds \"${SIP_WAIT_SECONDS:-20}\" \
    --stay-online \
    --auto-answer \
    --play-file \"/app/assets/audio/welcome_message.wav\" \
    --message-duration \"${SIP_MESSAGE_DURATION:-8}\" \
    --hangup-delay \"${SIP_HANGUP_DELAY:-2}\" \
    --enable-recording \
    --recording-path \"/app/recordings\" \
    --enable-vad \
    --silence-after-speech-sec \"${SIP_SILENCE_AFTER_SPEECH_SEC:-3.0}\" \
    --vad-threshold \"${SIP_VAD_THRESHOLD:-0.5}\" \
    --goodbye-file \"/app/assets/audio/goodbye_voice.wav\" \
    --enable-asr"]