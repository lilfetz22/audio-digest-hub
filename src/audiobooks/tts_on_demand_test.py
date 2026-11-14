"""Tests for the pasted-text TTS runner's pure helpers and status reporting.

The HTTP layer is replaced with a recorder, so no API is called.
"""
import pytest
import requests

import tts_on_demand as runner


class RecordingPatch:
    """Stands in for requests.patch and records each body sent."""

    def __init__(self, fail_times=0):
        self.bodies = []
        self.fail_times = fail_times

    def __call__(self, url, headers=None, json=None, timeout=None):
        self.bodies.append(json)
        if self.fail_times > 0:
            self.fail_times -= 1
            raise requests.ConnectionError("boom")

        class _Ok:
            def raise_for_status(self):
                return None

        return _Ok()


def test_map_synthesis_percent_scales_into_first_ninety_percent():
    assert runner.map_synthesis_percent(0, 10) == 0
    assert runner.map_synthesis_percent(5, 10) == 45
    assert runner.map_synthesis_percent(10, 10) == 90


def test_map_synthesis_percent_handles_empty_total():
    assert runner.map_synthesis_percent(0, 0) == 0


def test_fallback_title_uses_first_line():
    assert runner.fallback_title("Short line\nSecond line") == "Short line"


def test_fallback_title_truncates_long_first_line():
    title = runner.fallback_title("word " * 40)

    assert title.endswith("...")
    assert len(title) <= runner.FALLBACK_TITLE_CHARS + 3


def test_fallback_title_for_blank_text():
    assert runner.fallback_title("   ") == "Pasted text"


def test_progress_never_moves_backwards(monkeypatch):
    recorder = RecordingPatch()
    monkeypatch.setattr(runner.requests, "patch", recorder)
    reporter = runner.ProgressReporter("https://api", "key", "job-1")

    reporter.update("synthesizing", 40)
    reporter.update("synthesizing", 10)  # e.g. after a worker-pool restart

    assert [b["percent"] for b in recorder.bodies] == [40, 40]


def test_intermediate_update_failure_is_swallowed(monkeypatch):
    recorder = RecordingPatch(fail_times=1)
    monkeypatch.setattr(runner.requests, "patch", recorder)
    reporter = runner.ProgressReporter("https://api", "key", "job-1")

    reporter.update("synthesizing", 20)  # must not raise

    assert len(recorder.bodies) == 1


def test_terminal_update_is_retried(monkeypatch):
    recorder = RecordingPatch(fail_times=2)
    monkeypatch.setattr(runner.requests, "patch", recorder)
    reporter = runner.ProgressReporter("https://api", "key", "job-1")

    reporter.finish("done", 100)

    assert recorder.bodies[-1] == {"status": "done", "percent": 100}
    assert len(recorder.bodies) == 3


def test_terminal_update_raises_after_retries_exhausted(monkeypatch):
    recorder = RecordingPatch(fail_times=10)
    monkeypatch.setattr(runner.requests, "patch", recorder)
    reporter = runner.ProgressReporter("https://api", "key", "job-1")

    with pytest.raises(RuntimeError):
        reporter.finish("failed", error="x")


def test_error_text_is_truncated(monkeypatch):
    recorder = RecordingPatch()
    monkeypatch.setattr(runner.requests, "patch", recorder)
    reporter = runner.ProgressReporter("https://api", "key", "job-1")

    reporter.finish("failed", error="e" * 900)

    assert len(recorder.bodies[-1]["error"]) == 500
