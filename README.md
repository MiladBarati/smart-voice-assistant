# PJSUA2 SIP Registration & Call Bot

A comprehensive Python toolkit for SIP/VoIP functionality using PJSUA2, including registration, outbound/inbound call handling, and automated audio playback.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Getting Started - Quick Guide](#getting-started---quick-guide)
- [Project Structure](#project-structure)
- [Usage](#usage)
  - [Basic Registration](#basic-registration)
  - [Full-Featured Bot](#full-featured-bot)
  - [Common Use Cases](#common-use-cases)
- [Configuration Options](#configuration-options)
- [Audio File Playback](#audio-file-playback)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)
- [Elasticsearch Integration](#elasticsearch-integration)

## 🎯 Overview

This project provides Python scripts for interacting with SIP servers (like Asterisk, FreeSWITCH, or any SIP-compliant PBX) using the PJSUA2 library. It includes both minimal working examples and a production-ready bot with comprehensive features.

## ✨ Features

- **SIP Registration**: Register with SIP servers using various authentication methods
- **Inbound Call Handling**: Accept and process incoming calls with auto-answer capability
- **Outbound Calls**: Make calls to SIP extensions or full URIs
- **Audio Playback**: Play WAV files to remote party during calls (e.g., welcome messages, IVR)
- **Voice Recording**: Capture incoming caller audio streams and outgoing bot audio to separate WAV files with organized storage
- **Automatic Audio Duration Detection**: Reads WAV file duration for precise playback timing
- **Auto-Answer**: Automatically answer incoming calls (enabled by default)
- **Smart Hangup**: Automatically hang up after audio playback completes with configurable delay
- **Unique Call IDs**: Uses UUID-based call IDs to prevent duplicates across program restarts
- **Multiple Transports**: Support for UDP, TCP, and TLS
- **NAT Traversal**: Proper handling of NAT scenarios
- **Event-Driven**: Non-blocking event loop with proper PJSUA2 event pumping
- **Signal Handling**: Graceful shutdown on Ctrl+C / SIGTERM
- **Extensive Logging**: Configurable log levels for debugging

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
   ```

## 🚦 Getting Started - Quick Guide

This section walks you through running the bot from scratch, step by step.

### Step 1: Verify PJSUA2 Installation

First, ensure PJSUA2 is properly installed:

```bash
# Activate your virtual environment (if using one)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Test PJSUA2 import
python -c "import pjsua2 as pj; print('PJSUA2 version:', pj.Endpoint.instance().libVersion().full)"
```

If this fails, you need to install PJSUA2 (see [Prerequisites](#prerequisites)).

### Step 2: Gather SIP Account Information

You'll need the following information from your SIP provider or PBX administrator:

- **Username/Extension**: e.g., `1001`, `john.doe`
- **Password**: Your SIP account password
- **Domain/Server**: e.g., `pbx.example.com`, `192.168.1.100`
- **Port** (optional): Usually `5060` for UDP/TCP, `5061` for TLS
- **Transport** (optional): `udp` (default), `tcp`, or `tls`

### Step 3: Test Basic Registration

Start with a simple registration test using `mwe_register.py`:

```bash
python mwe_register.py \
  --user YOUR_EXTENSION \
  --password YOUR_PASSWORD \
  --domain YOUR_SIP_SERVER
```

**Example**:
```bash
python mwe_register.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100
```

**Expected Output**:
```
***reg: active=False code=0 reason=
***reg: active=True code=200 reason=OK
***Registered successfully
```

If you see "Registered successfully", congratulations! Move to Step 4.

**Common Issues**:
- **401 Unauthorized**: Wrong username or password
- **408 Timeout**: Server unreachable, check domain/IP and network
- **Port conflict**: Add `--local-port 5070` to use a different port

### Step 4: Receive Your First Call

Now let's set up the bot to receive incoming calls:

```bash
python register_bot.py \
  --user YOUR_EXTENSION \
  --password YOUR_PASSWORD \
  --domain YOUR_SIP_SERVER \
  --stay-online
```

**Example**:
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100 \
  --stay-online
```

**What happens**:
1. Bot registers with the SIP server
2. Waits for incoming calls
3. **Automatically answers any call with "200 OK"** (auto-answer is enabled by default)
4. Plays the welcome message (if `welcome_message.wav` exists)
5. Hangs up 2 seconds after the message finishes playing
6. Press **Ctrl+C** to exit

**Test it**: Call the extension from another phone and you should hear the welcome message!

**Note**: To disable auto-answer, add the `--no-auto-answer` flag.

### Step 5: Make an Outbound Call

Test making a call to another extension:

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100 \
  --dest 1002
```

**What happens**:
1. Bot registers with server
2. Calls extension `1002`
3. If answered, audio is bridged
4. Call stays active (press Ctrl+C to hang up)

**Auto-hangup after 30 seconds**:
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100 \
  --dest 1002 \
  --hangup-seconds 30
```

### Step 6: Add Audio Playback (Welcome Message)

Now let's play a welcome message when someone calls:

#### A. Convert Your Audio File to WAV

If you have `welocme_voice.m4a` (or any audio file), convert it to WAV format:

```bash
# Install FFmpeg first if you don't have it:
# Windows: Download from https://ffmpeg.org/download.html
# Linux: sudo apt install ffmpeg
# Mac: brew install ffmpeg

# Convert to WAV (8kHz mono, telephony quality)
ffmpeg -i welocme_voice.m4a -ar 8000 -ac 1 -sample_fmt s16 welcome_message.wav
```

**Result**: You now have `welcome_message.wav` ready to use!

#### B. Run Bot with Audio Playback

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100 \
  --stay-online \
  --play-file welcome_message.wav
```

**What happens**:
1. Bot registers and waits for calls
2. When someone calls, bot auto-answers
3. **Reads the WAV file duration automatically** (e.g., 6.2 seconds)
4. **Plays `welcome_message.wav` to the caller exactly once** (no looping)
5. **Waits 2 seconds after the message finishes**
6. **Automatically hangs up the call**
7. You can hear the caller's audio locally (for monitoring)

**Test it**: Call the extension from another phone and you'll hear the welcome message!

#### C. Customize Hangup Delay

Control how long to wait after the message finishes before hanging up:

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100 \
  --stay-online \
  --play-file welcome_message.wav \
  --hangup-delay 5
```

This will wait 5 seconds after the message finishes before hanging up.

### Step 7: Advanced Scenarios

#### Scenario A: IVR/Auto-Attendant System

Create a menu prompt and let callers hear it, then automatically hang up:

```bash
# 1. Create menu.wav with text-to-speech or record it
# 2. Run the bot:
python register_bot.py \
  --user ivr-main \
  --password ivrpass \
  --domain pbx.local \
  --stay-online \
  --play-file menu.wav \
  --hangup-delay 3
```

The bot will automatically detect the menu.wav duration, play it once, wait 3 seconds, and hang up.

#### Scenario B: Automated Announcement System

Call an extension and play an announcement:

```bash
python register_bot.py \
  --user notification-bot \
  --password botpass \
  --domain pbx.local \
  --dest 5551234567 \
  --play-file emergency-alert.wav \
  --hangup-seconds 60
```

#### Scenario C: Using TCP Transport (More Reliable)

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --transport tcp \
  --stay-online
```

#### Scenario D: Secure TLS Connection

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain secure.pbx.com \
  --transport tls \
  --local-port 5061 \
  --tls-verify \
  --stay-online
```

#### Scenario E: Voice Recording System

Record incoming calls for analysis or archival:

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording \
  --recording-path /var/recordings
```

**What happens**:
1. Bot registers and waits for calls
2. When someone calls, bot auto-answers
3. **Captures incoming audio to WAV files** in organized directories
4. Files stored as: `/var/recordings/2025-01-26/{timestamp}_{caller}_incoming.wav` and `/var/recordings/2025-01-26/{timestamp}_{caller}_outgoing.wav`
5. Recording metadata included in Elasticsearch call records

**File naming**: `20250126_143022_1002_incoming.wav` and `20250126_143022_1002_outgoing.wav`
- Timestamp ensures uniqueness and chronological ordering
- Caller number for easy identification
- `_incoming` suffix for caller audio
- `_outgoing` suffix for bot audio

#### Scenario F: Combined Playback and Recording

Play welcome message while recording caller response:

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --play-file welcome.wav \
  --enable-recording \
  --recording-path ./call-recordings
```

This creates a complete IVR system that plays a message and captures both caller audio and bot audio separately.

### Step 8: Running as a Service (Production)

For production deployments, you can run the bot as a system service:

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: "At system startup"
4. Action: Start a program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `register_bot.py --user 1001 --password secret123 --domain pbx.local --stay-online --auto-answer`
   - Start in: `C:\path\to\pjsua-installation`

#### Linux (systemd)

Create `/etc/systemd/system/sip-bot.service`:

```ini
[Unit]
Description=PJSUA2 SIP Bot
After=network.target

[Service]
Type=simple
User=sipbot
WorkingDirectory=/home/sipbot/pjsua-installation
ExecStart=/home/sipbot/pjsua-installation/venv/bin/python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --auto-answer \
  --play-file welocme_voice.wav
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sip-bot
sudo systemctl start sip-bot
sudo systemctl status sip-bot
```

### Step 9: Monitoring and Logs

#### Increase Logging for Debugging

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --log-level 5
```

Log levels: `0` (none) to `6` (trace). Default is `3` (info).

#### Save Logs to File

```bash
# Windows PowerShell:
python register_bot.py --user 1001 --password secret123 --domain pbx.local --stay-online 2>&1 | Tee-Object -FilePath bot.log

# Linux/Mac:
python register_bot.py --user 1001 --password secret123 --domain pbx.local --stay-online 2>&1 | tee bot.log
```

### Quick Reference: Common Commands

```bash
# Test registration only
python mwe_register.py --user 1001 --password pass --domain pbx.local

# Answer calls automatically (auto-answer enabled by default)
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online

# Answer with welcome message (auto-detects duration, plays once, hangs up after 2s)
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --play-file welcome.wav

# Record incoming calls
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --enable-recording

# Answer with welcome message and record caller response
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --play-file welcome.wav --enable-recording

# Answer with welcome message and custom hangup delay
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --play-file welcome.wav --hangup-delay 5

# Disable auto-answer (manual call handling)
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --no-auto-answer

# Make outbound call
python register_bot.py --user 1001 --password pass --domain pbx.local --dest 1002

# Make call with announcement
python register_bot.py --user 1001 --password pass --domain pbx.local --dest 1002 --play-file msg.wav --hangup-seconds 30

# Use different port (if 5060 is busy)
python register_bot.py --user 1001 --password pass --domain pbx.local --local-port 5070 --stay-online

# Use TCP transport
python register_bot.py --user 1001 --password pass --domain pbx.local --transport tcp --stay-online

# Maximum logging
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --log-level 6
```

---

## 📁 Project Structure

```

## Elasticsearch Integration

This project logs exactly one structured document per call to Elasticsearch. The single document is created and sent only once at call end (disconnect) and contains the complete call record (caller/callee, timing, duration, status, media and bot metadata). No per-event or per-stage logs are sent during the call.

### Install Client

Use the 7.x Python client for compatibility with Elasticsearch 8.x servers:

```bash
pip install "elasticsearch>=7.0.0,<8.0.0"
pip install python-dotenv
```

### Configuration

The integration is enabled by default via the internal logger. All configuration is now done through environment variables for security and flexibility.

#### Environment Variables

Create a `.env` file in the project root with your Elasticsearch configuration:

```bash
# Elasticsearch Configuration
ES_HOST="your-elasticsearch-host"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="your-password"
ES_USE_SSL="false"
ES_VERIFY_CERTS="false"
ELASTIC_INDEX_PREFIX="pjsua-calls"
```

#### Default Values

If environment variables are not set, the following defaults are used:

- Host: `localhost`
- Port: `9200`
- Username: `elastic`
- Password: (empty)
- SSL: `false`
- Verify Certs: `false`
- Index Prefix: `pjsua-calls`

#### Security Benefits

- **No hardcoded credentials** in source code
- **Environment-specific configuration** for dev/staging/prod
- **Easy credential rotation** without code changes
- **Version control safety** - credentials not committed to repository

### Index Pattern

All call records are stored in a single unified index:

- `pjsua-calls` — Contains one record per call

In Kibana (Stack Management → Index Patterns) create:

- `pjsua-calls`

### Unique Call ID System

The bot now uses UUID-based call IDs to ensure uniqueness across program restarts. This solves the issue where PJSUA2's internal call ID counter resets to zero on each restart, causing duplicate call IDs in logs.

**Key Features:**
- **UUID-based IDs**: Each call gets a globally unique identifier
- **Cross-session persistence**: Call IDs remain unique even after program restarts
- **Elasticsearch compatibility**: UUIDs work perfectly with Elasticsearch indexing
- **Backward compatibility**: Original PJSUA2 call ID is preserved for reference

**Implementation Details:**
- Uses Python's `uuid.uuid4()` for generating unique identifiers
- Each `AnyCall` instance gets a `unique_call_id` attribute
- Call records use the UUID as the primary `call_id` field
- Original PJSUA2 call ID is available for debugging purposes

### Structured Call Record Schema

On call disconnect, the bot writes one document that matches this mapping (example mapping shown; create in Elasticsearch if you need strict types):

```json
{
  "mappings": {
    "properties": {
      "call_id":        {"type":"keyword"},
      "caller_number":  {"type":"keyword"},
      "callee_ext":     {"type":"keyword"},
      "start_time":     {"type":"date"},
      "end_time":       {"type":"date"},
      "duration_sec":   {"type":"integer"},
      "status":         {"type":"keyword"},
      "direction":      {"type":"keyword"},
      "media":          {"type":"object","enabled": true},
      "bot":            {"type":"object","enabled": true},
      "host":           {"type":"keyword"},
      "ingest_ts":      {"type":"date"}
    }
  }
}
```

Fields populated by the bot on disconnect:

- `call_id`: **UUID-based unique identifier** (prevents duplicates across restarts)
- `caller_number`: parsed from remote SIP URI
- `callee_ext`: parsed from local SIP URI
- `start_time`, `end_time`: UTC ISO8601
- `duration_sec`: integer seconds (computed)
- `status`: `disconnected`
- `direction`: `inbound` (outbound support can be extended)
- `media`: `{ file_played, playback_started, playback_finished }`
- `bot`: `{ auto_answer, domain, user }`
- `host`: machine hostname
- `ingest_ts`: set at index time

**Note**: The `call_id` field now uses UUID format (e.g., `"550e8400-e29b-41d4-a716-446655440000"`) instead of sequential integers, ensuring uniqueness across program restarts and multiple bot instances.

### Testing Integration

Quick test script (connectivity and basic indexing checks):

```bash
python test_elasticsearch.py
```

Expected successful output includes cluster health and ✅ for each sample event type. Then, verify data in Kibana (`Discover`) using the index patterns above.
pjsua-installation/
├── register_bot.py       # Full-featured SIP bot with all options
├── mwe_register.py       # Minimal working example for registration
├── main.py               # Basic project entry point
├── elasticsearch_client.py # Elasticsearch integration with environment variables
├── test_connectivity.py  # Elasticsearch connectivity testing
├── test_elasticsearch.py # Elasticsearch integration testing
├── welocme_voice.m4a     # Sample audio file (needs conversion to WAV)
├── welcome_message.wav   # Sample WAV file for testing
├── .env                  # Environment variables (not in git)
├── .env.example          # Example environment file
├── pyproject.toml        # Project configuration
├── README.md             # This file
└── venv/                 # Virtual environment (not in git)
```

### File Descriptions

- **`register_bot.py`**: Production-ready bot with comprehensive features including call handling, audio playback, multiple transports, and extensive CLI options.
- **`mwe_register.py`**: Minimal working example demonstrating basic SIP registration with proper event pumping.
- **`main.py`**: Simple placeholder entry point.
- **`elasticsearch_client.py`**: Elasticsearch integration client with environment variable configuration and structured logging.
- **`test_connectivity.py`**: Script to test Elasticsearch connectivity and troubleshoot connection issues.
- **`test_elasticsearch.py`**: Comprehensive test script for Elasticsearch integration functionality.
- **`.env`**: Environment variables file (not committed to version control for security).
- **`.env.example`**: Example environment file showing required variables.

## 💻 Usage

### Basic Registration

Use `mwe_register.py` for simple registration testing:

```bash
python mwe_register.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --local-port 5070
```

**Options:**
- `--user`: SIP username/extension
- `--password`: SIP password
- `--domain`: SIP server domain or IP
- `--auth-user`: Authentication username (if different from user)
- `--transport`: udp, tcp, or tls (default: udp)
- `--local-port`: Local SIP port (default: 5070)
- `--wait`: Seconds to wait for registration (default: 10)

### Full-Featured Bot

Use `register_bot.py` for advanced scenarios:

#### 1. Register and Stay Online (Receive Calls)

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --stay-online \
  --auto-answer
```

#### 2. Make Outbound Call

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --dest 1002 \
  --hangup-seconds 30
```

#### 3. Auto-Answer with Welcome Message

```bash
# First, convert audio to WAV format
ffmpeg -i welocme_voice.m4a -ar 8000 -ac 1 -sample_fmt s16 welocme_voice.wav

# Run bot with audio playback
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --stay-online \
  --auto-answer \
  --play-file welocme_voice.wav
```

#### 4. Outbound Call with Audio Playback

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --dest sip:1002@pbx.example.com \
  --play-file announcement.wav \
  --hangup-seconds 60
```

#### 5. Using TLS Transport

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain secure.example.com \
  --transport tls \
  --tls-verify \
  --local-port 5061 \
  --stay-online
```

#### 6. With Outbound Proxy

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --outbound-proxy "sip:proxy.example.com:5060;lr" \
  --stay-online
```

### Common Use Cases

#### IVR System / Auto-Attendant
```bash
python register_bot.py \
  --user ivr-line \
  --password ivrpass \
  --domain pbx.local \
  --stay-online \
  --auto-answer \
  --play-file menu.wav
```

#### Voicemail Notification System
```bash
python register_bot.py \
  --user notification-bot \
  --password botpass \
  --domain pbx.local \
  --dest 5551234567 \
  --play-file voicemail-alert.wav \
  --hangup-seconds 45
```

#### Call Testing / Load Testing
```bash
python register_bot.py \
  --user test-1001 \
  --password testpass \
  --domain test-pbx.local \
  --dest 9999 \
  --hangup-seconds 5
```

## ⚙️ Configuration Options

### `register_bot.py` CLI Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--user` | string | *required* | SIP username or extension |
| `--password` | string | *required* | SIP password |
| `--domain` | string | *required* | Registrar/realm host or domain |
| `--auth-user` | string | `None` | Authentication username (if different from user) |
| `--local-port` | int | 5060 | Local SIP port to bind |
| `--wait-seconds` | int | 10 | Time to wait for registration/connect |
| `--stay-online` | flag | `False` | Keep endpoint running to receive calls |
| `--auto-answer` | flag | `True` | Answer incoming calls with 200 OK (enabled by default) |
| `--no-auto-answer` | flag | `False` | Disable auto-answering of incoming calls |
| `--dest` | string | `None` | Destination SIP URI or extension for outbound call |
| `--hangup-seconds` | int | 0 | Auto hangup after N seconds of connection; 0 to disable |
| `--outbound-proxy` | string | `None` | Outbound proxy URI (e.g., `sip:host:5060;lr`) |
| `--transport` | choice | `udp` | SIP transport: udp, tcp, or tls |
| `--tls-verify` | flag | `False` | Verify TLS server certificate (when using TLS) |
| `--log-level` | int | 3 | Endpoint log level (0-6, higher = more verbose) |
| `--play-file` | string | `welcome_message.wav` | Path to WAV file to play to remote when call connects |
| `--hangup-delay` | int | 2 | Seconds to wait after welcome message before hanging up |
| `--message-duration` | int | 5 | Fallback duration if WAV file cannot be read (auto-detected from file) |
| `--enable-recording` | flag | `False` | Enable voice capture for incoming calls |
| `--recording-path` | string | `./recordings` | Base directory for storing recorded audio files |

### Environment Variables

Currently, all configuration is done via CLI arguments. Environment variable support can be added if needed.

## 🔧 Environment Variables

This project uses environment variables for secure configuration management, particularly for Elasticsearch integration.

### Elasticsearch Configuration

Create a `.env` file in your project root with the following variables:

```bash
# Elasticsearch Configuration
ES_HOST="your-elasticsearch-host"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="your-secure-password"
ES_USE_SSL="false"
ES_VERIFY_CERTS="false"
ELASTIC_INDEX_PREFIX="pjsua-calls"
```

### Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_HOST` | `localhost` | Elasticsearch server hostname or IP |
| `ES_PORT` | `9200` | Elasticsearch server port |
| `ES_USERNAME` | `elastic` | Username for Elasticsearch authentication |
| `ES_PASSWORD` | (empty) | Password for Elasticsearch authentication |
| `ES_USE_SSL` | `false` | Whether to use HTTPS for Elasticsearch connection |
| `ES_VERIFY_CERTS` | `false` | Whether to verify SSL certificates |
| `ELASTIC_INDEX_PREFIX` | `pjsua-calls` | Prefix for Elasticsearch index names |

### Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use different `.env` files** for different environments (dev, staging, prod)
3. **Rotate credentials regularly** by updating environment variables
4. **Use strong passwords** for production environments
5. **Enable SSL/TLS** in production (`ES_USE_SSL="true"`)

### Example `.env` Files

#### Development Environment
```bash
# .env.dev
ES_HOST="localhost"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="dev-password"
ES_USE_SSL="false"
ES_VERIFY_CERTS="false"
ELASTIC_INDEX_PREFIX="pjsua-calls-dev"
```

#### Production Environment
```bash
# .env.prod
ES_HOST="elasticsearch.production.com"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="super-secure-production-password"
ES_USE_SSL="true"
ES_VERIFY_CERTS="true"
ELASTIC_INDEX_PREFIX="pjsua-calls-prod"
```

### Loading Environment Variables

The application automatically loads environment variables from the `.env` file using `python-dotenv`. You can also:

1. **Set variables in your shell**:
   ```bash
   export ES_HOST="your-host"
   export ES_PASSWORD="your-password"
   ```

2. **Use different `.env` files**:
   ```bash
   # Load specific environment file
   python -c "from dotenv import load_dotenv; load_dotenv('.env.prod')"
   ```

3. **Override at runtime**:
   ```bash
   ES_HOST="override-host" python register_bot.py --user 1001 --password pass --domain pbx.local
   ```

## 🎙️ Voice Recording

The `--enable-recording` option captures incoming caller audio streams to WAV files for analysis, archival, or compliance purposes.

### How It Works

1. **Automatic Capture**: When a call's media becomes active, if recording is enabled, separate `AudioMediaRecorder` instances are created for incoming and outgoing audio
2. **File Organization**: Recordings are stored in date-based directories: `{recording-path}/YYYY-MM-DD/`
3. **Separate Files**: Creates two files per call:
   - `{timestamp}_{caller}_incoming.wav` - Audio from the caller
   - `{timestamp}_{caller}_outgoing.wav` - Audio from the bot (welcome message)
4. **Parallel Operation**: Both recordings run alongside existing audio playback/bridging without interference
5. **Metadata Integration**: Recording information for both files is included in Elasticsearch call records

### Audio Format

- **Output**: WAV files (PCM encoding)
- **Sample Rate**: Inherited from call media (typically 8kHz or 16kHz)
- **Channels**: Mono (single caller stream)
- **Quality**: Telephony-grade audio suitable for voice analysis

### Storage Structure

```
recordings/
├── 2025-01-26/
│   ├── 20250126_143022_1001_incoming.wav
│   ├── 20250126_143022_1001_outgoing.wav
│   ├── 20250126_143155_1002_incoming.wav
│   ├── 20250126_143155_1002_outgoing.wav
├── 2025-01-27/
│   ├── 20250127_091230_1003_incoming.wav
│   └── 20250127_091230_1003_outgoing.wav
```

### Recording Metadata in Elasticsearch

Call records include a `recording` field when recording is enabled:

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "caller_number": "1002",
  "recording": {
    "incoming": {
      "file_path": "/var/recordings/2025-01-26/20250126_143022_1002_incoming.wav",
      "file_size_bytes": 245760,
      "recorded": true
    },
    "outgoing": {
      "file_path": "/var/recordings/2025-01-26/20250126_143022_1002_outgoing.wav",
      "file_size_bytes": 128000,
      "recorded": true
    }
  }
}
```

### Usage Examples

#### Basic Recording
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording
```

#### Custom Recording Directory
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording \
  --recording-path /var/voip-recordings
```

#### Recording with Playback (IVR + Capture)
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --play-file menu.wav \
  --enable-recording \
  --recording-path ./ivr-recordings
```

## 🔊 Audio File Playback

The `--play-file` option allows you to play audio files to the remote party during a call.

### Requirements

1. **WAV Format**: PJSUA2's media player requires WAV files
2. **Recommended Settings**:
   - Sample Rate: 8000 Hz (standard telephony) or 16000 Hz
   - Channels: 1 (mono)
   - Format: 16-bit signed PCM

### Converting Audio Files

Use FFmpeg to convert any audio format to compatible WAV:

```bash
# Convert to 8kHz mono WAV (standard quality)
ffmpeg -i input.m4a -ar 8000 -ac 1 -sample_fmt s16 output.wav

# Convert to 16kHz mono WAV (higher quality)
ffmpeg -i input.mp3 -ar 16000 -ac 1 -sample_fmt s16 output.wav

# Batch convert all m4a files in directory
for file in *.m4a; do
  ffmpeg -i "$file" -ar 8000 -ac 1 -sample_fmt s16 "${file%.m4a}.wav"
done
```

### How It Works

- When a call's media becomes active, if `--play-file` is specified, an `AudioMediaPlayer` is created
- **The bot automatically reads the WAV file duration** using Python's `wave` module
- The audio file is transmitted to the remote party **exactly once** (no looping)
- After the message finishes playing, the bot **waits for the configured delay** (default: 2 seconds)
- The call is **automatically hung up** after the delay
- Local speakers still receive audio from the remote side (for monitoring)
- The player is released when the call disconnects

### Automatic Duration Detection

The bot intelligently detects the actual duration of your WAV file:

```
***WAV file duration: 6.23 seconds
***Using actual WAV duration: 6.23 seconds
***Welcome message playback started
***Will stop player after 6.23 seconds
***Stopped player transmission to prevent looping
***Welcome message finished. Will hang up in 2 seconds
***Auto-hanging up after welcome message
```

This ensures precise timing and prevents the message from replaying!

## 🔧 Troubleshooting

### Registration Fails

**Problem**: Registration timeout or 401/403 errors

**Solutions**:
- Verify credentials (`--user`, `--password`, `--auth-user`)
- Check if domain is correct (`--domain`)
- Try different transport (`--transport tcp` instead of udp)
- Increase wait time (`--wait-seconds 20`)
- Check firewall/NAT rules
- Increase log level (`--log-level 5`) for details

### Port Already in Use

**Problem**: `Transport creation error` or port binding failure

**Solutions**:
- Use a different port: `--local-port 5070`
- Kill existing process using the port
- On Linux: `sudo lsof -i :5060` to find process

### Audio Not Playing

**Problem**: No audio heard on remote side

**Solutions**:
- Ensure WAV file format is correct (8kHz/16kHz, mono, 16-bit PCM)
- Verify file path is correct and accessible
- Check that call media state becomes `ACTIVE` (look for "Media: playing file" log)
- Test with a simple beep/tone WAV file first
- Verify the bot shows "***WAV file duration: X seconds" at startup

### Audio Keeps Looping

**Problem**: Welcome message plays multiple times instead of once

**Solutions**:
- This should be fixed automatically - the bot stops player transmission after the detected duration
- Check logs for "***Stopped player transmission to prevent looping"
- Adjust `--message-duration` if the auto-detection is incorrect
- Ensure your WAV file is properly formatted (corrupted files may have incorrect duration metadata)

### Call Drops Immediately

**Problem**: Call connects then disconnects

**Solutions**:
- Check codec compatibility between endpoints
- Verify RTP/media ports are not blocked
- Try disabling ICE/STUN if behind complex NAT
- Increase log level to see detailed SIP/SDP negotiation

### TLS Handshake Fails

**Problem**: Registration fails when using `--transport tls`

**Solutions**:
- Ensure server supports TLS on the expected port (usually 5061)
- Try without `--tls-verify` if using self-signed certificates
- Check certificate validity and CA trust chain
- Verify server certificate includes correct hostname/IP

### Elasticsearch Connection Issues

**Problem**: Elasticsearch logging fails or connection errors

**Solutions**:
- Verify `.env` file exists and contains correct credentials
- Check Elasticsearch server is running and accessible
- Test connectivity: `python test_connectivity.py`
- Verify environment variables are loaded: `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('ES_HOST:', os.getenv('ES_HOST'))"`
- Check firewall rules for Elasticsearch port (default 9200)
- Ensure `python-dotenv` is installed: `pip install python-dotenv`

**Common Error Messages**:
- `ModuleNotFoundError: No module named 'dotenv'` → Install python-dotenv
- `ConnectionError` → Check ES_HOST and ES_PORT in .env file
- `AuthenticationException` → Verify ES_USERNAME and ES_PASSWORD
- `SSLHandshakeError` → Set `ES_USE_SSL="false"` or fix SSL configuration

### Duplicate Call IDs (Fixed)

**Problem**: Call IDs starting from 0 on each restart causing duplicate entries

**Solution**: ✅ **Fixed in current version** - The bot now uses UUID-based call IDs that are globally unique across program restarts and multiple instances. Each call gets a unique identifier like `"550e8400-e29b-41d4-a716-446655440000"` instead of sequential numbers.

## 🔬 Technical Details

### Event Loop Architecture

Both scripts use proper PJSUA2 event pumping via `ep.libHandleEvents(ms)` in a loop rather than blocking sleeps. This ensures:
- Timely processing of SIP messages and media events
- Proper callback execution
- Graceful handling of signals and shutdown

### NAT Handling

The scripts disable certain NAT traversal features that can cause issues in stable LAN environments:
- SIP Outbound (RFC 5626) disabled
- Contact/Via rewrite disabled
- Contact source port forcing disabled

These can be re-enabled for complex NAT scenarios if needed.

### Memory Management

- **Call References**: Calls are stored in `Account.calls` dict to maintain strong references during call lifetime
- **Cleanup**: References are removed on call disconnect to allow proper garbage collection
- **Media Players**: Player objects are kept as instance variables and released on disconnect

### Call ID Management

- **UUID Generation**: Each call instance gets a unique UUID via `uuid.uuid4()` at creation time
- **Cross-session Uniqueness**: UUIDs ensure no duplicate call IDs even across program restarts
- **Elasticsearch Integration**: UUIDs are stored as keyword fields for efficient querying
- **Backward Compatibility**: Original PJSUA2 call IDs are preserved for debugging

### Signal Handling

- `SIGINT` (Ctrl+C) and `SIGTERM` are caught for graceful shutdown
- Event loop checks `stopping["flag"]` to exit cleanly
- `ep.libDestroy()` is called in a `finally` block to ensure cleanup

### Threading Model

- PJSUA2 callbacks run in library threads
- Event pumping happens in the main thread
- **All PJSUA2 API calls must be made from the main event loop thread** (not from background threads)
- The bot uses time-based flags checked in the main loop for automatic hangup (thread-safe approach)
- No manual threading required; PJSUA2 handles internal threading

### Audio Playback Control

- **Duration Detection**: Uses Python's `wave` module to read WAV file metadata at startup
- **Playback Timer**: Sets a stop time based on actual file duration
- **Loop Prevention**: Actively stops player transmission after the calculated duration
- **Precise Hangup**: Waits for configurable delay after message finishes before hanging up
- **Thread-Safe**: All operations happen in the main event loop, avoiding PJSUA2 threading issues

## 📝 License

This project is provided as-is for educational and development purposes.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Add DTMF handling
- Implement call recording
- Add configuration file support
- ~~Environment variable configuration~~ ✅ **Completed**
- Multiple simultaneous calls
- SIP MESSAGE support
- Presence/subscription handling
- Enhanced audio playback completion detection (using PJSUA2 callbacks if available)
- SIP credential environment variable support
- Docker containerization
- Kubernetes deployment manifests

## 📚 Resources

- [PJSIP Official Documentation](https://docs.pjsip.org/)
- [PJSUA2 Book](https://docs.pjsip.org/en/latest/pjsua2/intro.html)
- [SIP RFC 3261](https://www.rfc-editor.org/rfc/rfc3261)
- [Asterisk Documentation](https://docs.asterisk.org/)

## 🆘 Support

For issues specific to:
- **PJSIP/PJSUA2 library**: See [PJSIP Mailing List](https://www.pjsip.org/lists.htm)
- **This project**: Open an issue in the repository
- **SIP server configuration**: Consult your PBX documentation

---

**Version**: 0.2.0  
**Last Updated**: January 2025  
**Python**: 3.11+  
**PJSUA2**: Compatible with PJSIP 2.x  
**New in v0.2.0**: UUID-based unique call IDs to prevent duplicates across program restarts
