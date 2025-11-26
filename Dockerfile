FROM nvidia/cuda:11.4.3-cudnn8-runtime-ubuntu20.04

ARG PJSIP_VERSION=2.14

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && apt-get clean \
    && wget

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

# Build Python bindings
WORKDIR /tmp/pjproject-${PJSIP_VERSION}/pjsip-apps/src/swig/python
RUN make && python3 setup.py install

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY assets/ ./assets/
# COPY goodbye_voice.wav /app/assets/audio/goodbye_voice.wav

# Create necessary directories
RUN mkdir -p /app/data/recordings /app/logs

# Create non-root user
RUN useradd -m -u 1000 voicebot && \
    chown -R voicebot:voicebot /app

USER voicebot

# ALSA null device config
RUN mkdir -p /etc/alsa && \
    echo 'pcm.!default { type plug slave.pcm "null" }' > /etc/alsa/asound.conf

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH \
    AUDIODEV=null

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import pjsua2; print('OK')" || exit 1

# Persistent volumes
VOLUME ["/app/data/recordings", "/app/assets/audio"]

# SIP and RTP ports
EXPOSE 5060/udp 10000-20000/udp

# Run the voicebot
CMD ["python3", "/app/src/pjsua_bot/register_bot.py", "--user", "1004", "--auth-user", "1004", "--password", "05e858b1bbd57d5b1f42fbdbdf5c7616", "--domain", "178.239.151.95", "--transport", "udp", "--local-port", "0", "--wait-seconds", "20", "--stay-online", "--auto-answer", "--play-file", "/app/assets/audio/welcome_message.wav", "--message-duration", "8", "--hangup-delay", "2", "--enable-recording", "--enable-vad", "--silence-after-speech-sec", "3.0", "--vad-threshold", "0.5", "--goodbye-file", "/app/assets/audio/goodbye_voice.wav"]
