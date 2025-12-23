# PJSUA2 SIP Registration & Call Bot


A comprehensive Python toolkit for SIP/VoIP functionality using PJSUA2, including registration, outbound/inbound call handling, automated audio playback, voice activity detection, automatic speech recognition, and intelligent intent classification.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Resources](#resources)

## 🎯 Overview

This project provides Python scripts for interacting with SIP servers (like Asterisk, FreeSWITCH, or any SIP-compliant PBX) using the PJSUA2 library. It includes both minimal working examples and a production-ready bot with comprehensive features including AI-powered intent classification for automated FAQ responses.

## ✨ Features

### Core SIP Functionality
- **SIP Registration**: Register with SIP servers using various authentication methods
- **Inbound Call Handling**: Accept and process incoming calls with auto-answer capability
- **Outbound Calls**: Make calls to SIP extensions or full URIs
- **Multiple Transports**: Support for UDP, TCP, and TLS
- **NAT Traversal**: Proper handling of NAT scenarios
- **Busy Call Handling**: Automatic rejection of incoming calls when already busy (486 Busy Here)
- **Caller ID Validation**: Configurable caller ID filtering for security

### Audio & Media
- **Audio Playback**: Play WAV files to remote party during calls (e.g., welcome messages, IVR)
- **Voice Recording**: Capture incoming caller audio streams and outgoing bot audio to separate WAV files
- **Automatic Audio Duration Detection**: Reads WAV file duration for precise playback timing
- **Goodbye & Waiting Messages**: Configurable goodbye and waiting voice playback

### Voice Activity Detection (VAD)
- **Real-time Speech Detection**: Using Silero VAD with automatic chunk segmentation
- **VAD Metrics Logging**: Speech duration, chunk count, silence duration, and confidence scores logged to Elasticsearch
- **Smart Hangup**: Automatically hang up based on VAD silence detection

### Automatic Speech Recognition (ASR)
- **Whisper-based ASR**: OpenAI Whisper models via transformers (Persian/Farsi and 100+ languages)
- **Omnilingual ASR**: Meta SeamlessM4T v2 models for superior multilingual support (100+ languages with translation)
- **Live Transcription**: Real-time ASR transcription during calls with chunk-based processing
- **Model Selection**: Choose between `omniASR_CTC_1B` and `omniASR_CTC_350M` models

### Intent Classification (NEW!)
- **Rule-Based Classification**: Fast keyword matching with Persian text normalization
- **LLM-Based Classification**: Ollama integration with Qwen models for intelligent classification
- **58+ FAQ Intents**: Pre-configured Persian/Farsi FAQ responses for IT help desk
- **Custom FAQ Support**: Load custom FAQ configurations from JSON files
- **Automatic Response Playback**: Play audio responses based on detected intent
- **Fallback Support**: Graceful fallback from LLM to rule-based when Ollama unavailable

### Infrastructure & Operations
- **Event-Driven**: Non-blocking event loop with proper PJSUA2 event pumping
- **Signal Handling**: Graceful shutdown on Ctrl+C / SIGTERM
- **Extensive Logging**: Configurable log levels for debugging
- **Elasticsearch Integration**: Call logging and analytics with VAD metrics
- **Comprehensive Testing**: Unit testing framework with pytest, coverage reporting, and mock support
- **Docker Support**: Multi-stage Dockerfile with optimized build and runtime images
- **Code Quality**: Pre-commit hooks with Ruff, Black, and mypy for linting, formatting, and type checking

## 📦 Prerequisites

- **Python**: 3.9 or higher (3.11 recommended)
- **PJSUA2**: Python bindings for PJSIP library
- **FFmpeg** (optional): For audio file conversion to WAV format
- **Ollama** (optional): For LLM-based intent classification

### Installing PJSUA2

PJSUA2 Python bindings typically need to be compiled from source or installed via platform-specific packages:

```bash
# Option 1: Build from source (recommended for latest version)
# Download PJSIP from https://www.pjsip.org/download.htm
# Follow build instructions at https://docs.pjsip.org/en/latest/get-started/posix/build.html

# Option 2: Use pre-built packages (if available for your platform)
# Check your distribution's package manager
```

### Installing Ollama (for LLM Intent Classification)

```bash
# Linux/WSL
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull recommended model
ollama pull qwen2.5:3b
```

## 🚀 Installation

1. **Clone or download this repository**

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**:
   ```bash
   pip install pjsua2  # If available via pip
   # Otherwise, ensure PJSUA2 is installed system-wide or in venv

   # Install Elasticsearch client (version compatible with server)
   pip install "elasticsearch>=7.0.0,<8.0.0"
   
   # Install python-dotenv for environment variable support
   pip install python-dotenv
   
   # Install VAD dependencies (optional, for voice activity detection)
   pip install torch torchaudio
   
   # Install ASR dependencies (optional, for automatic speech recognition)
   # Option 1: Whisper-based ASR (cross-platform)
   pip install transformers accelerate sentencepiece
   
   # Option 2: Omnilingual ASR (Linux/WSL only, recommended for multilingual)
   pip install omnilingual-asr
   
   # Install testing dependencies
   pip install pytest pytest-cov
   ```

## 🚦 Quick Start

### Test Basic Registration

```bash
# Using the minimal working example (simplified registration)
python src/pjsua_bot/mwe_register.py \
  --user YOUR_EXTENSION \
  --password YOUR_PASSWORD \
  --domain YOUR_SIP_SERVER

# Or using the full bot (recommended)
python -m src.pjsua_bot.register_bot \
  --user YOUR_EXTENSION \
  --password YOUR_PASSWORD \
  --domain YOUR_SIP_SERVER
```

### Receive Incoming Calls

```bash
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online
```

### Enable Live Transcription (ASR)

```bash
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording \
  --enable-vad \
  --enable-asr
```

### Enable Intent Classification (Rule-Based)

```bash
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording \
  --enable-vad \
  --enable-asr \
  --enable-intent
```

### Enable Intent Classification (LLM via Ollama)

```bash
# Make sure Ollama is running with the model loaded
ollama pull qwen2.5:3b

python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording \
  --enable-vad \
  --enable-asr \
  --enable-intent \
  --intent-classifier ollama \
  --ollama-model qwen2.5:3b
```

### Play Welcome Message

```bash
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --play-file assets/audio/welcome_message.wav
```

### Make Outbound Call

```bash
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --dest 1002
```

### Transcribe Audio Recordings

```bash
# Using Whisper-based ASR
python examples/asr_usage_example.py

# Using Omnilingual ASR (Linux/WSL only)
python examples/omnilingual_asr_example.py
```

**👉 For detailed step-by-step instructions, see [Getting Started Guide](docs/GETTING_STARTED.md)**

### Complete CLI Options

The `register_bot.py` script supports the following command-line arguments:

#### Required Arguments
- `--user`: SIP username or extension
- `--password`: SIP password
- `--domain`: Registrar/realm host or domain

#### SIP Configuration
- `--auth-user`: Authentication username (if different from user)
- `--local-port`: Local SIP port to bind (default: 5060)
- `--transport`: SIP transport protocol - `udp`, `tcp`, or `tls` (default: udp)
- `--tls-verify`: Verify TLS server certificate (when using TLS transport)
- `--outbound-proxy`: Outbound proxy URI (e.g., `sip:host:5060;lr`)

#### Call Behavior
- `--stay-online`: Keep endpoint running to receive calls
- `--auto-answer`: Answer incoming calls with 200 OK (enabled by default)
- `--no-auto-answer`: Disable auto-answering of incoming calls
- `--dest`: Destination SIP URI or extension for outbound call (e.g., `sip:1002@host` or just `1002`)
- `--hangup-seconds`: Auto hangup after N seconds of connection; 0 to disable (default: 0)
- `--wait-seconds`: Time to wait for registration/connect (default: 10)

#### Audio Playback
- `--play-file`: Path to WAV file to play when call connects (default: `welcome_message.wav`)
- `--goodbye-file`: Path to WAV file to play before hanging up (default: `goodbye_voice.wav`)
- `--message-duration`: Fallback duration in seconds if WAV file cannot be read (default: 5)
- `--hangup-delay`: Deprecated: fixed delay; overridden by VAD-based hangup if enabled (default: 2)

#### Recording & Analysis
- `--enable-recording`: Enable voice capture for incoming calls (default: False)
- `--recording-path`: Base directory for storing recorded audio files (default: `./artifacts/recordings`)
- `--enable-vad`: Enable Silero VAD-based hangup after caller silence (default: False)
- `--silence-after-speech-sec`: Seconds of silence after last caller speech to hang up (default: 3.0)
- `--vad-threshold`: Silero VAD speech probability threshold (default: 0.5)
- `--enable-asr`: Enable ASR for live and final transcription (default: False)
- `--asr-model`: ASR model to use: `omniASR_CTC_1B` or `omniASR_CTC_350M` (default: omniASR_CTC_1B)

#### Intent Classification
- `--enable-intent`: Enable intent classification from transcription (default: False)
- `--intent-classifier`: Classifier type: `rule-based` (keyword matching) or `ollama` (LLM-based) (default: rule-based)
- `--ollama-url`: Ollama API base URL (default: http://localhost:11434)
- `--ollama-model`: Ollama model name (default: qwen2.5:3b). Using 1.5b/3b recommended for GPUs with <8GB VRAM
- `--ollama-use-cpu`: Attempt to force CPU usage for Ollama (hint only; set OLLAMA_NUM_GPU=0 for true CPU mode)
- `--faq-config`: Path to custom FAQ JSON config file (optional)

#### Logging
- `--log-level`: Endpoint log level 0-6, higher = more verbose (default: 3)

## 🐳 Docker Deployment

### Quick Start with Docker

The project includes a multi-stage Dockerfile for production deployment:

```bash
# Build the Docker image
docker build -t pjsua-bot:latest .

# Run with Docker
docker run -d \
  --name sipbot \
  -p 5060:5060/udp \
  -v ./artifacts/recordings:/app/data/recordings \
  -e ES_HOST=your-elasticsearch-host \
  pjsua-bot:latest
```

### Docker Compose (Recommended)

For production deployment with Elasticsearch integration:

```bash
# Start the bot and connect to existing Elasticsearch
docker-compose up -d

# View logs
docker-compose logs -f sipbot

# Stop the bot
docker-compose down
```

### Docker with Omnilingual ASR

For enhanced multilingual ASR support with omnilingual-asr:

```bash
# Build and run with omnilingual ASR support
docker-compose -f docker-compose.omnilingual.yml up -d

# View logs
docker-compose -f docker-compose.omnilingual.yml logs -f

# Build the image manually
docker build -f Dockerfile.omnilingual -t pjsua-bot-omnilingual:latest .
```

**Note**: Omnilingual ASR requires Linux/WSL environment. The `Dockerfile.omnilingual` includes all necessary dependencies for omnilingual-asr models.

**Configuration via Environment Variables:**

Set these in your `.env` file or docker-compose.yml:

- `ES_HOST`: Elasticsearch host (default: elasticsearch)
- `ES_PORT`: Elasticsearch port (default: 9200)
- `ES_USERNAME`: Elasticsearch username (default: elastic)
- `ES_PASSWORD`: Elasticsearch password
- `ES_USE_SSL`: Use SSL for Elasticsearch (default: false)
- `ES_VERIFY_CERTS`: Verify SSL certificates (default: false)
- `ELASTIC_INDEX_PREFIX`: Index prefix for Elasticsearch (default: pjsua-calls)
- `LOG_LEVEL`: PJSUA2 log level 0-5 (default: 3)

**Docker Features:**

- Multi-stage build for optimized image size
- PJSIP 2.14 compiled from source with optimized codecs
- Python 3.11 slim base image
- Non-root user for security
- Health checks for container monitoring
- Persistent volumes for recordings and audio assets
- Automatic library dependency management
- Support for both standard and omnilingual ASR variants
- Model caching for faster startup times

## 📁 Project Structure

```
pjsua-installation/
├── src/
│   └── pjsua_bot/
│       ├── __init__.py              # Package exports
│       ├── utils.py                 # Utility functions
│       ├── account.py               # Account management class
│       ├── register_bot.py          # Main entry point (~900 lines)
│       ├── elasticsearch_client.py  # Elasticsearch integration
│       ├── asr.py                   # Automatic Speech Recognition - Omnilingual
│       ├── mwe_register.py          # Minimal working example
│       ├── calls/                   # Call handling modules
│       │   ├── __init__.py          # Call package exports
│       │   ├── any_call.py          # Advanced call handling
│       │   ├── out_call.py          # Outbound call handling
│       │   ├── goodbye.py           # Goodbye playback mixin
│       │   ├── recording_cleanup.py # Recording cleanup utilities
│       │   └── mixins/              # Reusable call handler mixins
│       │       ├── __init__.py      # Mixin package exports
│       │       ├── asr_support.py   # ASR integration mixin
│       │       ├── call_media_handler.py # Media handling mixin
│       │       ├── call_state_handler.py # State management mixin
│       │       ├── event_logger.py  # Event logging mixin
│       │       ├── intent_handler.py # Intent classification mixin
│       │       └── playback_monitor.py # Playback monitoring mixin
│       ├── intent/                  # Intent classification modules (NEW!)
│       │   ├── __init__.py          # Intent package exports
│       │   ├── classifier.py        # Base classifier & rule-based implementation
│       │   ├── faq_config.py        # Persian FAQ configuration (58+ intents)
│       │   └── ollama_classifier.py # LLM-based classifier using Ollama
│       └── vad/                     # Voice Activity Detection modules
│           ├── __init__.py          # VAD package exports
│           ├── silero.py            # Silero VAD implementation
│           ├── audio_reader.py      # Audio stream reading
│           ├── chunk_manager.py     # Voice chunk management
│           ├── silence.py           # Silence tracking
│           ├── types.py             # VAD type definitions
│           └── config.py            # VAD configuration
├── examples/                    # Usage examples
│   ├── asr_usage_example.py    # ASR transcription example (Whisper)
│   ├── omnilingual_asr_example.py # Omnilingual ASR example
│   ├── measure_inference_time.py # ASR performance measurement
│   ├── verify_cache.py         # Model cache verification
│   └── timing_utils.py         # Timing utilities for examples
├── tests/                       # Test suite
│   ├── __init__.py             # Test package
│   ├── conftest.py             # Pytest fixtures and configuration
│   ├── test_main.py            # Main module tests
│   ├── test_account.py         # Account tests
│   ├── test_intent_classifier.py # Intent classifier tests
│   ├── test_intent_handler_mixin.py # Intent handler mixin tests
│   ├── test_intent_phase1.py   # Phase 1 intent tests
│   ├── test_ollama_classifier.py # Ollama classifier tests
│   ├── test_elasticsearch_client.py # Elasticsearch tests
│   └── [additional test files]
├── scripts/                     # Utility scripts
│   ├── run_tests.py            # Test runner with coverage
│   ├── check_ollama.py         # Ollama connectivity check
│   ├── test_intent_classifier.py # Intent classifier testing
│   ├── test_connectivity.py    # Connectivity testing
│   └── test_elasticsearch.py   # Elasticsearch connectivity test
├── docs/                        # Documentation
│   ├── GETTING_STARTED.md
│   ├── USAGE_GUIDE.md
│   ├── CONFIGURATION.md
│   ├── VOICE_RECORDING.md
│   ├── AUDIO_PLAYBACK.md
│   ├── ELASTICSEARCH.md
│   ├── TROUBLESHOOTING.md
│   ├── TECHNICAL_DETAILS.md
│   ├── TESTING.md
│   ├── INTENT_CLASSIFICATION_IMPLEMENTATION_GUIDE.md  # NEW!
│   ├── RASA_INTEGRATION_GUIDE.md  # NEW!
│   └── [additional technical docs]
├── rasa-integration/            # Rasa NLU integration (optional)
│   ├── README.md               # Rasa setup instructions
│   ├── setup.sh                # Setup script
│   └── install-python3.10.sh   # Python 3.10 installer for Rasa
├── assets/                      # Static assets
│   └── audio/                   # Audio files (WAV, M4A)
├── recordings/                  # Call recordings (organized by date)
├── infrastructure/              # Infrastructure definitions
│   ├── freepbx/                # FreePBX Docker setup
│   └── nginx/                  # Nginx reverse proxy setup
├── Dockerfile                  # Multi-stage Docker build
├── Dockerfile.omnilingual      # Docker build with omnilingual ASR
├── docker-compose.yml          # Docker Compose configuration
├── docker-compose.omnilingual.yml # Docker Compose with omnilingual
├── pyproject.toml              # Project configuration and dependencies
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
└── uv.lock                     # UV dependency lock file
```

### Module Breakdown

#### Core Modules (`src/pjsua_bot/`)

- **`utils.py`**: Common utility functions
  - `parse_sip_user()`, `setup_logging()`, `get_wav_duration()`
  - `ensure_recording_directory()`, `pump_events()`, `wait_until()`
  - `generate_unique_id()` for UUID-based call identification

- **`account.py`**: SIP account management
  - `Account` class with registration and incoming call handling
  - Event-driven callback system for call state changes
  - Busy call rejection and caller ID validation

- **`register_bot.py`** (~900 lines): Main entry point and CLI
  - Comprehensive CLI argument parsing with 35+ options
  - Bot lifecycle management and graceful shutdown
  - Integration of all components (account, calls, VAD, ASR, intent, Elasticsearch)
  - Signal handling for SIGINT/SIGTERM
  - Resource cleanup for models and connections

- **`elasticsearch_client.py`**: Elasticsearch integration
  - `ElasticsearchLogger` class for event logging
  - Call record management with VAD metrics
  - Automatic index creation and schema management

- **`asr.py`**: Automatic Speech Recognition (Omnilingual backend)
  - `ASRService` class using Meta SeamlessM4T v2
  - Support for 100+ languages with automatic detection
  - Model selection: `omniASR_CTC_1B` or `omniASR_CTC_350M`

#### Intent Classification Package (`src/pjsua_bot/intent/`) - NEW!

- **`classifier.py`**: Base classifier interface and rule-based implementation
  - `IntentClassifier` abstract base class
  - `RuleBasedClassifier` with Persian text normalization
  - Weighted keyword matching with confidence scoring

- **`faq_config.py`**: Persian FAQ configuration
  - 58+ predefined intents for IT help desk
  - Keywords, questions, and response text for each intent
  - Audio file paths for response playback
  - System prompt generator for Ollama

- **`ollama_classifier.py`**: LLM-based classifier
  - `OllamaClassifier` using Qwen models via Ollama API
  - Model preloading for faster first response
  - Automatic fallback to rule-based on errors
  - CPU/GPU mode support
  - Connection pooling for performance

#### Call Handling Package (`src/pjsua_bot/calls/`)

- **`any_call.py`**: Advanced call handler
  - `AnyCall` class for full-featured call management
  - Audio recording (incoming/outgoing streams)
  - VAD, ASR, and intent classification integration

- **`out_call.py`**: Outbound call handler
  - `OutCall` class for making calls
  - Simple playback and hangup logic

- **`goodbye.py`**: Goodbye playback mixin
  - Waiting voice playback during silence periods
  - Configurable hangup timing

#### Call Handler Mixins (`src/pjsua_bot/calls/mixins/`)

- **`asr_support.py`**: ASR integration mixin
- **`call_media_handler.py`**: Media handling mixin
- **`call_state_handler.py`**: State management mixin
- **`event_logger.py`**: Event logging mixin
- **`intent_handler.py`**: Intent classification mixin (NEW!)
- **`playback_monitor.py`**: Playback monitoring mixin

#### Voice Activity Detection Package (`src/pjsua_bot/vad/`)

- **`silero.py`**: Silero VAD implementation
- **`audio_reader.py`**: Audio stream processing
- **`chunk_manager.py`**: Voice chunk management
- **`silence.py`**: Silence tracking
- **`config.py`**: VAD configuration
- **`types.py`**: VAD type definitions

### Importing and Using Modules

```python
# Import from package root (recommended)
from src.pjsua_bot import Account, OutCall, AnyCall, main, setup_logging

# Import from specific modules
from src.pjsua_bot.account import Account
from src.pjsua_bot.calls import OutCall, AnyCall
from src.pjsua_bot.utils import setup_logging, pump_events, wait_until
from src.pjsua_bot.asr import ASRService, ASRConfig
from src.pjsua_bot.vad import SileroVAD, VADConfig, VoiceChunk
from src.pjsua_bot.elasticsearch_client import ElasticsearchLogger, es_logger

# Import intent classification (NEW!)
from src.pjsua_bot.intent import RuleBasedClassifier, FAQS
from src.pjsua_bot.intent.ollama_classifier import OllamaClassifier

# Use the main function
from src.pjsua_bot import main
main()
```

## 📚 Documentation

### Getting Started
- **[Getting Started Guide](docs/GETTING_STARTED.md)** - Step-by-step quick start tutorial
- **[Usage Guide](docs/USAGE_GUIDE.md)** - Detailed usage examples and common use cases

### Configuration
- **[Configuration Options](docs/CONFIGURATION.md)** - Complete CLI options and environment variables
- **[Environment Variables](docs/CONFIGURATION.md#environment-variables)** - Secure configuration management

### Features
- **[Audio Playback](docs/AUDIO_PLAYBACK.md)** - Playing WAV files and automatic duration detection
- **[Voice Recording](docs/VOICE_RECORDING.md)** - Recording incoming/outgoing audio streams
- **[Intent Classification](docs/INTENT_CLASSIFICATION_IMPLEMENTATION_GUIDE.md)** - AI-powered FAQ response system (NEW!)

### Integration & Testing
- **[Elasticsearch Integration](docs/ELASTICSEARCH.md)** - Call logging and data storage with VAD metrics
- **[Testing Framework](docs/TESTING.md)** - Unit tests and coverage reporting
- **[Rasa Integration](docs/RASA_INTEGRATION_GUIDE.md)** - NLU integration guide (NEW!)

### Infrastructure
- **[Docker Deployment](#-docker-deployment)** - Production deployment with Docker and Docker Compose
- **[FreePBX Setup](infrastructure/freepbx/README.md)** - Local FreePBX test environment
- **[Nginx Configuration](infrastructure/nginx/readme.md)** - Reverse proxy setup for web interfaces

### Reference
- **[Technical Details](docs/TECHNICAL_DETAILS.md)** - Implementation details and architecture
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### ASR, Docker & WSL Guides
- **ASR**
  - [ASR Migration Guide](docs/ASR_MIGRATION_GUIDE.md)
  - [ASR Quick Reference](docs/ASR_QUICK_REFERENCE.md)
- **Docker (recommended)**
  - [Docker Quick Start](docs/DOCKER_QUICK_START.md)
  - [Docker Setup Guide](docs/DOCKER_SETUP_GUIDE.md)
  - [Docker Troubleshooting](docs/DOCKER_TROUBLESHOOTING.md)
- **WSL**
  - [WSL Quick Start](docs/WSL_QUICK_START.md)
  - [WSL Setup Guide](docs/WSL_SETUP_GUIDE.md)
  - [Dual Environment Guide (Windows + WSL)](docs/DUAL_ENVIRONMENT_GUIDE.md)
- **Omnilingual ASR Overview**
  - [Omnilingual ASR Summary](docs/OMNILINGUAL_ASR_SUMMARY.md)
  - [Omnilingual ASR Options](docs/OMNILINGUAL_ASR_OPTIONS.md)
  - [Omnilingual ASR Setup](docs/OMNILINGUAL_ASR_SETUP.md)
- **Performance & Caching**
  - [Model Cache Guide](docs/MODEL_CACHE_GUIDE.md)
  - [Inference Time Guide](docs/INFERENCE_TIME_GUIDE.md)
- **Index**
  - [Setup Documentation Index](docs/SETUP_INDEX.md)

## 🧰 Development & Testing

### Quality Gates & Pre-commit Hooks

This repository enforces linting, formatting, and type checking on commit via pre-commit hooks.

**Setup:**

```bash
# Install dev tools with pip
pip install ruff black mypy pre-commit

# Or with uv (if available)
uv pip install --system --group dev

# Install pre-commit hooks
pre-commit install

# Run across the repo once
pre-commit run --all-files
```

**Tools:**

- **Ruff** (v0.6.9): Fast Python linter and import sorter
- **Black** (v24.8.0): Code formatting (88 character line length)
- **mypy** (v1.11.2): Static type checking

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_main.py

# Run intent classification tests
pytest tests/test_intent_classifier.py tests/test_ollama_classifier.py -v

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src/pjsua_bot --cov-report=html

# Use the test runner script
python scripts/run_tests.py
```

**Test Configuration:**

- Configuration: `pytest.ini`
- Coverage: 30% minimum threshold
- Reports: Terminal, HTML (`artifacts/htmlcov/`), and XML (`artifacts/coverage.xml`)
- Markers: unit, integration, slow, elasticsearch, pjsua

### Project Dependencies

**Managed via:**
- `pyproject.toml`: Primary dependency configuration
- `requirements.txt`: Pip-compatible dependency list
- `uv.lock`: UV dependency lock file for reproducible builds

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install pre-commit hooks (`pre-commit install`)
4. Make your changes
5. Run tests (`pytest`)
6. Commit your changes (pre-commit hooks will run automatically)
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Quality Standards

- Follow PEP 8 style guide (enforced by Black and Ruff)
- Add type hints (checked by mypy)
- Write unit tests for new features
- Maintain or improve test coverage
- Update documentation for user-facing changes

### Areas for Improvement

**High Priority:**
- DTMF handling and IVR menu support
- Configuration file support (YAML/JSON)
- Multiple simultaneous calls management
- WebSocket API for real-time call monitoring
- Kubernetes deployment manifests
- Semantic search-based intent classification (Phase 2)
- TTS integration for dynamic audio responses (Phase 4)

**Medium Priority:**
- SIP MESSAGE support
- Presence/subscription handling
- Enhanced audio playback completion detection
- Video call support
- Call transfer and forwarding
- Rasa NLU integration

**Completed Features:**
- ✅ Call recording (incoming/outgoing streams)
- ✅ Environment variable configuration
- ✅ Voice Activity Detection (VAD)
- ✅ Automatic Speech Recognition (ASR) - Multiple backends
- ✅ Live transcription during calls
- ✅ Elasticsearch integration
- ✅ Docker containerization (standard & omnilingual variants)
- ✅ Modular codebase architecture with mixins
- ✅ Comprehensive testing framework
- ✅ Pre-commit hooks and code quality tools
- ✅ Goodbye and waiting voice playback
- ✅ VAD-based smart hangup
- ✅ **Intent Classification** - Rule-based and LLM (Ollama) (NEW!)
- ✅ **Persian FAQ System** - 58+ IT help desk intents (NEW!)

## 📝 License

This project is provided as-is for educational and development purposes.

## 🆘 Support

For issues specific to:
- **PJSIP/PJSUA2 library**: See [PJSIP Mailing List](https://www.pjsip.org/lists.htm)
- **This project**: Open an issue in the repository
- **SIP server configuration**: Consult your PBX documentation
- **Ollama**: See [Ollama Documentation](https://ollama.ai/docs)

## 📚 Resources

- [PJSIP Official Documentation](https://docs.pjsip.org/)
- [PJSUA2 Book](https://docs.pjsip.org/en/latest/pjsua2/intro.html)
- [SIP RFC 3261](https://www.rfc-editor.org/rfc/rfc3261)
- [Asterisk Documentation](https://docs.asterisk.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Ollama Documentation](https://ollama.ai/docs)
- [Qwen2.5 Models](https://huggingface.co/Qwen)

---

## 📋 Version Information

**Current Version**: 1.1.0  
**Last Updated**: December 2025  
**Python**: 3.9+ (3.11 recommended)  
**PJSUA2**: Compatible with PJSIP 2.x (tested with 2.14)  
**ASR Backends**: Omnilingual (Meta SeamlessM4T v2) & Whisper (transformers)
**Intent Classification**: Rule-based & Ollama (Qwen2.5)

### Changelog

#### v1.1.0 (December 2025) - Intent Classification Release
- 🧠 **Intent Classification**: Added AI-powered intent classification system
  - Rule-based classifier with Persian text normalization
  - LLM-based classifier using Ollama with Qwen models
  - 58+ predefined FAQ intents for IT help desk
  - IntentHandlerMixin for call integration
- 🔌 **Ollama Integration**: Full Ollama API support
  - Model preloading for faster responses
  - CPU/GPU mode support
  - Automatic fallback to rule-based classifier
  - Connection pooling for performance
- 📞 **Call Handling Improvements**:
  - Busy call rejection (486 Busy Here) when already handling a call
  - Caller ID validation (configurable range filtering)
  - Improved resource cleanup on shutdown
- 🎯 **ASR Model Selection**: New `--asr-model` flag for model choice
- 📚 **New Documentation**:
  - Intent Classification Implementation Guide
  - Rasa Integration Guide
- ✅ **Expanded Test Coverage**: New tests for intent classification

#### v1.0.0 (November 2025) - Production Release
- ✨ **Modular architecture**: Refactored into `calls/` and `vad/` subpackages with mixin-based design
- 🎯 **Advanced call handling**: Separated `AnyCall`, `OutCall`, and `GoodbyePlaybackMixin` classes
- 🔊 **Enhanced VAD**: Modular VAD system with audio reader, chunk manager, and silence tracker
- 🎤 **Dual ASR backends**: Support for both Whisper-based and Omnilingual ASR
- 🌐 **Omnilingual ASR**: Meta SeamlessM4T v2 integration for superior multilingual support
- 🔄 **Live transcription**: Real-time ASR transcription during calls
- 🐳 **Docker production ready**: Multi-stage Dockerfile with PJSIP 2.14
- 🔧 **Code quality**: Pre-commit hooks with Ruff, Black, and mypy
- 📦 **Dependency management**: UV lock file for reproducible builds
- 📚 **Comprehensive documentation**: 25+ documentation files
- 🎵 **Enhanced playback**: Goodbye and waiting voice playback support

#### v0.5.0 (October 2025)
- 🎤 **ASR Integration**: Automatic Speech Recognition with Whisper models
- 🌐 **Multi-language support**: Persian/Farsi and 100+ other languages
- 🔇 **Silence tracking**: Enhanced VAD with mutual silence detection

#### v0.4.1 (October 2025)
- 🎙️ **Voice Activity Detection**: Silero VAD integration
- ✂️ **Automatic chunking**: Intelligent voice segment separation
- 📈 **VAD metrics**: Speech duration, chunk count, confidence logging

#### v0.4.0 (September 2025)
- 🏗️ **Modular codebase**: Separated into focused modules
- 📦 **Package structure**: Professional src/package layout

#### v0.3.0 (September 2025)
- ✅ **Testing framework**: Comprehensive pytest suite
- 📊 **Coverage reporting**: HTML, XML, and terminal reports

#### v0.2.0 (August 2025)
- 🆔 **UUID call IDs**: Unique identifiers prevent duplicates
- 📁 **Organized recordings**: Date-based directory structure

#### v0.1.0 (July 2025) - Initial Release
- 📞 **SIP registration**: Basic SIP account registration
- ☎️ **Call handling**: Inbound and outbound call support
- 🔊 **Audio playback**: WAV file playback during calls
- 📼 **Call recording**: Separate incoming/outgoing audio streams
- 🗄️ **Elasticsearch**: Call event logging
