# Audio File Playback

The `--play-file` option allows you to play audio files to the remote party during a call.

## Requirements

1. **WAV Format**: PJSUA2's media player requires WAV files
2. **Recommended Settings**:
   - Sample Rate: 8000 Hz (standard telephony) or 16000 Hz
   - Channels: 1 (mono)
   - Format: 较低16-bit signed PCM

## Converting Audio Files

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

## How It Works

- When a call's media becomes active, if `--play-file` is specified, an `AudioMediaPlayer` is created
- **The bot automatically reads the WAV file duration** using Python's `wave` module
- The audio file is transmitted to the remote party **exactly once** (no looping)
- After the message finishes playing, the bot **waits for the configured delay** (default: 2 seconds)
- The call is **automatically hung up** after the delay
- Local speakers still receive audio from the remote side (for monitoring)
- The player is released when the call disconnects

## Automatic Duration Detection

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


