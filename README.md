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

## 🎯 Overview

This project provides Python scripts for interacting with SIP servers (like Asterisk, FreeSWITCH, or any SIP-compliant PBX) using the PJSUA2 library. It includes both minimal working examples and a production-ready bot with comprehensive features.

## ✨ Features

- **SIP Registration**: Register with SIP servers using various authentication methods
- **Inbound Call Handling**: Accept and process incoming calls with auto-answer capability
- **Outbound Calls**: Make calls to SIP extensions or full URIs
- **Audio Playback**: Play WAV files to remote party during calls (e.g., welcome messages, IVR)
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
  --stay-online \
  --auto-answer
```

**Example**:
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100 \
  --stay-online \
  --auto-answer
```

**What happens**:
1. Bot registers with the SIP server
2. Waits for incoming calls
3. Automatically answers any call with "200 OK"
4. Bridges audio between your microphone/speakers and the remote caller
5. Press **Ctrl+C** to exit

**Test it**: Call the extension from another phone and you should be connected!

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
ffmpeg -i welocme_voice.m4a -ar 8000 -ac 1 -sample_fmt s16 welocme_voice.wav
```

**Result**: You now have `welocme_voice.wav` ready to use!

#### B. Run Bot with Audio Playback

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain 192.168.1.100 \
  --stay-online \
  --auto-answer \
  --play-file welocme_voice.wav
```

**What happens**:
1. Bot registers and waits for calls
2. When someone calls, bot auto-answers
3. **Plays `welocme_voice.wav` to the caller**
4. You can hear the caller's audio locally (for monitoring)

**Test it**: Call the extension from another phone and you'll hear the welcome message!

### Step 7: Advanced Scenarios

#### Scenario A: IVR/Auto-Attendant System

Create a menu prompt and let callers hear it:

```bash
# 1. Create menu.wav with text-to-speech or record it
# 2. Run the bot:
python register_bot.py \
  --user ivr-main \
  --password ivrpass \
  --domain pbx.local \
  --stay-online \
  --auto-answer \
  --play-file menu.wav
```

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

# Answer calls automatically
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --auto-answer

# Answer with welcome message
python register_bot.py --user 1001 --password pass --domain pbx.local --stay-online --auto-answer --play-file welcome.wav

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
pjsua-installation/
├── register_bot.py       # Full-featured SIP bot with all options
├── mwe_register.py       # Minimal working example for registration
├── main.py               # Basic project entry point
├── welocme_voice.m4a     # Sample audio file (needs conversion to WAV)
├── pyproject.toml        # Project configuration
├── README.md             # This file
└── venv/                 # Virtual environment (not in git)
```

### File Descriptions

- **`register_bot.py`**: Production-ready bot with comprehensive features including call handling, audio playback, multiple transports, and extensive CLI options.
- **`mwe_register.py`**: Minimal working example demonstrating basic SIP registration with proper event pumping.
- **`main.py`**: Simple placeholder entry point.

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
| `--auto-answer` | flag | `False` | Answer incoming calls with 200 OK |
| `--dest` | string | `None` | Destination SIP URI or extension for outbound call |
| `--hangup-seconds` | int | 0 | Auto hangup after N seconds of connection; 0 to disable |
| `--outbound-proxy` | string | `None` | Outbound proxy URI (e.g., `sip:host:5060;lr`) |
| `--transport` | choice | `udp` | SIP transport: udp, tcp, or tls |
| `--tls-verify` | flag | `False` | Verify TLS server certificate (when using TLS) |
| `--log-level` | int | 3 | Endpoint log level (0-6, higher = more verbose) |
| `--play-file` | string | `None` | Path to WAV file to play to remote when call connects |

### Environment Variables

Currently, all configuration is done via CLI arguments. Environment variable support can be added if needed.

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
- The audio file is transmitted to the remote party
- Local speakers still receive audio from the remote side (for monitoring)
- The player is released when the call disconnects

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

### Signal Handling

- `SIGINT` (Ctrl+C) and `SIGTERM` are caught for graceful shutdown
- Event loop checks `stopping["flag"]` to exit cleanly
- `ep.libDestroy()` is called in a `finally` block to ensure cleanup

### Threading Model

- PJSUA2 callbacks run in library threads
- Event pumping happens in the main thread
- No manual threading required; PJSUA2 handles internal threading

## 📝 License

This project is provided as-is for educational and development purposes.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Add DTMF handling
- Implement call recording
- Add configuration file support
- Environment variable configuration
- Multiple simultaneous calls
- SIP MESSAGE support
- Presence/subscription handling

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

**Version**: 0.1.0  
**Last Updated**: October 2025  
**Python**: 3.11+  
**PJSUA2**: Compatible with PJSIP 2.x

