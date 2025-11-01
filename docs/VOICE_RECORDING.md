# Voice Recording

The `--enable-recording` option captures incoming caller audio streams to WAV files for analysis, archival, or compliance purposes.

## How It Works

1. **Automatic Capture**: When a call's media becomes active, if recording is enabled, separate `AudioMediaRecorder` instances are created for incoming and outgoing audio
2. **File Organization**: Recordings are stored in date-based directories: `{recording-path}/YYYY-MM-DD/`
3. **Separate Files**: Creates two files per call:
   - `{timestamp}_{caller}_incoming.wav` - Audio from the caller
   - `{timestamp}_{caller}_outgoing.wav` - Audio from the bot (welcome message)
4. **Parallel Operation**: Both recordings run alongside existing audio playback/bridging without interference
5. **Metadata Integration**: Recording information for both files is included in Elasticsearch call records

## Audio Format

- **Output**: WAV files (PCM encoding)
- **Sample Rate**: Inherited from call media (typically 8kHz or 16kHz)
- **Channels**: Mono (single caller stream)
- **Quality**: Telephony-grade audio suitable for voice analysis

## Storage Structure

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

## Recording Metadata in Elasticsearch

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

## Usage Examples

### Basic Recording
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording
```

### Custom Recording Directory
```bash
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording \
  --recording-path /var/voip-recordings
```

### Recording with Playback (IVR + Capture)
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


