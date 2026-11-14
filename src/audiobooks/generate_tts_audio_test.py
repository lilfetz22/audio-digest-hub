"""Tests for the progress_callback hook in generate_tts_audio.

Kokoro and ffmpeg are stubbed, so these run without the model or a
real encode. Only the single-process path is exercised; the worker-pool
path spawns processes and is covered by the workflow run instead.
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
