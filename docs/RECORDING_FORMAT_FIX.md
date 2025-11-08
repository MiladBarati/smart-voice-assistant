# Recording Format Fix - MP3 Conversion and Elasticsearch Sync

## Issue Summary

**Original Question**: "Are we saving the calls in mp3 and sending them to the elastic search server as wav?"

**Answer**: No, the system is working correctly. Both the storage and Elasticsearch records use the same format (MP3 if ffmpeg is available, WAV otherwise).

## How It Works

### Recording Flow

1. **During Call** (Recording Phase):
   - Audio is recorded in **WAV format** using PJSUA2's `AudioMediaRecorder`
   - Two files per call: `incoming.wav` and `outgoing.wav`
   - Files are stored in call-specific directories: `recordings/{date}/call_{timestamp}_{caller}/`

2. **After Call Ends** (Conversion Phase):
   - `_cleanup_recording()` is called to finalize recordings
   - If `ffmpeg` is available:
     - WAV files are converted to **MP3 format** (high quality: `-q:a 2`)
     - Original WAV files are **deleted** to save disk space
     - File path references (`self._recording_file` and `self._outgoing_recording_file`) are **updated to MP3 paths**
   - If `ffmpeg` is NOT available:
     - WAV files are kept as-is
     - File path references remain as WAV paths

3. **Elasticsearch Logging** (Metadata Phase):
   - Recording metadata is built using the **updated file paths** (MP3 or WAV)
   - Elasticsearch receives the **actual file format** that exists on disk
   - File paths in Elasticsearch always match the files on disk

### Code Flow

```python
# 1. Call disconnects
if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
    # 2. Convert recordings (WAV → MP3 if ffmpeg available)
    self._cleanup_recording()
    # At this point: self._recording_file is updated to .mp3 path (if conversion succeeded)
    
    # 3. Build metadata using updated paths
    recording_metadata = {}
    if self._recording_file and os.path.exists(self._recording_file):
        # This uses the MP3 path if conversion succeeded
        incoming_file_url = convert_recording_path_to_url(self._recording_file)
        recording_metadata["incoming"] = {
            "file_path": incoming_file_url,  # .mp3 path
            ...
        }
    
    # 4. Send to Elasticsearch
    es_logger.log_call_record(call_record)
```

## Improvements Made

### 1. Enhanced Logging

Added explicit logging to show what format is being sent to Elasticsearch:

```
***Recording: attempting to convert incoming WAV to MP3...
***Recording: incoming file converted to MP3 at /path/to/file.mp3
***Elasticsearch: sending incoming recording as .MP3 format: /url/to/file.mp3
***Elasticsearch: sending outgoing recording as .MP3 format: /url/to/file.mp3
```

If ffmpeg is not available:

```
***Recording: MP3 conversion failed (ffmpeg not available?), keeping WAV file
***Elasticsearch: sending incoming recording as .WAV format: /url/to/file.wav
```

### 2. Updated Documentation

- Updated `docs/VOICE_RECORDING.md` to clearly document:
  - Initial recording format (WAV during call)
  - Final storage format (MP3 after conversion)
  - Automatic conversion process
  - Elasticsearch metadata structure with MP3 paths

### 3. Verified Correct Behavior

The code already had the correct logic:
- ✅ Recordings start as WAV (PJSUA2 requirement)
- ✅ Converted to MP3 after call ends (if ffmpeg available)
- ✅ File references are updated before Elasticsearch logging
- ✅ Elasticsearch receives correct file paths matching disk

## Verification

To verify the system is working correctly, check the console logs after a call ends:

1. Look for: `***Recording: incoming file converted to MP3 at ...`
2. Look for: `***Elasticsearch: sending incoming recording as .MP3 format: ...`
3. Check that the file extension matches in both logs

## Requirements

- **ffmpeg**: Must be installed and available in PATH for MP3 conversion
- Without ffmpeg, recordings will be kept as WAV files (larger size but still functional)

## File Size Savings

MP3 conversion typically reduces file size by **80-90%**:
- 10-second WAV file (~160 KB at 8kHz mono)
- 10-second MP3 file (~20 KB with -q:a 2 quality)

## Related Files

- `src/pjsua_bot/calls.py` - Recording and conversion logic
- `src/pjsua_bot/utils.py` - `convert_wav_to_mp3()` function
- `docs/VOICE_RECORDING.md` - User documentation






