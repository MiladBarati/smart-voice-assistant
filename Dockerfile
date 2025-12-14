# Stage 1: Build PJSIP (cached separately for faster rebuilds)
FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04 AS pjsip-builder

ARG PJSIP_VERSION=2.14

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies with cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    ca-certificates \
    libssl-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libgsm1-dev \
    swig \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
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
RUN mkdir -p /usr/local/lib/python3.11/site-packages && \
    make && \
    python3.11 setup.py install

# Stage 2: Final runtime image
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

ARG PJSIP_VERSION=2.14

# Set timezone and non-interactive mode
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install runtime dependencies with cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libssl-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libgsm1-dev \
    libsndfile1 \
    ffmpeg \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install gosu from official GitHub release (recommended for Docker)
RUN set -eux; \
    GOSU_VERSION=1.17; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
    amd64) GOSU_ARCH='amd64' ;; \
    arm64) GOSU_ARCH='arm64' ;; \
    *) echo >&2 "error: unsupported architecture: $arch"; exit 1 ;; \
    esac; \
    curl -L -o /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-${GOSU_ARCH}"; \
    chmod +x /usr/local/bin/gosu; \
    chown root:root /usr/local/bin/gosu; \
    gosu --version

# Set python3.11 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Copy PJSIP libraries and Python bindings from builder stage
COPY --from=pjsip-builder /usr/local/lib/ /usr/local/lib/
COPY --from=pjsip-builder /usr/local/include/ /usr/local/include/

# Update library cache
RUN ldconfig

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies with uv (system Python) using cache
WORKDIR /app
COPY pyproject.toml uv.lock ./

# CRITICAL: Install PyTorch with CUDA 12.8 support BEFORE other dependencies
# Matching local environment exactly (2.8.0+cu128)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --python python3.11 --no-deps \
    --index-url https://download.pytorch.org/whl/cu128 \
    torch==2.8.0+cu128 \
    torchaudio==2.8.0+cu128

# Install soundfile with bundled libsndfile (with cache)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --python python3.11 soundfile>=0.12.1

# Install onnxruntime-gpu for ONNX model support (avoids PyTorch 2.8.0 TorchScript compatibility issues)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --python python3.11 onnxruntime-gpu>=1.16.0

# Install all other dependencies from pyproject.toml
# torch/torchaudio should be removed from pyproject.toml dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --python python3.11 -r pyproject.toml

# Copy application code
COPY src/ ./src/
COPY assets/ ./assets/

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/recordings /app/logs

# Create non-root user
RUN useradd -m -u 1000 voicebot && \
    chown -R voicebot:voicebot /app

# ALSA null device config for voicebot user
RUN mkdir -p /home/voicebot/.config/alsa && \
    echo 'pcm.!default { type plug slave.pcm "null" }' > /home/voicebot/.config/alsa/asound.conf && \
    chown -R voicebot:voicebot /home/voicebot/.config

# Environment variables for CUDA
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib:/usr/local/cuda/lib64:$LD_LIBRARY_PATH \
    AUDIODEV=null \
    PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PYTORCH_JIT=0 \
    CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    INTENT_CLASSIFIER=ollama \
    OLLAMA_URL=http://host.docker.internal:11434 \
    OLLAMA_MODEL=qwen2.5:14b \
    OLLAMA_USE_CPU= \
    HF_HOME=/app/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/app/.cache/huggingface/hub \
    TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers \
    TORCH_HOME=/app/.cache/torch \
    FAIRSEQ2_CACHE=/app/.cache/fairseq2 \
    XDG_CACHE_HOME=/app/.cache

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3.11 -c "import pjsua2; import torch; assert torch.cuda.is_available(), 'CUDA not available'; print('OK')" || exit 1

# Persistent volumes
VOLUME ["/app/recordings", "/app/assets/audio"]

# SIP and RTP ports
EXPOSE 5060/udp 10000-20000/udp

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Run the voicebot
CMD ["sh", "-c", "python3.11 /app/src/pjsua_bot/register_bot.py \
    --user \"${SIP_USER:-1004}\" \
    --auth-user \"${SIP_AUTH_USER:-1004}\" \
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
    --silence-after-speech-sec \"${SIP_SILENCE_AFTER_SPEECH_SEC:-1.0}\" \
    --vad-threshold \"${SIP_VAD_THRESHOLD:-0.5}\" \
    --goodbye-file \"/app/assets/audio/goodbye_voice.wav\" \
    --enable-asr \
    --asr-model \"${ASR_MODEL:-omniASR_LLM_3B}\" \
    --enable-intent \
    --intent-classifier \"${INTENT_CLASSIFIER:-ollama}\" \
    --ollama-url \"${OLLAMA_URL:-http://host.docker.internal:11434}\" \
    --ollama-model \"${OLLAMA_MODEL:-qwen2.5:7b}\" \
    ${OLLAMA_USE_CPU:+--ollama-use-cpu}"]