# Recording Format Sync Fix - Summary

## Question
"Are we saving the calls in mp3 and sending them to the elastic search server as wav?"

## Answer
**No, this is not happening.** The system correctly sends the same format to Elasticsearch that is stored on disk (MP3 if ffmpeg is available, WAV otherwise).

## How It Works

### The Correct Flow
```
1. Call Recording  → WAV files created (PJSUA2 requirement)
2. Call Ends       → _cleanup_recording() called
3. Conversion      → WAV → MP3 (if ffmpeg available)
4. Path Update     → self._recording_file updated to .mp3 path
5. ES Metadata     → Built using updated paths
6. ES Logging      → Receives MP3 paths
7. Disk Cleanup    → WAV files deleted
```

### Result
- **Files on Disk**: `.mp3` (if ffmpeg available)
- **Elasticsearch**: `.mp3` paths (matching disk)
- **If No ffmpeg**: Both disk and ES use `.wav`

## Changes Made

### 1. Enhanced Logging in `calls.py`
Added explicit logging to show:
- When MP3 conversion is attempted
- Whether conversion succeeded or failed  
- What file format is sent to Elasticsearch

**Example Output:**
```
***Recording: attempting to convert incoming WAV to MP3...
***Recording: incoming file converted to MP3 at /path/incoming.mp3
***Elasticsearch: sending incoming recording as .MP3 format: http://example.com/incoming.mp3
```

### 2. Updated Documentation
- `docs/VOICE_RECORDING.md` - Clarified MP3 conversion process
- `docs/RECORDING_FORMAT_FIX.md` - Detailed technical explanation

## Key Points

✅ **No Bug Found**: The code was already working correctly
✅ **Sync Guaranteed**: File paths in Elasticsearch always match disk
✅ **Automatic Conversion**: WAV → MP3 happens transparently after each call
✅ **Graceful Fallback**: If ffmpeg unavailable, keeps WAV files
✅ **Better Logging**: Now explicitly shows what format is sent to ES

## Verification

After a call, you'll see these logs:
1. `***Recording: attempting to convert incoming WAV to MP3...`
2. `***Recording: incoming file converted to MP3 at ...`
3. `***Elasticsearch: sending incoming recording as .MP3 format: ...`

If these all show `.mp3`, the system is working correctly.

## Dependencies

- **ffmpeg** - Required for MP3 conversion
- Without it: recordings stay as WAV (larger but functional)

## File Changes

1. `src/pjsua_bot/calls.py`:
   - Added conversion status logging (lines ~891, 905, 952, 966)
   - Added Elasticsearch format logging (lines ~277-282)

2. `docs/VOICE_RECORDING.md`:
   - Updated audio format section
   - Added MP3 conversion explanation
   - Updated Elasticsearch metadata examples

3. `docs/RECORDING_FORMAT_FIX.md` (NEW):
   - Technical deep-dive on the fix

4. `RECORDING_SYNC_FIX_SUMMARY.md` (THIS FILE):
   - Quick reference summary













