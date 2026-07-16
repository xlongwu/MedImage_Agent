from __future__ import annotations

from src.backend.app.runtime.pipeline_executor import _elapsed_seconds


def test_elapsed_seconds_supports_runtime_iso_timestamps() -> None:
    assert (
        _elapsed_seconds(
            "2026-07-16T00:46:18.784696+00:00",
            "2026-07-16T00:47:24.467435+00:00",
        )
        == 65.682739
    )


def test_elapsed_seconds_fails_closed_for_invalid_timestamps() -> None:
    assert _elapsed_seconds("invalid", "also-invalid") == 0.0
