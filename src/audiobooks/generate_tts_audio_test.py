"""Tests for the progress_callback hook in generate_tts_audio.

Kokoro and ffmpeg are stubbed, so these run without the model or a
real encode. The worker-pool path is tested with an inline stand-in for the
process pool, so no real processes are spawned.
"""
import numpy as np
import pytest

import generate_tts_audio as tts


@pytest.fixture
def stub_tts(monkeypatch):
    """Replace the model and encoder with no-op stand-ins."""
    monkeypatch.setattr(tts, "_load_pipeline", lambda device: None)
    monkeypatch.setattr(
        tts,
        "_synthesize_chunk",
        lambda pipeline, text, voice, speed: np.zeros(240, dtype=np.float32),
    )

    def fake_encode(wav_path, mp3_path, bitrate):
        mp3_path.write_bytes(b"ID3")

    monkeypatch.setattr(tts, "_encode_mp3", fake_encode)


# "Q1: ..." is a question line, so a pause marker follows it:
# chunks are [question, PAUSE, answer] -> 3 total.
TEXT = "Q1: Is it fine?\nAnswer here."


def test_progress_reports_every_chunk_including_pauses(stub_tts, tmp_path):
    calls = []

    tts.generate_audio_from_text(
        TEXT,
        tmp_path / "out.mp3",
        max_workers=1,
        progress_callback=lambda done, total: calls.append((done, total)),
    )

    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_progress_callback_error_does_not_abort_synthesis(stub_tts, tmp_path):
    def broken(done, total):
        raise ConnectionError("status endpoint unreachable")

    out = tts.generate_audio_from_text(
        TEXT,
        tmp_path / "out.mp3",
        max_workers=1,
        progress_callback=broken,
    )

    assert out.exists()


def test_no_callback_is_the_default(stub_tts, tmp_path):
    out = tts.generate_audio_from_text(TEXT, tmp_path / "out.mp3", max_workers=1)

    assert out.exists()


class _InlineExecutor:
    """Stand-in for ProcessPoolExecutor that runs each task immediately."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, *args):
        from concurrent.futures import Future

        future = Future()
        future.set_result(fn(*args))
        return future


def test_worker_pool_progress_counts_prefilled_pauses_then_each_future(
    stub_tts, monkeypatch, tmp_path
):
    worked = []

    def fake_worker(index, chunk, voice, speed):
        worked.append(index)
        return index, np.zeros(240, dtype=np.float32), None

    monkeypatch.setattr(tts, "ProcessPoolExecutor", _InlineExecutor)
    monkeypatch.setattr(tts, "_worker_synthesize", fake_worker)
    calls = []

    out = tts.generate_audio_from_text(
        TEXT,
        tmp_path / "out.mp3",
        max_workers=2,
        progress_callback=lambda done, total: calls.append((done, total)),
    )

    assert out.exists()
    # The pause chunk (index 1) is filled in the parent, not sent to a worker.
    assert worked == [0, 2]
    # One report for the pre-filled pause, then one per finished future.
    assert calls == [(1, 3), (2, 3), (3, 3)]
