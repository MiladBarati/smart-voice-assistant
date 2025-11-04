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
- **Automatic Speech Recognition (ASR)**: Transcribe audio recordings using Whisper-based models with support for Persian/Farsi and other languages
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
   pip install transformers
   
   # Install testing dependencies
   pip install pytest pytest-cov
   ```

## 🚦 Quick Start

### Test Basic Registration

```bash
python mwe_register.py \
  --user YOUR_EXTENSION \
  --password YOUR_PASSWORD \
  --domain YOUR_SIP_SERVER
```

### Receive Incoming Calls

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online
```

### Enable Live Transcription (ASR)

```bash
python register_bot.py \
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
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --play-file welcome_message.wav
```

### Make Outbound Call

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --dest 1002
```

### Transcribe Audio Recordings

```bash
python examples/asr_usage_example.py
```

**👉 For detailed step-by-step instructions, see [Getting Started Guide](docs/GETTING_STARTED.md)**

## 📁 Project Structure

```
pjsua-installation/
├── src/
│   └── pjsua_bot/
│       ├── __init__.py          # Package exports
│       ├── utils.py             # Utility functions
│       ├── account.py           # Account management class
│       ├── calls.py             # Call handling classes
│       ├── register_bot.py      # Main entry point (refactored)
│       ├── elasticsearch_client.py # Elasticsearch integration
│       ├── vad.py               # Voice Activity Detection (Silero VAD)
│       ├── asr.py               # Automatic Speech Recognition (ASR)
│       └── mwe_register.py      # Minimal working example
├── examples/                    # Usage examples
│   └── asr_usage_example.py    # ASR transcription example
├── tests/                       # Test suite
├── scripts/                     # Utility scripts
├── docs/                        # Documentation
│   ├── GETTING_STARTED.md
│   ├── USAGE_GUIDE.md
│   ├── CONFIGURATION.md
│   ├── VOICE_RECORDING.md
│   ├── AUDIO_PLAYBACK.md
│   ├── ELASTICSEARCH.md
│   ├── TROUBLESHOOTING.md
│   ├── TECHNICAL_DETAILS.md
│   └── TESTING.md
├── assets/                      # Static assets
│   └── audio/                   # Audio files
├── recordings/                  # Call recordings (generated)
├── infrastructure/              # Infrastructure definitions
└── main.py                     # Basic entry point
```

### Module Breakdown

#### Core Modules (`src/pjsua_bot/`)

- **`utils.py`** (110 lines): Common utility functions
  - `parse_sip_user()`, `setup_logging()`, `get_wav_duration()`
  - `ensure_recording_directory()`, `pump_events()`, `wait_until()`

- **`account.py`** (113 lines): SIP account management
  - `Account` class with registration and incoming call handling

- **`calls.py`** (893 lines): Call handling logic
  - `OutCall` class for outbound calls
  - `AnyCall` class for advanced call handling with recording, playback, VAD integration, and silence tracking

- **`vad.py`** (993 lines): Voice Activity Detection
  - `SileroVAD` class for real-time speech detection
  - Chunk segmentation and metrics calculation
  - Speech duration, chunk count, silence duration, and confidence tracking

- **`asr.py`** (428 lines): Automatic Speech Recognition
  - `ASRService` class for transcribing audio using Whisper models
  - Support for Persian/Farsi and other languages
  - Error handling and retry logic for robust transcription

- **`register_bot.py`** (245 lines): Main entry point
  - CLI argument parsing
  - Bot lifecycle management

- **`elasticsearch_client.py`** (486 lines): Elasticsearch integration
  - Event logging and call record management

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
from src.pjsua_bot.utils import setup_logging, pump_events, wait_until
from src.pjsua_bot.asr import ASRService, ASRConfig
from src.pjsua_bot.vad import SileroVAD

# Use the main function
from src.pjsua_bot import main
main()
```

**Note**: See `REFACTORING_SUMMARY.md` for detailed migration guide and module documentation.

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

### Reference
- **[Technical Details](docs/TECHNICAL_DETAILS.md)** - Implementation details and architecture
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Additional Documentation
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Module refactoring guide
- **[TESTING.md](TESTING.md)** - Testing documentation
- **[PROJECT_STRUCTURE_IMPROVEMENTS.md](PROJECT_STRUCTURE_IMPROVEMENTS.md)** - Project structure details
- **[VOICE_CAPTURE_IMPLEMENTATION.md](VOICE_CAPTURE_IMPLEMENTATION.md)** - Voice recording implementation
- **[ELASTICSEARCH_INTEGRATION.md](ELASTICSEARCH_INTEGRATION.md)** - Elasticsearch integration details

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Add DTMF handling
- ~~Implement call recording~~ ✅ **Completed**
- Add configuration file support
- ~~Environment variable configuration~~ ✅ **Completed**
- Multiple simultaneous calls
- SIP MESSAGE support
- Presence/subscription handling
- Enhanced audio playback completion detection (using PJSUA2 callbacks if available)
- SIP credential environment variable support
- Docker containerization
- Kubernetes deployment manifests
- ~~Modularize codebase~~ ✅ **Completed** - See `REFACTORING_SUMMARY.md`

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

**Version**: 0.5.0  
**Last Updated**: November 2025  
**Python**: 3.11+  
**PJSUA2**: Compatible with PJSIP 2.x  
**New in v0.5.0**: Automatic Speech Recognition (ASR) service integration with Whisper models for transcribing audio recordings, enhanced VAD with silence duration tracking when neither caller nor bot are speaking  
**New in v0.4.1**: Voice Activity Detection (VAD) with Silero integration, automatic chunk segmentation, and VAD metrics (speech duration, chunk count, confidence) logged to Elasticsearch  
**New in v0.4.0**: Modular codebase with separate modules for account, calls, utilities, and main entry point (77% reduction in register_bot.py)  
**New in v0.3.0**: Comprehensive unit testing framework with pytest, coverage reporting, and mock support  
**New in v0.2.0**: UUID-based unique call IDs to prevent duplicates across program restarts
