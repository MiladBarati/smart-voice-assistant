# Audio Playback, Recording, and Elasticsearch Integration

This guide merges the audio playback/recording reference with the Elasticsearch integration manual. It explains how media flows through the bot, how artifacts are stored, and how the resulting metadata lands in Elasticsearch for downstream observability.

## Audio File Playback

The `--play-file` flag streams a prerecorded WAV to the remote party once the call media becomes active.

### Requirements

1. **WAV container**: PJSUA2's media player only accepts WAV input.
2. **Recommended format**:
   - Sample rate: 8000 Hz (telephony) or 16000 Hz.
   - Channels: mono.
   - Encoding: 16-bit signed PCM.

### Converting Audio Files

Use FFmpeg to normalize audio assets before deploying them:

```bash
# Convert to 8 kHz mono WAV (telephony)
ffmpeg -i input.m4a -ar 8000 -ac 1 -sample_fmt s16 output.wav

# Convert to 16 kHz mono WAV (higher fidelity)
ffmpeg -i input.mp3 -ar 16000 -ac 1 -sample_fmt s16 output.wav

# Batch convert all m4a files in the current directory
for file in *.m4a; do
  ffmpeg -i "$file" -ar 8000 -ac 1 -sample_fmt s16 "${file%.m4a}.wav"
done
```

### Playback Flow

- When call media becomes active and `--play-file` is present, an `AudioMediaPlayer` boots.
- The bot inspects the WAV using Python's `wave` module to determine its precise duration.
- Audio is streamed once (no looping). Local speakers still receive remote audio for monitoring.
- After playback completes, the bot waits for the configured hang-up delay (default: 2 seconds) before terminating the call.
- Resources are released when the call disconnects to avoid leaks.

### Automatic Duration Detection

```
***WAV file duration: 6.23 seconds
***Using actual WAV duration: 6.23 seconds
***Welcome message playback started
***Will stop player after 6.23 seconds
***Stopped player transmission to prevent looping
***Welcome message finished. Will hang up in 2 seconds
***Auto-hanging up after welcome message
```

Duration awareness prevents truncated prompts and uncontrolled looping.

## Call Recording

### Overview

1. **Automatic capture**: When media activates and recording is enabled, independent `AudioMediaRecorder` instances start for the incoming (caller) and outgoing (bot) streams.
2. **Parallel operation**: Recording runs alongside playback or bridging without affecting live audio.
3. **File organization**: Each call writes `incoming` and `outgoing` files under `recordings/YYYY-MM-DD/`.
4. **Metadata integration**: Final file paths, durations, and capture state flow into the Elasticsearch call document.

### Recording Flow

1. **Capture phase**
   - Audio lands as WAV (PCM) inside `recordings/{date}/call_{timestamp}_{caller}/`.
2. **Conversion phase**
   - `_cleanup_recording()` finalizes file handles.
   - If `ffmpeg` is available:
     - WAV files convert to MP3 using `libmp3lame -q:a 2`.
     - Original WAVs are deleted to save disk.
     - Attributes such as `self._recording_file` update to the MP3 paths.
   - Without `ffmpeg`, WAV files remain and are referenced directly.
3. **Metadata phase**
   - Elasticsearch payloads reference whichever format survives on disk, so indexed records mirror reality.

### Storage Layout

```
recordings/
├── 2025-01-26/
│   ├── 20250126_143022_1001_incoming.mp3
│   ├── 20250126_143022_1001_outgoing.mp3
│   ├── 20250126_143155_1002_incoming.mp3
│   └── 20250126_143155_1002_outgoing.mp3
├── 2025-01-27/
│   └── 20250127_091230_1003_incoming.mp3
```

*Files begin as `.wav` and convert to `.mp3` automatically when FFmpeg is available.*

### Audio Format & Conversion

- **Initial recording**: WAV (PCM, mono, 8 kHz or 16 kHz depending on negotiated media).
- **Final storage**: MP3 when conversion succeeds; WAV otherwise.
- **Compression**: `libmp3lame -q:a 2` typically shrinks files by 80–90%.
- **Fallback**: Conversion failures are logged and metadata keeps pointing at the WAV files.

Expected log sequence:

```
***Recording: attempting to convert incoming WAV to MP3...
***Recording: incoming file converted to MP3 at /path/to/file.mp3
***Elasticsearch: sending incoming recording as .MP3 format: /url/to/file.mp3
```

### Elasticsearch Metadata Example

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

### Verification Checklist

After each call:

1. Confirm conversion logs (MP3 success or explicit WAV fallback).
2. Ensure Elasticsearch entries reference the same extension as the files on disk.
3. Inspect durations for both `incoming` and `outgoing` recordings.

### Usage Examples

```bash
# Basic recording
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording

# Custom recording directory
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --enable-recording \
  --recording-path /var/voip-recordings

# Recording with playback (IVR + capture + logging)
python register_bot.py \
  --user 1001 \
  --password secret123 \
  --domain pbx.local \
  --stay-online \
  --play-file menu.wav \
  --enable-recording \
  --recording-path ./ivr-recordings
```

### Implementation Notes

- `src/pjsua_bot/calls.py` orchestrates playback, recording, conversion, and metadata logging.
- `src/pjsua_bot/utils.py` holds helpers such as `convert_wav_to_mp3()`.
- Install FFmpeg and make sure it is on `PATH` to unlock MP3 conversion.

## Elasticsearch Integration

The Elasticsearch logger receives synchronized metadata from playback, recording, and other call lifecycle events to power dashboards, alerts, and audits.

### Overview

- Structured documents track registration, call state, media, voice capture, and bot metadata.
- A final call record is indexed when the session ends, acting as the canonical summary.
- Logging is asynchronous so failures never block SIP handling.
- A single index prefix (`pjsua-calls` by default) simplifies retention and visualization.

### Capabilities

- Real-time monitoring and alerting on call outcomes.
- Unified analytics by correlating event-level and per-call summaries.
- Troubleshooting support through consistent host, user, and domain metadata.
- Optional batch logging (`log_batch_events`) for high-volume workloads.

### Installation & Dependencies

The project pins compatible versions in `pyproject.toml`. Install extras when running standalone tooling:

```bash
pip install "elasticsearch>=7.0.0,<8.0.0"
pip install python-dotenv
```

### Configuration

Environment variables (typically via `.env`) drive the connection and index naming:

```bash
# Elasticsearch configuration
ES_HOST="your-elasticsearch-host"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="your-password"
ES_USE_SSL="false"
ES_VERIFY_CERTS="false"
ELASTIC_INDEX_PREFIX="pjsua-calls"

# Optional Kibana helpers
KIBANA_URL="https://your-kibana-url"
```

**Defaults**

- Host: `localhost`
- Port: `9200`
- Username: `elastic`
- Password: empty
- SSL: `false`
- Verify certs: `false`
- Index prefix: `pjsua-calls`

**Security and operations**

- Keep credentials in env vars or secret stores—never commit them.
- Enable SSL and certificate verification in production.
- Rotate credentials without redeploying the bot.

### Connection Behaviour

`ElasticsearchLogger` composes the connection URL from the above configuration. It calls `info()` before pinging, caches connectivity state, and retries automatically whenever a write follows a disconnect.

### Index Strategy

- Default index: `${ELASTIC_INDEX_PREFIX}` (`pjsua-calls` by default).
- All document types share the same index for simpler aggregation.
- Create a matching index pattern in Kibana so dashboards auto-discover fields.

### Event Documents

Event writers include host metadata and timestamps and omit null fields. Every document sets `service: "pjsua2"` for filtering.

- **Call events**: `incoming_call`, `outbound_call`, `call_ringing`, `call_connected`, `call_disconnected`, `call_state_change`, `call_answered`, `call_error`.
- **Registration events**: `registration_attempt`, `registration_success`, `registration_failed`.
- **Media events**: `media_active`, `playback_started`, `playback_finished`, `audio_bridged`, `media_error`.
- **Voice capture events**: `voice_capture_started`, `voice_capture_finished`, `voice_capture_error` (carry `audio_file_path`, `capture_duration`, `voice_captured`).

### Structured Call Record

When a call disconnects, the logger emits a comprehensive record. Apply the sample mapping if you want strict typing:

```json
{
  "mappings": {
    "properties": {
      "call_id":        {"type": "keyword"},
      "caller_number":  {"type": "keyword"},
      "callee_ext":     {"type": "keyword"},
      "start_time":     {"type": "date"},
      "end_time":       {"type": "date"},
      "duration_sec":   {"type": "integer"},
      "status":         {"type": "keyword"},
      "direction":      {"type": "keyword"},
      "media":          {"type": "object", "enabled": true},
      "bot":            {"type": "object", "enabled": true},
      "host":           {"type": "keyword"},
      "ingest_ts":      {"type": "date"}
    }
  }
}
```

Key points:

- `call_id` uses UUIDs to stay unique across restarts.
- `media` and `bot` sub-documents summarize playback, recording, auto-answer, user, and domain.
- `ingest_ts` defaults to indexing time when omitted.

### Running with Elasticsearch Logging Enabled

The logger initializes automatically:

```bash
python register_bot.py --user username --password secret --domain domain.com --stay-online
```

Combine with the playback/recording flags shown earlier to stream prompts, capture both legs, and log a unified call record.

### Testing the Integration

Run the connectivity smoke test before deploying:

```bash
python test_elasticsearch.py
```

It reports cluster health and indexes sample documents for each event type.

### Viewing Data in Kibana

1. Navigate to `${KIBANA_URL}` (or your Kibana endpoint).
2. Create an index pattern for `pjsua-calls`.
3. Explore events in Discover (`event_type:call_*`, etc.).
4. Build dashboards for call duration histograms, media success, error rates, and voice capture coverage.

### Monitoring & Alerts

- Track call success/failure rates, registration state, playback success, and error counts.
- Sample queries:
  - Calls in the last hour: `event_type:call_* AND @timestamp:[now-1h TO now]`
  - Failed registrations: `event_type:registration_failed`
  - Call or media errors: `event_type:(call_error OR media_error)`
  - Call duration analysis: `event_type:call_disconnected AND duration:>0`

### Troubleshooting

- **Connection issues**: Verify cluster reachability, credentials, and SSL settings.
- **Logging gaps**: Review Python logs for exceptions, confirm index privileges, and ensure disk space.
- **Performance**: Logging is non-blocking, but monitor cluster load and refresh intervals during sustained volume.

### Related Files

- `src/pjsua_bot/register_bot.py` — emits events during the call lifecycle.
- `src/pjsua_bot/calls.py` — assembles playback, recording, and final call records.
- `src/pjsua_bot/elasticsearch_client.py` — logger implementation.
- `src/pjsua_bot/utils.py` — helper utilities (e.g., audio conversion).
- `test_elasticsearch.py` — connectivity and smoke-test script.

### Future Enhancements

- Expanded CLI control for Elasticsearch configuration.
- Custom log filtering/formatting and curated dashboards.
- Automated alerting on audio quality metrics.
- Optional integration with additional monitoring backends.
