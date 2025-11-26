# Stage 1: Build PJSIP from source (CPU-only, no GPU needed)
FROM python:3.11-slim AS builder

ARG PJSIP_VERSION=2.14

# Install build dependencies with cache mount
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
    make install

# Build Python bindings
WORKDIR /tmp/pjproject-${PJSIP_VERSION}/pjsip-apps/src/swig/python
RUN make && python3 setup.py install

# Stage 2: Build Python dependencies with GPU support
FROM nvidia/cuda:11.4.3-cudnn8-runtime-ubuntu20.04 AS python-deps-builder

# Install Python 3.11
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Make Python 3.11 default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

WORKDIR /app
COPY pyproject.toml ./

# Install PyTorch with CUDA 11.3 support (compatible with CUDA 11.4 driver)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install \
    torch==2.1.0+cu118 \
    torchaudio==2.1.0+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install \
    elasticsearch==7.17.9 \
    python-dotenv>=1.0.0 \
    requests>=2.25.0 \
    transformers>=4.35.0 \
    accelerate>=0.24.0 \
    sentencepiece>=0.1.99 \
    numpy>=1.21.0 \
    pytest>=7.0.0 \
    pytest-cov>=4.0.0

# Stage 3: Final runtime image with GPU support
FROM nvidia/cuda:11.4.3-cudnn8-runtime-ubuntu20.04

# Install Python 3.11 and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-distutils \
    libssl1.1 \
    libopus0 \
    libspeex1 \
    libspeexdsp1 \
    libgsm1 \
    libasound2 \
    libasound2-plugins \
    alsa-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Make Python 3.11 default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Copy PJSIP libraries and bindings from builder
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/include/ /usr/local/include/
COPY --from=builder /usr/local/lib/python3.11/site-packages/pjsua2* /usr/local/lib/python3.11/dist-packages/
COPY --from=builder /usr/local/lib/python3.11/site-packages/_pjsua2* /usr/local/lib/python3.11/dist-packages/

# Copy Python packages from deps builder
COPY --from=python-deps-builder /install /usr/local

# Update library cache
RUN ldconfig

# Create ALSA config for null audio device
RUN mkdir -p /etc/alsa && \
    echo 'pcm.!default { type plug slave.pcm "null" }' > /etc/alsa/asound.conf

WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY assets/ ./assets/

# Create necessary directories
RUN mkdir -p /app/data/recordings /app/logs /app/.cache/huggingface

# Create non-root user
RUN useradd -m -u 1000 voicebot && \
    chown -R voicebot:voicebot /app

USER voicebot

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH \
    AUDIODEV=null \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    HF_HOME=/app/.cache/huggingface \
    CUDA_VISIBLE_DEVICES=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import pjsua2; import torch; assert torch.cuda.is_available(); print('OK')" || exit 1

# Persistent volumes
VOLUME ["/app/data/recordings", "/app/assets/audio", "/app/.cache/huggingface"]

# SIP and RTP ports
EXPOSE 5060/udp 10000-20000/udp

# Run the voicebot (ASR disabled by default; pass --enable-asr to enable)
CMD ["python3", "/app/src/pjsua_bot/register_bot.py", "--user", "1004", "--auth-user", "1004", "--password", "05e858b1bbd57d5b1f42fbdbdf5c7616", "--domain", "178.239.151.95", "--transport", "udp", "--local-port", "0", "--wait-seconds", "20", "--stay-online", "--auto-answer", "--play-file", "/app/assets/audio/welcome_message.wav", "--message-duration", "8", "--hangup-delay", "2", "--enable-recording", "--enable-vad", "--silence-after-speech-sec", "3.0", "--vad-threshold", "0.5", "--goodbye-file", "/app/assets/audio/goodbye_voice.wav"]
