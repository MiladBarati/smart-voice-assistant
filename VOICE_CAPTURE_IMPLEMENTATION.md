# Voice Capture Implementation Summary

## Overview
This document summarizes the implementation of voice capture functionality for the PJSUA2 bot, including WAV file creation, timestamp-based naming, and Elasticsearch dashboard logging.

## Implementation Date
- Day 2 (Morning & Afternoon tasks completed)

## 1. Audio File Saving (Day 2, Morning)

### Implementation Details

#### WAV File Creation
- **Format**: 16-bit PCM, mono audio
- **Location**: Files are created in the `recordings/YYYY-MM-DD/` directory structure
- **Naming Convention**: `call_YYYYMMDD_HHMMSS_[incoming|outgoing].wav`
  - Example: `call_20250115_143022_incoming.wav`
  - Example: `call_20250115_143022_outgoing.wav`

#### Technical Implementation
- Uses PJSUA2's `AudioMediaRecorder` class for audio capture
- Two separate recording streams:
  - **Incoming**: Captures audio from the remote caller (stored in `self._recorder`)
  - **Outgoing**: Captures audio from the bot's welcome message (stored in `self._outgoing_recorder`)
- Files are automatically organized by date in subdirectories

#### Audio Format Verification
Current welcome message format:
- **Channels**: 1 (mono)
- **Sample Width**: 2 bytes (16-bit PCM)
- **Frame Rate**: 22050 Hz
- **Duration**: ~7.59 seconds

Note: PJSUA2 will record call audio in the same format as it receives it from the SIP call.

### Code Location
- File: `src/pjsua_bot/register_bot.py`
- Lines: 334-609 (recording setup)
- Lines: 699-811 (recording cleanup)

## 2. Dashboard Logging (Day 2, Afternoon)

### Implementation Details

#### New Fields Added to Call Record
The following fields have been added to the Elasticsearch call record schema:

1. **`voice_captured`** (boolean)
   - Indicates whether any voice was captured during the call
   - `true` if either incoming or outgoing recording exists
   - `false` if no recording was made

2. **`audio_file_path`** (string)
   - Path to the primary audio file
   - Prefers incoming recording over outgoing
   - Format: `recordings-domain_example_com/2025-10-25/call_20251025_175516_incoming.wav`

3. **`capture_duration`** (float)
   - Total duration of voice capture in seconds
   - Sum of incoming and outgoing recording durations
   - Rounded to 2 decimal places
   - Example: `7.42`

#### Recording Metadata Structure
Each call record now includes a `recording` object with detailed metadata:

```json
{
  "recording": {
    "incoming": {
      "file_path": "recordings/2025-10-25/call_20251025_175516_incoming.wav",
      "file_size_bytes": 123456,
      "recorded": true,
      "voice_captured": true,
      "audio_file_path": "recordings/2025-10-25/call_20251025_175516_incoming.wav",
      "capture_duration": 7.42
    },
    "outgoing": {
      "file_path": "recordings/2025-10-25/call_20251025_175516_outgoing.wav",
      "file_size_bytes": 45678,
      "recorded": true,
      "voice_captured": true,
      "audio_file_path": "recordings/2025-10-25/call_20251025_175516_outgoing.wav",
      "capture_duration": 5.21
    }
  },
  "voice_captured": true,
  "audio_file_path": "recordings/2025-10-25/call_20251025_175516_incoming.wav",
  "capture_duration": 12.63
}
```

#### New Elasticsearch Method
Added `log_voice_capture_event()` method to the Elasticsearch client for logging individual capture events.

- **File**: `src/pjsua_bot/elasticsearch_client.py`
- **Method**: `log_voice_capture_event()`
- **Lines**: 395-453

### Usage
```python
es_logger.log_voice_capture_event(
    event_type="voice_capture_started",
    call_id="some-call-id",
    voice_captured=True,
    audio_file_path="/path/to/file.wav",
    capture_duration=7.42
)
```

## 3. Tracking Changes

### Duration Tracking
- Recording start time is captured when recording begins
- Duration is calculated when recording stops
- Stored in:
  - `self._recording_duration` (incoming)
  - `self._outgoing_recording_duration` (outgoing)

### Code Changes
1. **Added duration tracking attributes** (Lines 339-346):
   - `self._recording_start_time`
   - `self._recording_duration`
   - `self._outgoing_recording_start_time`
   - `self._outgoing_recording_duration`

2. **Capture start time** (Lines 552, 605):
   - Start time is set when recording begins

3. **Calculate duration** (Lines 737-739, 796-798):
   - Duration is calculated during cleanup

4. **Enhanced metadata** (Lines 405-418, 453-477):
   - Added voice_captured, audio_file_path, and capture_duration to all metadata

## 4. Testing (Day 3)

### Test Checklist

#### Audio Quality
- [ ] Verify audio is clear and intelligible
- [ ] Check for audio clipping or distortion
- [ ] Confirm proper audio synchronization

#### File Integrity
- [ ] Verify files are created successfully
- [ ] Check file sizes are reasonable (> 0 bytes)
- [ ] Confirm files can be opened in standard audio players
- [ ] Validate WAV headers are correct

#### Dashboard Display
- [ ] Check Elasticsearch dashboard shows voice_captured field
- [ ] Verify audio_file_path is displayed correctly
- [ ] Confirm capture_duration is accurate
- [ ] Test filtering by voice_captured=true
- [ ] Validate recording metadata is nested correctly

#### Real Call Testing
- [ ] Test with incoming calls from different extensions
- [ ] Verify both incoming and outgoing recording works
- [ ] Test with short calls (< 5 seconds)
- [ ] Test with longer calls (> 30 seconds)
- [ ] Verify proper cleanup when calls end abruptly

### Command Line Usage

Enable recording with:
```bash
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password secret \
  --domain example.com \
  --stay-online \
  --enable-recording \
  --recording-path ./recordings
```

### Manual Verification
Check that files exist:
```bash
ls -l recordings/$(date +%Y-%m-%d)/
```

Query Elasticsearch:
```bash
curl -X GET "localhost:9200/pjsua-calls/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must": [
        {"term": {"event_type": "call_record"}},
        {"term": {"voice_captured": true}}
      ]
    }
  }
}
'
```

## 5. File Structure

```
recordings/
├── 2025-01-15/
│   ├── call_20250115_143022_incoming.wav
│   ├── call_20250115_143022_outgoing.wav
│   ├── call_20250115_144536_incoming.wav
│   └── call_20250115_144536_outgoing.wav
└── 2025-01-16/
    └── ...
```

## 6. Elasticsearch Schema

The call records now include:
- Top-level fields: `voice_captured`, `audio_file_path`, `capture_duration`
- Nested recording object with full details
- Compatible with existing dashboard queries

## Summary

All Day 2 tasks have been completed:
✅ WAV file creation and writing functionality implemented
✅ Timestamp-based file naming (call_YYYYMMDD_HHMMSS.wav format)
✅ Proper audio format handling (mono, 16-bit PCM)
✅ Elasticsearch logging extended with new fields
✅ Dashboard schema updated for voice capture events
✅ Duration tracking implemented

Ready for Day 3 testing phase.

