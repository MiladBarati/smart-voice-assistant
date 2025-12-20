"""Smoke tests for omnilingual-asr.

Important: `omnilingual-asr` can depend on system libraries (e.g. `libsndfile` via
fairseq2n). In CI we want to **skip** these tests unless explicitly enabled.
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.integration
def test_omnilingual_asr_import_smoke() -> None:
    """Import omnilingual-asr without crashing the test suite."""
    if not os.getenv("TEST_ASR_OMNILINGUAL"):
        pytest.skip("Set TEST_ASR_OMNILINGUAL=1 to run omnilingual-asr smoke tests")

    try:
        import omnilingual_asr  # noqa: F401
        from omnilingual_asr.models.inference.pipeline import (  # noqa: F401
            ASRInferencePipeline,
        )
    except Exception as exc:  # noqa: BLE001 - native loader errors should skip in CI
        pytest.skip(f"omnilingual-asr not available in this environment: {exc}")

