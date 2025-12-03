# PJSUA2 SIP Registration & Call Bot


A comprehensive Python toolkit for SIP/VoIP functionality using PJSUA2, including registration, outbound/inbound call handling, and automated audio playback.

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

This project provides Python scripts for interacting with SIP servers (like Asterisk, FreeSWITCH, or any SIP-compliant PBX) using the PJSUA2 library. It includes both minimal working examples and a production-ready bot with comprehensive features.

## ✨ Features

- **SIP Registration**: Register with SIP servers using various authentication methods
- **Inbound Call Handling**: Accept and process incoming calls with auto-answer capability
- **Outbound Calls**: Make calls to SIP extensions or full URIs
- **Audio Playback**: Play WAV files to remote party during calls (e.g., welcome messages, IVR)
- **Voice Recording**: Capture incoming caller audio streams and outgoing bot audio to separate WAV files with organized storage
- **Voice Activity Detection (VAD)**: Real-time speech detection using Silero VAD with automatic chunk segmentation
- **VAD Metrics Logging**: Speech duration, chunk count, silence duration, and confidence scores logged to Elasticsearch for analytics
- **Automatic Speech Recognition (ASR)**: Transcribe audio recordings using multiple backends:
  - **Whisper-based ASR**: OpenAI Whisper models via transformers (Persian/Farsi and 100+ languages)
  - **Omnilingual ASR**: Meta SeamlessM4T v2 models for superior multilingual support (100+ languages with translation)
- **Live Transcription**: Real-time ASR transcription during calls with chunk-based processing
- **Automatic Audio Duration Detection**: Reads WAV file duration for precise playback timing
- **Auto-Answer**: Automatically answer incoming calls (enabled by default)
- **Smart Hangup**: Automatically hang up after audio playback completes with configurable delay or based on VAD silence detection
- **Unique Call IDs**: Uses UUID-based call IDs to prevent duplicates across program restarts
- **Multiple Transports**: Support for UDP, TCP, and TLS
- **NAT Traversal**: Proper handling of NAT scenarios
- **Event-Driven**: Non-blocking event loop with proper PJSUA2 event pumping
- **Signal Handling**: Graceful shutdown on Ctrl+C / SIGTERM
- **Extensive Logging**: Configurable log levels for debugging
- **Comprehensive Testing**: Unit testing framework with pytest, coverage reporting, and mock support
- **Docker Support**: Multi-stage Dockerfile with optimized build and runtime images
- **Production Ready**: Docker Compose setup for easy deployment with Elasticsearch integration
- **Code Quality**: Pre-commit hooks with Ruff, Black, and mypy for linting, formatting, and type checking

## 📦 Prerequisites

- **Python**: 3.11 or higher
- **PJSUA2**: Python bindings for PJSIP library
- **FFmpeg** (optional): For audio file conversion to WAV format

### Installing PJSUA2

PJSUA2 Python bindings typically need to be compiled from source or installed via platform-specific packages:

```bash
# Option 1: Build from source (recommended for latest version)
# Download PJSIP from https://www.pjsip.org/download.htm
# Follow build instructions at https://docs.pjsip.org/en/latest/get-started/posix/build.html

# Option 2: Use pre-built packages (if available for your platform)
# Check your distribution's package manager
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
- `--waiting-file`: Path to WAV file to play when VAD detects silence (default: `waiting_voice.wav`)
- `--message-duration`: Fallback duration in seconds if WAV file cannot be read (default: 5)
- `--hangup-delay`: Deprecated: fixed delay; overridden by VAD-based hangup if enabled (default: 2)

#### Recording & Analysis
- `--enable-recording`: Enable voice capture for incoming calls (default: False)
- `--recording-path`: Base directory for storing recorded audio files (default: `./recordings`)
- `--enable-vad`: Enable Silero VAD-based hangup after caller silence (default: False)
- `--silence-after-speech-sec`: Seconds of silence after last caller speech to hang up (default: 3.0)
- `--vad-threshold`: Silero VAD speech probability threshold (default: 0.5)
- `--enable-asr`: Enable ASR for live and final transcription (default: False)

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
  -v ./recordings:/app/data/recordings \
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
│       ├── utils.py                 # Utility functions (235 lines)
│       ├── account.py               # Account management class (120 lines)
│       ├── register_bot.py          # Main entry point (533 lines)
│       ├── elasticsearch_client.py  # Elasticsearch integration (547 lines)
│       ├── asr.py                   # Automatic Speech Recognition - Omnilingual (376 lines)
│       ├── asr_whisper.py           # Whisper-based ASR backend (481 lines)
│       ├── asr_omnilingual.py       # Omnilingual ASR wrapper (376 lines)
│       ├── mwe_register.py          # Minimal working example (109 lines)
│       ├── calls/                   # Call handling modules
│       │   ├── __init__.py          # Call package exports
│       │   ├── any_call.py          # Advanced call handling (871 lines)
│       │   ├── out_call.py          # Outbound call handling (122 lines)
│       │   ├── goodbye.py           # Goodbye playback mixin (351 lines)
│       │   ├── recording_cleanup.py # Recording cleanup utilities (351 lines)
│       │   └── mixins/              # Reusable call handler mixins
│       │       ├── __init__.py      # Mixin package exports
│       │       ├── asr_support.py   # ASR integration mixin
│       │       ├── call_media_handler.py # Media handling mixin
│       │       ├── call_state_handler.py # State management mixin
│       │       ├── event_logger.py  # Event logging mixin
│       │       └── playback_monitor.py # Playback monitoring mixin
│       └── vad/                     # Voice Activity Detection modules
│           ├── __init__.py          # VAD package exports
│           ├── silero.py            # Silero VAD implementation (752 lines)
│           ├── audio_reader.py      # Audio stream reading (262 lines)
│           ├── chunk_manager.py     # Voice chunk management (326 lines)
│           ├── silence.py           # Silence tracking (54 lines)
│           ├── types.py             # VAD type definitions (17 lines)
│           └── config.py            # VAD configuration (17 lines)
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
│   ├── test_elasticsearch_client.py # Elasticsearch tests
│   ├── test_batch.py           # Batch processing tests
│   └── test_setup.py           # Setup and configuration tests
├── scripts/                     # Utility scripts
│   ├── run_tests.py            # Test runner with coverage
│   ├── demo_tests.py           # Demo test suite
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
│   └── [additional technical docs]
├── assets/                      # Static assets
│   └── audio/                   # Audio files (WAV, M4A)
├── recordings/                  # Call recordings (organized by date)
├── infrastructure/              # Infrastructure definitions
│   ├── freepbx/                # FreePBX Docker setup
│   └── nginx/                  # Nginx reverse proxy setup
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Docker Compose configuration
├── pyproject.toml              # Project configuration and dependencies
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
└── uv.lock                     # UV dependency lock file
```

### Module Breakdown

#### Core Modules (`src/pjsua_bot/`)

- **`utils.py`** (235 lines): Common utility functions
  - `parse_sip_user()`, `setup_logging()`, `get_wav_duration()`
  - `ensure_recording_directory()`, `pump_events()`, `wait_until()`
  - `generate_unique_id()` for UUID-based call identification

- **`account.py`** (120 lines): SIP account management
  - `Account` class with registration and incoming call handling
  - Event-driven callback system for call state changes

- **`register_bot.py`** (533 lines): Main entry point and CLI
  - Comprehensive CLI argument parsing with 30+ options
  - Bot lifecycle management and graceful shutdown
  - Integration of all components (account, calls, VAD, ASR, Elasticsearch)
  - Signal handling for SIGINT/SIGTERM

- **`elasticsearch_client.py`** (547 lines): Elasticsearch integration
  - `ElasticsearchLogger` class for event logging
  - Call record management with VAD metrics
  - Automatic index creation and schema management
  - Health checking and connection verification

- **`asr.py`** (376 lines): Automatic Speech Recognition (Omnilingual backend - default)
  - `ASRService` class for transcribing audio using omnilingual-asr (Meta SeamlessM4T v2)
  - Support for 100+ languages with automatic language detection
  - Translation capabilities (e.g., Farsi to English)
  - Model caching for improved performance
  - Error handling and retry logic for robust transcription
  - **Note**: Requires Linux/WSL environment; falls back gracefully if unavailable

- **`asr_whisper.py`** (481 lines): Whisper-based ASR (Alternative backend)
  - `ASRService` class for transcribing audio using OpenAI Whisper models via transformers
  - Support for Persian/Farsi and 100+ other languages
  - Cross-platform support (Windows, Linux, macOS)
  - Batch processing capabilities for efficient transcription
  - Error handling and retry logic

- **`asr_omnilingual.py`** (376 lines): Omnilingual ASR wrapper
  - Wrapper around omnilingual-asr library
  - Provides compatibility layer with Whisper-based interface
  - Enhanced multilingual support and translation
  - Seamless integration with existing ASR service interface

- **`mwe_register.py`** (109 lines): Minimal working example
  - Simplified SIP registration example for learning
  - Basic call handling without advanced features

#### Call Handling Package (`src/pjsua_bot/calls/`)

- **`any_call.py`** (871 lines): Advanced call handler
  - `AnyCall` class for full-featured call management
  - Audio recording (incoming/outgoing streams)
  - Audio playback with duration detection
  - VAD integration for real-time speech detection
  - ASR integration for live transcription
  - Silence tracking and auto-hangup logic
  - Event logging to Elasticsearch

- **`out_call.py`** (122 lines): Outbound call handler
  - `OutCall` class for making calls
  - Simple playback and hangup logic
  - Integration with account management

- **`goodbye.py`** (351 lines): Goodbye playback mixin
  - Reusable mixin for playing goodbye messages before hangup
  - Waiting voice playback during silence periods
  - State management for playback tracking
  - Configurable hangup timing
  - ASR completion tracking integration

#### Call Handler Mixins (`src/pjsua_bot/calls/mixins/`)

- **`asr_support.py`**: ASR integration mixin
  - Thread-safe ASR processing queue
  - Real-time chunk transcription
  - Background transcription thread management
  - Integration with VAD chunk manager

- **`call_media_handler.py`**: Media handling mixin
  - Audio recording setup and management
  - VAD initialization and configuration
  - Media stream handling
  - Recording file management

- **`call_state_handler.py`**: State management mixin
  - Call state transition handling
  - Event collection and logging
  - VAD metrics aggregation
  - Elasticsearch event logging

- **`event_logger.py`**: Event logging mixin
  - Structured event logging
  - Elasticsearch integration
  - Call record management

- **`playback_monitor.py`**: Playback monitoring mixin
  - Audio playback status tracking
  - VAD-based hangup logic
  - ASR completion detection
  - Playback completion callbacks

- **`recording_cleanup.py`** (351 lines): Recording management
  - Automatic cleanup of incomplete recordings
  - File organization by date
  - Error handling for file operations

#### Voice Activity Detection Package (`src/pjsua_bot/vad/`)

- **`silero.py`** (752 lines): Silero VAD implementation
  - `SileroVAD` class for real-time speech detection
  - PyTorch-based Silero VAD model integration
  - Audio preprocessing and normalization
  - Confidence scoring and threshold-based detection

- **`audio_reader.py`** (262 lines): Audio stream processing
  - Real-time audio frame reading from PJSUA2
  - Format conversion and buffering
  - Integration with VAD pipeline

- **`chunk_manager.py`** (326 lines): Voice chunk management
  - Automatic segmentation of speech into chunks
  - Chunk metadata tracking (duration, confidence, etc.)
  - MP3 encoding and file storage
  - Metrics calculation (speech duration, chunk count)

- **`silence.py`** (54 lines): Silence tracking
  - `SilenceTracker` class for monitoring silence periods
  - Detection of mutual silence (neither party speaking)
  - Duration calculation for silence metrics

- **`config.py`** (17 lines): VAD configuration
  - `VADConfig` dataclass for VAD parameters
  - Configurable thresholds and timing settings

- **`types.py`** (17 lines): VAD type definitions
  - `VoiceChunk` dataclass for chunk metadata
  - Type hints for VAD components

### Benefits of Modular Structure

- **Improved Maintainability**: Each module has a focused responsibility
- **Better Testability**: Modules can be tested independently
- **Enhanced Reusability**: Components can be imported and used separately
- **Easier Navigation**: Developers can find functionality more quickly

### Importing and Using Modules

You can now import specific components as needed:

```python
# Import from package root (recommended)
from src.pjsua_bot import Account, OutCall, AnyCall, main, setup_logging

# Import from specific modules
from src.pjsua_bot.account import Account
from src.pjsua_bot.calls import OutCall, AnyCall
from src.pjsua_bot.utils import setup_logging, pump_events, wait_until, generate_unique_id
from src.pjsua_bot.asr import ASRService  # Omnilingual ASR (default)
from src.pjsua_bot.asr_whisper import ASRService as WhisperASRService  # Whisper ASR
from src.pjsua_bot.vad import SileroVAD, VADConfig, VoiceChunk
from src.pjsua_bot.elasticsearch_client import ElasticsearchLogger, es_logger

# Use the main function
from src.pjsua_bot import main
main()
```

**Note**: See `docs/REFACTORING_SUMMARY.md` for detailed migration guide and module documentation.

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

### Integration & Testing
- **[Elasticsearch Integration](docs/ELASTICSEARCH.md)** - Call logging and data storage with VAD metrics (speech duration, chunk count, silence duration, confidence scores)
- **[Testing Framework](docs/TESTING.md)** - Unit tests and coverage reporting

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
  - [Omnilingual ASR Setup (original overview)](docs/OMNILINGUAL_ASR_SETUP.md)
- **Performance & Caching**
  - [Model Cache Guide](docs/MODEL_CACHE_GUIDE.md)
  - [Inference Time Guide](docs/INFERENCE_TIME_GUIDE.md)
- **Index**
  - [Setup Documentation Index](docs/SETUP_INDEX.md)

### Additional Documentation
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Module refactoring guide
- **[TESTING.md](TESTING.md)** - Testing documentation
- **[PROJECT_STRUCTURE_IMPROVEMENTS.md](PROJECT_STRUCTURE_IMPROVEMENTS.md)** - Project structure details
- **[VOICE_CAPTURE_IMPLEMENTATION.md](VOICE_CAPTURE_IMPLEMENTATION.md)** - Voice recording implementation
- **[ELASTICSEARCH_INTEGRATION.md](ELASTICSEARCH_INTEGRATION.md)** - Elasticsearch integration details

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
  - Replaces Flake8, isort, and more
  - Auto-fixes common issues
  - Configured in `pyproject.toml`
  
- **Black** (v24.8.0): Code formatting
  - 88 character line length
  - Consistent style across codebase
  
- **mypy** (v1.11.2): Static type checking
  - Type hints validation
  - Catches type-related bugs early

**Pre-commit Configuration:**

The `.pre-commit-config.yaml` file defines:
- Ruff: Two-pass (autofix then check)
- Black: Automatic formatting
- mypy: Type checking on `src/` and `tests/` directories

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_main.py

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
- Reports: Terminal, HTML (`htmlcov/`), and XML (`coverage.xml`)
- Markers: unit, integration, slow, elasticsearch, pjsua

### Project Dependencies

**Managed via:**
- `pyproject.toml`: Primary dependency configuration
- `requirements.txt`: Pip-compatible dependency list
- `uv.lock`: UV dependency lock file for reproducible builds

**Dependency groups:**
- Production: Core runtime dependencies
- Dev: Development tools (pytest, ruff, black, mypy, pre-commit)

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

**Medium Priority:**
- SIP MESSAGE support
- Presence/subscription handling
- Enhanced audio playback completion detection (using PJSUA2 callbacks)
- Video call support
- Call transfer and forwarding

**Completed Features:**
- ✅ Call recording (incoming/outgoing streams)
- ✅ Environment variable configuration
- ✅ Voice Activity Detection (VAD)
- ✅ Automatic Speech Recognition (ASR) - Multiple backends (Whisper & Omnilingual)
- ✅ Live transcription during calls
- ✅ Elasticsearch integration
- ✅ Docker containerization (standard & omnilingual variants)
- ✅ Modular codebase architecture with mixins
- ✅ Comprehensive testing framework
- ✅ Pre-commit hooks and code quality tools
- ✅ Goodbye and waiting voice playback
- ✅ VAD-based smart hangup

See `docs/` for detailed technical documentation and `REFACTORING_SUMMARY.md` for architecture details.

## 📝 License

This project is provided as-is for educational and development purposes.

## 🆘 Support

For issues specific to:
- **PJSIP/PJSUA2 library**: See [PJSIP Mailing List](https://www.pjsip.org/lists.htm)
- **This project**: Open an issue in the repository
- **SIP server configuration**: Consult your PBX documentation

## 📚 Resources

- [PJSIP Official Documentation](https://docs.pjsip.org/)
- [PJSUA2 Book](https://docs.pjsip.org/en/latest/pjsua2/intro.html)
- [SIP RFC 3261](https://www.rfc-editor.org/rfc/rfc3261)
- [Asterisk Documentation](https://docs.asterisk.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)

---

## 📋 Version Information

**Current Version**: 1.0.0  
**Last Updated**: November 2025  
**Python**: 3.11+  
**PJSUA2**: Compatible with PJSIP 2.x (tested with 2.14)  
**ASR Backends**: Whisper (transformers) & Omnilingual (Meta SeamlessM4T v2)

### Changelog

#### v1.0.0 (November 2025) - Production Release
- ✨ **Modular architecture**: Refactored into `calls/` and `vad/` subpackages with mixin-based design
- 🎯 **Advanced call handling**: Separated `AnyCall`, `OutCall`, and `GoodbyePlaybackMixin` classes
- 🔊 **Enhanced VAD**: Modular VAD system with audio reader, chunk manager, and silence tracker
- 🎤 **Dual ASR backends**: Support for both Whisper-based and Omnilingual ASR with automatic fallback
- 🌐 **Omnilingual ASR**: Meta SeamlessM4T v2 integration for superior multilingual support
- 🔄 **Live transcription**: Real-time ASR transcription during calls with chunk-based processing
- 🐳 **Docker production ready**: Multi-stage Dockerfile with PJSIP 2.14 compiled from source
- 🐳 **Omnilingual Docker**: Separate Dockerfile and compose file for omnilingual ASR support
- 🔧 **Code quality**: Pre-commit hooks with Ruff, Black, and mypy
- 📦 **Dependency management**: UV lock file for reproducible builds
- 📚 **Comprehensive documentation**: 25+ documentation files covering all aspects
- 🎵 **Enhanced playback**: Goodbye and waiting voice playback support

#### v0.5.0 (October 2025)
- 🎤 **ASR Integration**: Automatic Speech Recognition with Whisper models
- 🌐 **Multi-language support**: Persian/Farsi and 100+ other languages
- 🔇 **Silence tracking**: Enhanced VAD with mutual silence detection
- 📊 **Extended metrics**: Silence duration tracking in Elasticsearch

#### v0.4.1 (October 2025)
- 🎙️ **Voice Activity Detection**: Silero VAD integration for real-time speech detection
- ✂️ **Automatic chunking**: Intelligent voice segment separation
- 📈 **VAD metrics**: Speech duration, chunk count, and confidence logging to Elasticsearch
- 🎵 **MP3 encoding**: Efficient storage of voice chunks

#### v0.4.0 (September 2025)
- 🏗️ **Modular codebase**: Separated into focused modules (account, calls, utils)
- 📦 **Package structure**: Professional src/package layout
- 🔄 **Import system**: Clean package exports and imports
- 📉 **Code reduction**: 77% reduction in main module size

#### v0.3.0 (September 2025)
- ✅ **Testing framework**: Comprehensive pytest suite
- 📊 **Coverage reporting**: HTML, XML, and terminal coverage reports
- 🎭 **Mock support**: Full PJSUA2 and Elasticsearch mocking
- 🔍 **Test markers**: Categorized tests (unit, integration, slow, etc.)

#### v0.2.0 (August 2025)
- 🆔 **UUID call IDs**: Unique identifiers prevent duplicates across restarts
- 📁 **Organized recordings**: Date-based directory structure
- 🔄 **Call lifecycle**: Proper call state management

#### v0.1.0 (July 2025) - Initial Release
- 📞 **SIP registration**: Basic SIP account registration
- ☎️ **Call handling**: Inbound and outbound call support
- 🔊 **Audio playback**: WAV file playback during calls
- 📼 **Call recording**: Separate incoming/outgoing audio streams
- 🗄️ **Elasticsearch**: Call event logging
