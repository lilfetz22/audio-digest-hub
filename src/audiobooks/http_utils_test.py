"""Tests for http_utils.py — the shared retrying GET used by date_range.py
and generate_audiobook.py.
"""

import pytest
import requests

import http_utils


def test_returns_response_on_first_success(requests_mock):
    requests_mock.get("https://fake-api.com/thing", json={"ok": True})

    response = http_utils.requests_get_with_retry(
        "https://fake-api.com/thing", headers={}
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_retries_then_succeeds(requests_mock, mocker):
    mock_sleep = mocker.patch.object(http_utils.time, "sleep")
    requests_mock.get(
        "https://fake-api.com/thing",
        [
            {"exc": requests.exceptions.ConnectionError("fail 1")},
            {"exc": requests.exceptions.Timeout("fail 2")},
            {"json": {"ok": True}, "status_code": 200},
        ],
    )

    response = http_utils.requests_get_with_retry(
        "https://fake-api.com/thing", headers={}, max_retries=3, backoff_base=2
    )

    assert response.json() == {"ok": True}
    assert mock_sleep.call_args_list == [mocker.call(1), mocker.call(2)]


def test_reraises_after_the_last_attempt(requests_mock, mocker):
    mocker.patch.object(http_utils.time, "sleep")
    requests_mock.get(
        "https://fake-api.com/thing",
        exc=requests.exceptions.ConnectionError("still down"),
    )

    with pytest.raises(requests.exceptions.ConnectionError):
        http_utils.requests_get_with_retry(
            "https://fake-api.com/thing", headers={}, max_retries=2
        )


def test_non_transient_error_is_not_retried(requests_mock, mocker):
    mock_sleep = mocker.patch.object(http_utils.time, "sleep")
    requests_mock.get(
        "https://fake-api.com/thing",
        exc=requests.exceptions.HTTPError("400 client error"),
    )

    with pytest.raises(requests.exceptions.HTTPError):
        http_utils.requests_get_with_retry(
            "https://fake-api.com/thing", headers={}, max_retries=3
        )

    mock_sleep.assert_not_called()


def test_max_retries_below_one_raises_immediately():
    with pytest.raises(ValueError, match="max_retries must be >= 1"):
        http_utils.requests_get_with_retry(
            "https://fake-api.com/thing", headers={}, max_retries=0
        )
