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

- **Initial Recording**: WAV files (PCM encoding) during the call
- **Final Storage**: MP3 files (automatically converted after call ends if `ffmpeg` is available)
- **Sample Rate**: Inherited from call media (typically 8kHz or 16kHz)
- **Channels**: Mono (single caller stream)
- **Quality**: Telephony-grade audio suitable for voice analysis
- **Compression**: MP3 conversion uses high-quality settings (libmp3lame -q:a 2) to reduce file size while maintaining audio quality

### Automatic MP3 Conversion

After each call ends, the system automatically:
1. Converts WAV recordings to MP3 format using `ffmpeg` (if available)
2. Deletes the original WAV files to save disk space
3. Updates all file paths in Elasticsearch to reference the MP3 files

If `ffmpeg` is not installed or conversion fails, the original WAV files are kept.

## Storage Structure

```
recordings/
├── 2025-01-26/
│   ├── 20250126_143022_1001_incoming.mp3  # Converted from WAV after call
│   ├── 20250126_143022_1001_outgoing.mp3
│   ├── 20250126_143155_1002_incoming.mp3
│   ├── 20250126_143155_1002_outgoing.mp3
├── 2025-01-27/
│   ├── 20250127_091230_1003_incoming.mp3
│   └── 20250127_091230_1003_outgoing.mp3
```

**Note**: Files are initially recorded as `.wav` during the call, then automatically converted to `.mp3` after the call ends (if `ffmpeg` is available).

## Recording Metadata in Elasticsearch

Call records include a `recording` field when recording is enabled. The file paths in Elasticsearch always reference the **final file format** (MP3 if conversion succeeded, WAV if `ffmpeg` is unavailable):

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "caller_number": "1002",
  "recording": {
    "incoming": {
      "file_path": "/var/recordings/2025-01-26/20250126_143022_1002_incoming.mp3",
      "file_size_bytes": 45760,
      "recorded": true,
      "voice_captured": true,
      "capture_duration": 7.42
    },
    "outgoing": {
      "file_path": "/var/recordings/2025-01-26/20250126_143022_1002_outgoing.mp3",
      "file_size_bytes": 28000,
      "recorded": true,
      "voice_captured": true,
      "capture_duration": 5.21
    }
  },
  "voice_captured": true,
  "audio_file_path": "/var/recordings/2025-01-26/20250126_143022_1002_incoming.mp3",
  "capture_duration": 12.63
}
```

**Important**: The file paths always match the actual files on disk. If MP3 conversion succeeds, `.mp3` paths are logged; if conversion fails, `.wav` paths are logged.

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


