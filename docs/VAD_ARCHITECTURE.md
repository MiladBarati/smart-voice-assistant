# Voice Activity Detection (VAD) Architecture

## Overview

The VAD module provides a modular, maintainable architecture for voice activity detection using Silero VAD models. The system processes incrementally growing WAV files in real-time, detecting speech activity and managing voice chunks.

## Architecture

The VAD system follows a modular design with clear separation of concerns:

```
SileroVAD (Orchestrator)
├── StreamingWavReader      # Incremental WAV file reading
├── AudioPreprocessor       # Audio preprocessing (resampling, gain)
├── VADInferenceEngine     # Model inference (TorchScript/ONNX)
├── ChunkManager           # Voice chunk detection and management
├── SilenceTracker         # Silence tracking and bot playback awareness
├── SileroModelLoader      # Model loading with fallback strategies
└── ThrottledLogger        # Time-based log throttling
```

## Components

### SileroVAD (Main Orchestrator)

**File:** `src/pjsua_bot/vad/silero.py`

The main orchestrator class that coordinates all VAD components. Provides a simple API for:
- Processing new audio frames incrementally
- Tracking last speech time
- Managing voice chunks
- Tracking silence periods

**Key Methods:**
- `process_new_audio(monotonic_time_fn)`: Process newly appended audio frames
- `get_chunks()`: Get all finalized voice chunks
- `get_speech_duration()`: Get total speech duration
- `get_silence_duration(monotonic_time_fn)`: Get total silence duration

### StreamingWavReader

**File:** `src/pjsua_bot/vad/audio_reader.py`

Handles incremental reading of growing WAV files. Maintains internal cursors to only read newly appended frames.

**Features:**
- Automatic WAV header parsing
- Fallback to manual parsing for streaming files
- Frame tracking to avoid re-reading data
- Sample rate detection

**WavInfo Dataclass:**

The `WavInfo` dataclass stores WAV file metadata when the standard `wave` module fails to parse streaming files:

```python
@dataclass
class WavInfo:
    channels: int      # Number of audio channels
    sampwidth: int     # Sample width in bytes
    framerate: int     # Sample rate in Hz
    data_offset: int   # Byte offset to audio data chunk
```

**Important:** `WavInfo` is a dataclass and must be accessed via attributes (e.g., `info.channels`), not iterated or unpacked as a tuple. The `ManualWavParser` creates `WavInfo` instances when manual parsing is needed.

### AudioPreprocessor

**File:** `src/pjsua_bot/vad/audio_preprocessor.py`

Handles all audio preprocessing steps:
- Conversion from numpy arrays to PyTorch tensors
- Gain adjustment for low-level telephony audio (default 3.0x)
- Resampling to target sample rate (8000 or 16000 Hz)
- Window size calculation for different sample rates

**Features:**
- Caches resamplers by input sample rate
- Supports 8kHz and 16kHz target rates
- Automatic fallback if resampling unavailable

### VADInferenceEngine

**File:** `src/pjsua_bot/vad/inference_engine.py`

Provides a unified interface for VAD inference across different model formats:
- **TorchScript models**: Original PyTorch format
- **ONNX Runtime sessions**: Optimized inference
- **ONNX callable wrappers**: torch.hub format

**State Management:**
- Automatically manages hidden states for stateful ONNX models
- Supports separate h/c states (Silero VAD v4/v5)
- Supports combined state (older versions)
- Handles state initialization and updates

### ChunkManager

**File:** `src/pjsua_bot/vad/chunk_manager.py`

Manages voice chunk detection and boundary management:
- Detects chunk boundaries based on speech/silence
- Enforces minimum/maximum chunk durations
- Saves chunks to disk (WAV or MP3)
- Tracks chunk metadata (timestamps, sample indices)

**State Machine:**
- Starts new chunk on speech detection
- Extends chunk during continuous speech
- Finalizes chunk on silence or max duration
- Handles chunk splitting for long utterances

**Manual WAV Parsing:**

When the standard `wave` module fails (e.g., with streaming files), `ChunkManager` uses `StreamingWavReader.manual_wav_info` which contains a `WavInfo` dataclass. The code correctly accesses `WavInfo` attributes directly (`info.channels`, `info.sampwidth`, etc.) rather than treating it as iterable or unpacking it as a tuple.

### SilenceTracker

**File:** `src/pjsua_bot/vad/silence.py`

Tracks silence periods and bot playback state:
- Distinguishes between caller silence and bot playback
- Prevents false silence detection during bot speech
- Tracks total silence duration
- Tracks bot playback duration

**Key Feature:**
- Bot playback awareness prevents treating bot's own audio as caller speech

### SileroModelLoader

**File:** `src/pjsua_bot/vad/silero_model_loader.py`

Handles model loading with multiple fallback strategies using a modular, maintainable architecture.

**Key Features:**
- **Programmatic Strategy Generation**: Strategies are generated programmatically rather than hardcoded, making it easy to modify or extend
- **Unified Cache Management**: Single `clear_cache()` method handles all cache clearing scenarios
- **Modular Design**: Separate methods for ONNX and TorchScript handling, strategy execution, and model initialization
- **Class-level Caching**: Shares loaded models across instances to reduce memory usage
- **Reactive Error Recovery**: Automatically clears cache when encountering `_construct` errors

**Loading Strategy Order:**
1. **ONNX Strategies** (preferred for PyTorch 2.5+):
   - ONNX via torch.hub (normal load)
   - ONNX via torch.hub (force reload)
2. **TorchScript Strategies** (with trust_repo):
   - TorchScript force reload with trust_repo
   - TorchScript normal load with trust_repo
3. **TorchScript Fallback** (original behavior):
   - TorchScript force reload (fallback)
   - TorchScript normal load (fallback)

**Architecture:**
- `_generate_strategies()`: Programmatically generates loading strategies
- `_try_strategy()`: Executes a single loading strategy
- `_handle_onnx_model()`: Handles ONNX model results (wrapper or file path)
- `_handle_torchscript_model()`: Handles TorchScript model results
- `clear_cache()`: Unified cache clearing with reason logging
- `try_reuse_cached_model()`: Attempts to reuse previously loaded models

**Model Format Support:**
- **ONNX Callable Wrapper**: Most common format from torch.hub
- **ONNX File Path**: Direct ONNX Runtime session loading
- **TorchScript**: Original PyTorch format for compatibility

**Error Handling:**
- Graceful fallback through strategy list
- Automatic cache clearing on `_construct` errors
- Detailed error logging for debugging
- Continues trying strategies until one succeeds or all fail

### ThrottledLogger

**File:** `src/pjsua_bot/vad/throttled_logger.py`

Utility to prevent log spam by throttling messages based on time intervals.

**Usage:**
```python
logger = ThrottledLogger(interval_seconds=5.0)
logger.log_if_ready(lambda: print("This won't spam"))
```

## Data Flow

1. **Audio Reading**: `StreamingWavReader` reads new frames from growing WAV file
2. **Preprocessing**: `AudioPreprocessor` converts to tensor, applies gain, resamples
3. **Inference**: `VADInferenceEngine` runs model inference on 32ms windows
4. **Chunk Management**: `ChunkManager` detects boundaries and manages chunks
5. **Silence Tracking**: `SilenceTracker` tracks silence periods (excluding bot playback)
6. **Speech Time**: `SileroVAD` updates `last_speech_time_monotonic` for hangup decisions

## Configuration

**File:** `src/pjsua_bot/vad/config.py`

```python
@dataclass
class VADConfig:
    target_sample_rate: int = 16000
    threshold: float = 0.15  # Lower for telephony audio
    min_chunk_duration_sec: float = 5.0
    max_chunk_duration_sec: float = 15.0
    min_silence_for_boundary_sec: float = 0.5
    keep_wav_for_asr: bool = False  # Keep WAV instead of MP3
```

## Usage Example

```python
from pjsua_bot.vad import SileroVAD, VADConfig

# Initialize VAD
vad = SileroVAD(
    wav_path="/path/to/recording.wav",
    config=VADConfig(threshold=0.15),
    chunks_output_dir="/path/to/chunks"
)

# In event loop
while call_active:
    vad.process_new_audio(lambda: time.time())
    
    # Check for silence timeout
    if vad.last_speech_time_monotonic:
        silence = time.time() - vad.last_speech_time_monotonic
        if silence > 5.0:
            hangup()
    
    # Get chunks for ASR processing
    chunks = vad.get_chunks()
    for chunk in chunks:
        if chunk.file_path:
            process_chunk(chunk.file_path)
```

## Refactoring Benefits

The refactored architecture provides:

1. **Modularity**: Each component has a single, clear responsibility
2. **Maintainability**: Easier to understand, test, and modify
3. **Testability**: Components can be tested independently
4. **Extensibility**: Easy to add new features or swap implementations
5. **Readability**: Reduced complexity from 784 lines to ~320 lines in main file

### SileroModelLoader Refactoring

The `SileroModelLoader` was refactored to improve simplicity and maintainability:

- **Before**: ~389 lines with hardcoded strategy list, duplicated cache clearing logic, and complex nested conditionals
- **After**: ~380 lines with programmatic strategy generation, unified cache management, and modular method structure
- **Complexity Rating**: Improved from 4/10 to 7/10

**Key Improvements:**
- Consolidated cache clearing into a single method
- Programmatic strategy generation instead of hardcoded list
- Extracted ONNX and TorchScript handling into separate methods
- Simplified main `load_model()` method (reduced from ~136 lines to ~40 lines)
- Better separation of concerns with focused, single-purpose methods

## Model Support

The system supports multiple model formats:
- **TorchScript**: Original PyTorch format (compatible with all PyTorch versions)
- **ONNX Runtime**: Optimized inference (faster, better compatibility)
- **ONNX Callable**: Wrapper format from torch.hub

The model loader automatically selects the best available format with fallback strategies.

## Performance Considerations

- **Resampling**: Cached per input sample rate to avoid recreation
- **Model Caching**: Class-level caching shares models across instances
- **Log Throttling**: Prevents log spam in high-frequency event loops
- **Incremental Processing**: Only processes new frames, not entire file
- **State Management**: Efficient state updates for stateful models

## Error Handling

- Graceful degradation if dependencies unavailable
- Automatic fallback between model formats
- Error recovery with cache clearing
- Throttled error logging to prevent spam

