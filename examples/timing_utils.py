"""
Timing utilities for measuring inference performance.

Usage:
    from timing_utils import time_inference, InferenceTimer
    
    # Method 1: Decorator
    @time_inference
    def my_transcription():
        return pipeline.transcribe(audio)
    
    # Method 2: Context manager
    with InferenceTimer("Transcription"):
        result = pipeline.transcribe(audio)
    
    # Method 3: Manual
    timer = InferenceTimer()
    timer.start()
    result = pipeline.transcribe(audio)
    timer.stop()
    print(f"Time: {timer.elapsed:.2f}s")
"""

import time
from functools import wraps
from typing import Any, Callable, Optional


class InferenceTimer:
    """Context manager and manual timer for measuring inference time."""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: Optional[float] = None
    
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        return self
    
    def stop(self):
        """Stop the timer and calculate elapsed time."""
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        return self.elapsed
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, *args):
        """Context manager exit."""
        self.stop()
        print(f"[TIMER] {self.name}: {self.elapsed:.3f} seconds")
    
    def __str__(self):
        if self.elapsed is not None:
            return f"{self.name}: {self.elapsed:.3f}s"
        return f"{self.name}: not measured"


def time_inference(func: Callable) -> Callable:
    """
    Decorator to measure and print function execution time.
    
    Usage:
        @time_inference
        def transcribe_audio(audio_path):
            return pipeline.transcribe(audio_path)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        print(f"[TIMER] {func.__name__}: {elapsed:.3f} seconds")
        return result
    return wrapper


def measure_rtf(audio_duration_sec: float, inference_time_sec: float) -> dict:
    """
    Calculate Real-Time Factor (RTF) and interpretation.
    
    Args:
        audio_duration_sec: Duration of audio in seconds
        inference_time_sec: Time taken to process in seconds
    
    Returns:
        dict with RTF and interpretation
    """
    rtf = inference_time_sec / audio_duration_sec
    
    if rtf < 0.5:
        speed = "very fast"
        suitable = "excellent for real-time and batch"
    elif rtf < 1.0:
        speed = "fast"
        suitable = "good for real-time processing"
    elif rtf < 2.0:
        speed = "moderate"
        suitable = "marginal for real-time, good for batch"
    else:
        speed = "slow"
        suitable = "batch processing only"
    
    return {
        'rtf': rtf,
        'speed': speed,
        'suitable_for': suitable,
        'interpretation': f"{rtf:.2f}x (takes {rtf:.2f}s to process 1s of audio)",
    }


# Example usage
if __name__ == "__main__":
    # Example 1: Context manager
    print("Example 1: Context manager")
    with InferenceTimer("Simulated transcription"):
        time.sleep(0.5)  # Simulate work
    
    # Example 2: Decorator
    print("\nExample 2: Decorator")
    @time_inference
    def simulate_work():
        time.sleep(0.3)
        return "done"
    
    result = simulate_work()
    
    # Example 3: Manual timing
    print("\nExample 3: Manual timing")
    timer = InferenceTimer("Manual operation")
    timer.start()
    time.sleep(0.2)
    elapsed = timer.stop()
    print(f"Elapsed: {elapsed:.3f}s")
    
    # Example 4: RTF calculation
    print("\nExample 4: RTF calculation")
    audio_duration = 10.0  # 10 seconds of audio
    inference_time = 2.5   # took 2.5 seconds to process
    rtf_info = measure_rtf(audio_duration, inference_time)
    print(f"RTF: {rtf_info['rtf']:.2f}x")
    print(f"Speed: {rtf_info['speed']}")
    print(f"Suitable for: {rtf_info['suitable_for']}")

