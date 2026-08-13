"""Tests for _parse_retry_after and the locked-in model cache in gemini_client."""

import threading
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

import gemini_client
from gemini_client import GeminiClientWithFallback, _parse_retry_after


def test_delta_seconds():
    assert _parse_retry_after("12") == 12.0


def test_delta_seconds_zero():
    assert _parse_retry_after("0") == 0.0


def test_negative_delta_seconds_clamped_to_zero():
    assert _parse_retry_after("-1") == 0.0
    assert _parse_retry_after("-30") == 0.0


def test_http_date_in_future():
    future = datetime.now(timezone.utc) + timedelta(seconds=30)
    seconds = _parse_retry_after(format_datetime(future, usegmt=True))
    assert 25 <= seconds <= 30


def test_http_date_in_past_clamped_to_zero():
    past = datetime.now(timezone.utc) - timedelta(seconds=30)
    assert _parse_retry_after(format_datetime(past, usegmt=True)) == 0.0


def test_empty_value_returns_none():
    assert _parse_retry_after("") is None


def test_whitespace_value_returns_none():
    assert _parse_retry_after("   ") is None


def test_unparseable_value_returns_none():
    assert _parse_retry_after("not-a-valid-value") is None


class _FakeResponse:
    def __init__(self, status_code, headers=None, text=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._text = text

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._text}}]}


@pytest.mark.parametrize(
    "header,expected",
    [("30", 30.0), ("999", 60.0), ("-1", 0.0), ("junk", 2.5)],
)
def test_openrouter_retry_after_drives_sleep(monkeypatch, header, expected):
    """The header must reach time.sleep() clamped into [0, max_delay]."""
    slept = []
    monkeypatch.setattr(gemini_client.time, "sleep", slept.append)
    # Pin jitter to its lower bound so the delay is deterministic.
    monkeypatch.setattr(gemini_client.random, "uniform", lambda a, b: a)

    responses = [
        _FakeResponse(429, {"Retry-After": header}),
        _FakeResponse(200, {}, text="ok"),
    ]
    client = GeminiClientWithFallback(
        api_key="",
        openrouter_api_key="k",
        openrouter_model="m",
        openrouter_only=True,
    )
    monkeypatch.setattr(
        client._http_client, "post", lambda *a, **k: responses.pop(0)
    )

    assert client.generate("hi") == "ok"
    assert slept == [expected]
    assert all(s >= 0 for s in slept)


def _make_client(monkeypatch, constructed):
    """Build a client whose genai.Client construction is recorded, not real."""

    class _FakeGenaiClient:
        def __init__(self, api_key):
            constructed.append(api_key)

    monkeypatch.setattr(gemini_client.genai, "Client", _FakeGenaiClient)
    return GeminiClientWithFallback(api_key="primary", model_name="m1")


def test_successful_generate_locks_in_pair(monkeypatch):
    constructed = []
    client = _make_client(monkeypatch, constructed)
    monkeypatch.setattr(
        GeminiClientWithFallback, "_try_model", lambda self, c, m, s, u: "ok"
    )

    assert client.generate("hi") == "ok"
    assert client._resolved is not None
    assert client._resolved[1] == "m1"


def test_invalidate_resolved_keeps_newer_pair(monkeypatch):
    client = _make_client(monkeypatch, [])
    stale = (object(), "old")
    fresh = (object(), "new")
    client._resolved = fresh

    client._invalidate_resolved(stale)
    assert client._resolved is fresh

    client._invalidate_resolved(fresh)
    assert client._resolved is None


def test_concurrent_generate_walks_chain_once(monkeypatch):
    constructed = []
    client = _make_client(monkeypatch, constructed)
    monkeypatch.setattr(
        GeminiClientWithFallback, "_try_model", lambda self, c, m, s, u: "ok"
    )

    start = threading.Barrier(8)
    results = []

    def worker():
        start.wait()
        results.append(client.generate("hi"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == ["ok"] * 8
    assert len(constructed) == 1


def test_concurrent_generate_never_sees_torn_resolution(monkeypatch):
    client = _make_client(monkeypatch, [])
    state = {"fail_next": True}
    lock = threading.Lock()

    def fake_try_model(self, tier_client, model, system_prompt, user_prompt):
        assert tier_client is not None, "torn resolution: client was None"
        with lock:
            if state["fail_next"] and self._resolved is not None:
                state["fail_next"] = False
                raise ConnectionError("flaky")
        return "ok"

    monkeypatch.setattr(GeminiClientWithFallback, "_try_model", fake_try_model)

    start = threading.Barrier(8)
    results = []

    def worker():
        start.wait()
        results.append(client.generate("hi"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == ["ok"] * 8
