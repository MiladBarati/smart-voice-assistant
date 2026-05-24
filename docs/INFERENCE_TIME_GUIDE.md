# Measuring Inference Time for omnilingual-asr

## Quick Answer

Your updated `test_omnilingual.py` now shows:
- ⏱️ **Model load time**
- ⚡ **Inference time**
- 📊 **Real-Time Factor (RTF)**
- 📝 **Transcription result**

## Run the Test

```powershell
.\docker-run.ps1 -TestASR
```

**Expected output:**
```
Testing omnilingual-asr installation...

[OK] omnilingual-asr imported successfully
[OK] ASRInferencePipeline imported successfully

Loading ASR pipeline (omniASR_CTC_1B)...
[OK] ASR pipeline loaded successfully
    Model load time: 3.45 seconds

Testing transcription with /app/assets/audio/welcome_message.wav...
    Audio duration: 8.50 seconds
[OK] Transcription successful!
    Inference time: 12.30 seconds
    Real-Time Factor (RTF): 1.45x
    (1.45x means it takes 1.45 seconds to process 1 second of audio)

    Transcription result:
    [Your transcribed text here...]
```

---

## Understanding the Metrics

### 1. **Model Load Time**
Time to load the model into memory (first time only).
- **First run:** 3-10 seconds (loading from cache)
- **Cold start:** Longer if downloading model

### 2. **Inference Time**
Time to actually transcribe the audio.
- **What it means:** How long it takes to process your audio file
- **Varies by:** Audio length, CPU/GPU, model size

### 3. **Real-Time Factor (RTF)**
Most important metric for ASR performance.

```
RTF = Inference Time / Audio Duration
```

**Examples:**
- `RTF = 0.5x` → Takes 0.5s to process 1s of audio ✅ **Fast!**
- `RTF = 1.0x` → Takes 1s to process 1s of audio ⚡ **Real-time**
- `RTF = 2.0x` → Takes 2s to process 1s of audio ⚠️ **Slow**

**Interpretation:**
- `RTF < 1.0` ✅ Faster than real-time (good for live transcription)
- `RTF = 1.0` ⚡ Exactly real-time (marginal for live)
- `RTF > 1.0` ⚠️ Slower than real-time (batch only)

---

## Methods to Measure Inference Time

### Method 1: Use the Test Script (Simplest)

```powershell
.\docker-run.ps1 -TestASR
```

Shows complete metrics automatically.

### Method 2: Custom Measurement Script

```powershell
# In Docker shell
.\docker-run.ps1 -Shell

# Run measurement utility
python3 examples/measure_inference_time.py recordings/your_audio.wav
```

**Output:**
```
======================================================================
INFERENCE RESULTS
======================================================================

📊 Audio Information:
  Duration: 8.50 seconds
  Sample rate: 16000 Hz
  Frames: 136,000

🔧 Model Loading:
  Load time: 3.45 seconds
  Warm-up time: 12.30 seconds

⚡ Inference Performance:
  Average time: 11.80 seconds
  Min time: 11.65 seconds
  Max time: 12.05 seconds

🎯 Real-Time Factor (RTF):
  RTF: 1.39x
  1.39x speed (takes 1.39s to process 1s of audio)
  ⚠️  Slower than real-time (may struggle with live)

📝 Transcription:
  [Your transcribed text...]
======================================================================
```

### Method 3: In Your Own Code

#### Option A: Context Manager

```python
from examples.timing_utils import InferenceTimer

# Measure transcription time
with InferenceTimer("ASR Transcription"):
    result = pipeline.transcribe([audio_file], lang=["fas_Arab"], batch_size=1)

# Output: [TIMER] ASR Transcription: 11.234 seconds
```

#### Option B: Decorator

```python
from examples.timing_utils import time_inference

@time_inference
def transcribe_audio(audio_path):
    return pipeline.transcribe([audio_path], lang=["fas_Arab"], batch_size=1)

# Use it
result = transcribe_audio("audio.wav")
# Output: [TIMER] transcribe_audio: 11.234 seconds
```

#### Option C: Manual Timing

```python
import time

start = time.time()
result = pipeline.transcribe([audio_file], lang=["fas_Arab"], batch_size=1)
elapsed = time.time() - start

print(f"Inference time: {elapsed:.2f} seconds")
```

#### Option D: Full Metrics

```python
from examples.timing_utils import measure_rtf
import time
import wave

# Get audio duration
with wave.open(audio_file, 'rb') as wf:
    frames = wf.getnframes()
    rate = wf.getframerate()
    audio_duration = frames / float(rate)

# Measure inference
start = time.time()
result = pipeline.transcribe([audio_file], lang=["fas_Arab"], batch_size=1)
inference_time = time.time() - start

# Calculate metrics
rtf_info = measure_rtf(audio_duration, inference_time)

print(f"Audio duration: {audio_duration:.2f}s")
print(f"Inference time: {inference_time:.2f}s")
print(f"RTF: {rtf_info['rtf']:.2f}x")
print(f"Speed: {rtf_info['speed']}")
print(f"Suitable for: {rtf_info['suitable_for']}")
```

---

## Optimizing Inference Speed

### 1. **Use GPU (if available)**

```python
# Instead of CPU
pipeline = ASRInferencePipeline(model_card="omniASR_CTC_1B", device="cuda")
```

**Expected improvement:** 5-10x faster

### 2. **Use Smaller Model**

```python
# Smaller model = faster inference
pipeline = ASRInferencePipeline(model_card="omniASR_CTC_300M")  # Smaller
```

**Trade-off:** Faster but slightly less accurate

### 3. **Batch Processing**

```python
# Process multiple files at once
results = pipeline.transcribe(
    [file1, file2, file3],
    lang=["fas_Arab", "fas_Arab", "fas_Arab"],
    batch_size=4  # Higher batch size
)
```

### 4. **Warm-up the Model**

```python
# Run once to warm up (first run is slower)
_ = pipeline.transcribe(["dummy.wav"], lang=["fas_Arab"], batch_size=1)

# Now measure actual performance
start = time.time()
result = pipeline.transcribe([real_audio], lang=["fas_Arab"], batch_size=1)
elapsed = time.time() - start
```

---

## Benchmarking Tips

### 1. **Run Multiple Times**

First inference is slower (cold start). Average multiple runs:

```python
import time

times = []
for i in range(5):
    start = time.time()
    result = pipeline.transcribe([audio_file], lang=["fas_Arab"])
    times.append(time.time() - start)

avg_time = sum(times) / len(times)
print(f"Average: {avg_time:.2f}s")
print(f"Min: {min(times):.2f}s")
print(f"Max: {max(times):.2f}s")
```

### 2. **Test with Different Audio Lengths**

RTF should be consistent across audio lengths:

```python
test_files = [
    "short_5s.wav",
    "medium_30s.wav",
    "long_120s.wav"
]

for audio in test_files:
    # Measure and compare RTF
    ...
```

### 3. **Monitor System Resources**

```bash
# In Docker shell
# CPU usage
top

# Memory usage
free -h

# GPU usage (if available)
nvidia-smi
```

---

## Typical Performance

### CPU (Docker on Windows)
- **Load time:** 3-5 seconds
- **RTF:** 1.5-3.0x (slower than real-time)
- **8s audio:** ~15-25 seconds to process
- **Use case:** Batch processing, offline transcription

### GPU (CUDA)
- **Load time:** 3-5 seconds
- **RTF:** 0.1-0.5x (much faster than real-time)
- **8s audio:** ~1-4 seconds to process
- **Use case:** Real-time transcription, large batches

---

## Quick Reference

### Files Created

| File | Purpose |
|------|---------|
| `test_omnilingual.py` | Automatic test with metrics |
| `examples/measure_inference_time.py` | Detailed benchmarking tool |
| `examples/timing_utils.py` | Reusable timing utilities |

### Commands

```powershell
# Quick test
.\docker-run.ps1 -TestASR

# Detailed benchmark
.\docker-run.ps1 -Shell
python3 examples/measure_inference_time.py recordings/test.wav

# Your own code (use timing_utils.py)
python3 your_script.py
```

### Key Metrics

| Metric | Formula | Good Value |
|--------|---------|------------|
| **Inference Time** | End - Start | < Audio duration |
| **RTF** | Inference / Duration | < 1.0 |
| **Throughput** | Files / Second | High |

---

## Example Integration

Here's how to add timing to your existing code:

```python
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from examples.timing_utils import InferenceTimer, measure_rtf
import wave

# Load model
pipeline = ASRInferencePipeline(model_card="omniASR_CTC_1B")

# Process audio with timing
audio_file = "recordings/call.wav"

# Get audio duration
with wave.open(audio_file, 'rb') as wf:
    audio_duration = wf.getnframes() / float(wf.getframerate())

# Transcribe with timing
with InferenceTimer("Transcription") as timer:
    result = pipeline.transcribe([audio_file], lang=["fas_Arab"], batch_size=1)

# Calculate RTF
rtf_info = measure_rtf(audio_duration, timer.elapsed)

# Display results
print(f"Audio: {audio_duration:.2f}s")
print(f"Processing: {timer.elapsed:.2f}s")
print(f"RTF: {rtf_info['rtf']:.2f}x - {rtf_info['speed']}")
print(f"Transcription: {result[0]}")
```

---

## Summary

✅ **test_omnilingual.py** shows timing automatically  
✅ **measure_inference_time.py** for detailed benchmarks  
✅ **timing_utils.py** for your own code  
✅ **RTF** is the key metric (< 1.0 is good)  

**Start here:**
```powershell
.\docker-run.ps1 -TestASR
```


