# Usage Guide

This document provides detailed usage examples and common use cases.

## Basic Registration

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

## Full-Featured Bot

Use `register_bot.py` for advanced scenarios:

### 1. Register and Stay Online (Receive Calls)

```bash
python register_bot.py \
  --user 1001 Wikidata:Q71282533 \
  --password secret123 \
  --domain pbx.example.com \
  --stay-online \
  --auto-answer
```

### 2. Make Outbound Call

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --dest 1002 \
  --hangup-seconds 30
```

### 3. Auto-Answer with Welcome Message

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

### 4. Outbound Call with Audio Playback

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --dest sip:1002@pbx.example.com \
  --play-file announcement.wav \
  --hangup-seconds 60
```

### 5. Using TLS Transport

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

### 6. With Outbound Proxy

```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.example.com \
  --outbound-proxy "sip:proxy.example.com:5060;lr" \
  --stay-online
```

## Common Use Cases

### IVR System / Auto-Attendant
```bash
python register_bot.py \
  --user ivr-line \
  --password ivrpass \
  --domain pbx.local \
  --stay-online \
  --auto-answer \
  --play-file menu.wav
```

### Voicemail Notification System
```bash
python register_bot.py \
  --user notification-bot \
  --password botpass \
  --domain pbx.local \
  --dest 5551234567 \
  --play-file voicemail-alert.wav \
  --hangup-seconds 45
```

### Call Testing / Load Testing
```bash
python register_bot.py \
  --user test-1001 \
  --password testpass \
  --domain test-pbx.local \
  --dest 9999 \
  --hangup-seconds 5
```


