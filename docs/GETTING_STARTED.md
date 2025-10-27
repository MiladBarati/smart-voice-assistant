# Getting Started - Quick Guide

This section walks you through running the bot from scratch, step by step.

## Step 1: Verify PJSUA2 Installation

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

If this fails, you need to install PJSUA2 (see [Prerequisites](../README.md#-prerequisites)).

## Step 2: Gather SIP Account Information

You'll need the following information from your SIP provider or PBX administrator:

- **Username/Extension**: e.g., `1001`, `john.doe`
- **Password**: Your SIP account password
- **Domain/Server**: e.g., `pbx.example.com`, `192.168.1.100`
- **Port** (optional): Usually `5060` for UDP/TCP, `5061` for TLS
- **Transport** (optional): `udp` (default), `tcp`, or `tls`

## Step 3: Test Basic Registration

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

## Step 4: Receive Your First Call

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

## Step 5: Make an Outbound Call

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

## Step 6: Add Audio Playback (Welcome Message)

Now let's play a welcome message when someone calls:

### A. Convert Your Audio File to WAV

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

### B. Run Bot with Audio Playback

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

### C. Customize Hangup Delay

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

## Step 7: Advanced Scenarios

### Scenario A: IVR/Auto-Attendant System

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

### Scenario B: Automated Announcement System

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

### Scenario C: Using TCP Transport (More Reliable)

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --transport tcp \
  --stay-online
```

### Scenario D: Secure TLS Connection

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

### Scenario E: Voice Recording System

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
4. Files stored as: `/var/recordings/2025-01-26/{timestamp}_{caller}_incoming.wav` and `/var/recordings/2025--fast 26/{timestamp}_{caller}_outgoing.wav`
5. Recording metadata included in Elasticsearch call records

**File naming**: `20250126_143022_1002_incoming.wav` and `20250126_143022_1002_outgoing.wav`
- Timestamp ensures uniqueness and chronological ordering
- Caller number for easy identification
- `_incoming` suffix for caller audio
- `_outgoing` suffix for bot audio

### Scenario F: Combined Playback and Recording

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

## Step 8: Running as a Service (Production)

For production deployments, you can run the bot as a system service:

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: "At system startup"
4. Action: Start a program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `register_bot.py --user 1001 --password secret123 --domain pbx.local --stay-online --auto-answer`
   - Start in: `C:\path\to\pjsua-installation`

### Linux (systemd)

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

## Step 9: Monitoring and Logs

### Increase Logging for Debugging

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --log-level 5
```

Log levels: `0` (none) to `6` (trace). Default is `3` (info).

### Save Logs to File

```bash
# Windows PowerShell:
python register_bot.py --user 1001 --password secret123 --domain pbx.local --stay-online 2>&1 | Tee-Object -FilePath bot.log

# Linux/Mac:
python register_bot.py --user 1001 --password secret123 --domain pbx.local --stay-online 2>&1 | tee bot.log
```

## Quick Reference: Common Commands

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

