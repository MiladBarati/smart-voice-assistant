"""Diagnostic logging helpers for Silero VAD.

This module provides structured logging functions to replace direct print()
statements, making the code cleaner and easier to maintain.
"""

from __future__ import annotations

from typing import Any


def log_model_loading_strategy(strategy_num: int, total: int, name: str) -> None:
    """Log that a model loading strategy is being attempted."""
    print(f"***VAD: Trying strategy {strategy_num}/{total}: {name}")


def log_model_loaded(strategy_name: str, details: str = "") -> None:
    """Log successful model loading."""
    msg = f"***VAD: model loaded successfully using {strategy_name}"
    if details:
        msg += f" ({details})"
    print(msg)


def log_model_loading_error(strategy_num: int, error: str) -> None:
    """Log a model loading strategy failure."""
    print(f"***VAD: Strategy {strategy_num} failed: {error}")


def log_reusing_cached_model(model_type: str) -> None:
    """Log that a cached model is being reused."""
    print(f"***VAD: reusing preloaded {model_type} model from cache")


def log_cache_cleared(reason: str) -> None:
    """Log that the model cache was cleared."""
    print(f"***VAD: proactively clearing cached model {reason}")


def log_onnx_providers(providers: list[str]) -> None:
    """Log ONNX Runtime execution providers being used."""
    print(f"***VAD: Loading ONNX model with providers: {providers}")


def log_onnx_model_info(session: Any) -> None:
    """Log ONNX model input/output specifications."""
    print("***VAD: ONNX model inputs:")
    for inp in session.get_inputs():
        print(f"  - {inp.name}: shape={inp.shape}, type={inp.type}")
    print("***VAD: ONNX model outputs:")
    for out in session.get_outputs():
        print(f"  - {out.name}: shape={out.shape}, type={out.type}")


def log_onnx_states_initialized(state_type: str, shape: tuple) -> None:
    """Log ONNX hidden state initialization."""
    print(f"***VAD: Initialized ONNX {state_type} states with shape {shape}")


def log_onnx_unknown_state_format(input_names: list[str]) -> None:
    """Log warning about unknown ONNX state input format."""
    print(f"***VAD: Warning - unknown state input names: {input_names}")


def log_wav_file_opened(
    n_channels: int, sampwidth: int, framerate: int, n_frames: int
) -> None:
    """Log WAV file information on first read."""
    print(
        f"***VAD: WAV file opened - {n_channels}ch, "
        f"{sampwidth}byte/sample, {framerate}Hz, {n_frames} frames"
    )


def log_wav_file_parsed_manually(
    n_channels: int, bits_per_sample: int, framerate: int
) -> None:
    """Log manually parsed WAV file information."""
    print(
        f"***VAD: WAV file parsed manually - {n_channels}ch, "
        f"{bits_per_sample}bit/sample, {framerate}Hz"
    )


def log_waiting_for_wav_file(size: int | None = None) -> None:
    """Log that we're waiting for WAV file to be ready."""
    if size is not None:
        print(f"***VAD: waiting for WAV file to be ready (size={size} bytes)")
    else:
        print("***VAD: waiting for WAV file to be ready")


def log_waiting_for_new_audio(last_idx: int, total: int) -> None:
    """Log that we're waiting for new audio data."""
    print(f"***VAD: waiting for new audio (last_idx={last_idx}, total={total})")


def log_wav_read_error(message: str) -> None:
    """Log WAV file read error."""
    print(f"***VAD: WAV read error - {message}")


def log_manual_read_debug(
    file_size: int,
    data_offset: int,
    current_pos: int,
    available: int,
    bytes_per_frame: int,
    last_idx: int,
) -> None:
    """Log debug information for manual WAV reading."""
    print(
        f"***VAD: manual read - file_size={file_size}, "
        f"data_offset={data_offset}, "
        f"current_pos={current_pos}, "
        f"available={available}, "
        f"bytes_per_frame={bytes_per_frame}, "
        f"last_idx={last_idx}"
    )


def log_manual_read_waiting() -> None:
    """Log that we're waiting for new audio during manual read."""
    print("***VAD: waiting for new audio (manual read)")


def log_manual_read_error(error: str) -> None:
    """Log error during manual WAV reading."""
    print(f"***VAD: manual read error: {error}")


def log_audio_read(sample_count: int, sample_rate: int) -> None:
    """Log that audio samples were read."""
    print(f"***VAD: read {sample_count} samples at {sample_rate} Hz")


def log_unsupported_sample_rate(sample_rate: int, reason: str = "") -> None:
    """Log that an unsupported sample rate was encountered."""
    msg = f"***VAD: unsupported sample rate {sample_rate}Hz (must be 8000 or 16000)"
    if reason:
        msg += f" - {reason}"
    print(msg)


def log_cannot_resample(from_rate: int, reason: str) -> None:
    """Log that resampling cannot be performed."""
    print(f"***VAD: cannot resample from {from_rate}Hz {reason}")


def log_waveform_too_small(actual: int, required: int, sample_rate: int) -> None:
    """Log that waveform is too small for processing."""
    print(
        f"***VAD: waveform too small ({actual} samples, "
        f"need {required} for {sample_rate}Hz)"
    )


def log_speech_detected(prob: float, time: float, sample: int) -> None:
    """Log that speech was detected."""
    print(
        f"***VAD: speech detected (prob={prob:.3f}, "
        f"time={time:.3f}, sample={sample})"
    )


def log_processing_stats(
    frames_processed: int, total_frames: int, max_prob: float, threshold: float
) -> None:
    """Log VAD processing statistics."""
    print(
        f"***VAD: processed {frames_processed}/{total_frames} "
        f"frames, max_prob={max_prob:.3f} "
        f"(threshold={threshold:.3f})"
    )


def log_no_frames_processed(total_frames: int) -> None:
    """Log that no frames were processed despite availability."""
    print(
        f"***VAD: {total_frames} frames available but none "
        "processed (check model errors)"
    )


def log_model_call_error(error: str) -> None:
    """Log error during model inference."""
    print(f"***VAD: model call error: {error}")


def log_chunk_split_due_to_max_duration(max_duration: float) -> None:
    """Log that a chunk was split due to max duration."""
    print(f"***VAD: chunk split due to max duration ({max_duration}s)")
