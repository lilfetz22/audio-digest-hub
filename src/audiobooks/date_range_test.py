"""Tests for date_range.py — the pipeline's single source of truth for which
days to process, shared by generate_audiobook.py, run_research_pipeline.py
and run_wiki_ingestion.py.
"""

import datetime
import logging

import pytest
import requests

import date_range


def _titles(*dates):
    return [{"title": f"Daily Digest for {d}"} for d in dates]


# --- find_last_upload_date ---------------------------------------------------


def test_find_last_upload_date_returns_max_date(requests_mock):
    requests_mock.get(
        "https://fake-api.com/audiobooks",
        json=_titles("2026-08-08", "2026-08-10", "2026-08-09"),
    )

    assert date_range.find_last_upload_date(
        "https://fake-api.com", "fake_key"
    ) == datetime.date(2026, 8, 10)


def test_find_last_upload_date_skips_untitled_and_unparseable(requests_mock):
    requests_mock.get(
        "https://fake-api.com/audiobooks",
        json=[
            {"title": "No date here"},
            {},
            {"title": "Daily Digest for 2026-13-45"},  # matches regex, invalid date
            {"title": "Daily Digest for 2026-08-09"},
        ],
    )

    assert date_range.find_last_upload_date(
        "https://fake-api.com", "fake_key"
    ) == datetime.date(2026, 8, 9)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status_code": 500},
        {"json": []},
        {"json": [{"title": "No dates at all"}]},
        {"text": "not json"},
    ],
)
def test_find_last_upload_date_returns_none_on_unusable_response(requests_mock, kwargs):
    requests_mock.get("https://fake-api.com/audiobooks", **kwargs)

    assert date_range.find_last_upload_date("https://fake-api.com", "fake_key") is None


def test_find_last_upload_date_swallows_network_error(requests_mock, caplog):
    requests_mock.get(
        "https://fake-api.com/audiobooks",
        exc=requests.exceptions.ConnectionError("fail"),
    )

    with caplog.at_level(logging.ERROR):
        result = date_range.find_last_upload_date("https://fake-api.com", "fake_key")

    assert result is None
    assert "Error fetching audiobooks to find last upload date" in caplog.text


# --- resolve_default_dates ---------------------------------------------------


def test_resolve_backfills_every_missed_day(mocker):
    """The reported bug: last upload 2026-08-10, running on 2026-08-14."""
    mocker.patch.object(
        date_range, "find_last_upload_date", return_value=datetime.date(2026, 8, 10)
    )

    dates = date_range.resolve_default_dates(
        "https://api", "key", datetime.date(2026, 8, 13)
    )

    assert dates == [
        datetime.date(2026, 8, 11),
        datetime.date(2026, 8, 12),
        datetime.date(2026, 8, 13),
    ]


def test_resolve_falls_back_to_end_date_without_watermark(mocker):
    mocker.patch.object(date_range, "find_last_upload_date", return_value=None)

    assert date_range.resolve_default_dates(
        "https://api", "key", datetime.date(2026, 8, 13)
    ) == [datetime.date(2026, 8, 13)]


def test_resolve_includes_end_date_when_watermark_is_the_day_before(mocker):
    mocker.patch.object(
        date_range, "find_last_upload_date", return_value=datetime.date(2026, 8, 12)
    )

    assert date_range.resolve_default_dates(
        "https://api", "key", datetime.date(2026, 8, 13)
    ) == [datetime.date(2026, 8, 13)]


@pytest.mark.parametrize("last_upload_day", [13, 14])
def test_resolve_returns_empty_when_caught_up(mocker, last_upload_day):
    """Watermark already at or past end_date: nothing new to do, so the
    orchestrator can skip the run entirely."""
    mocker.patch.object(
        date_range,
        "find_last_upload_date",
        return_value=datetime.date(2026, 8, last_upload_day),
    )

    assert (
        date_range.resolve_default_dates(
            "https://api", "key", datetime.date(2026, 8, 13)
        )
        == []
    )


def test_resolve_clamps_to_max_backfill_days(mocker, caplog):
    mocker.patch.object(
        date_range, "find_last_upload_date", return_value=datetime.date(2026, 1, 1)
    )

    with caplog.at_level(logging.WARNING):
        dates = date_range.resolve_default_dates(
            "https://api", "key", datetime.date(2026, 8, 13), max_backfill_days=3
        )

    assert dates == [
        datetime.date(2026, 8, 11),
        datetime.date(2026, 8, 12),
        datetime.date(2026, 8, 13),
    ]
    assert "would exceed the 3-day limit" in caplog.text


def test_resolve_max_backfill_days_zero_disables_the_cap(mocker):
    mocker.patch.object(
        date_range, "find_last_upload_date", return_value=datetime.date(2026, 8, 1)
    )

    dates = date_range.resolve_default_dates(
        "https://api", "key", datetime.date(2026, 8, 13), max_backfill_days=0
    )

    assert dates[0] == datetime.date(2026, 8, 2)
    assert dates[-1] == datetime.date(2026, 8, 13)
    assert len(dates) == 12


# --- resolve_transcript_dates ------------------------------------------------


def test_resolve_transcript_dates_finds_and_sorts_digests(tmp_path):
    for name in (
        "research_digest_2026-08-13.txt",
        "research_digest_2026-08-11.txt",
        "research_digest_2026-08-12.txt",
        "newsletter_2026-08-12.txt",  # not a research digest
        "research_digest_notadate.txt",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")

    dates = date_range.resolve_transcript_dates(
        str(tmp_path), datetime.date(2026, 8, 13)
    )

    assert dates == [
        datetime.date(2026, 8, 11),
        datetime.date(2026, 8, 12),
        datetime.date(2026, 8, 13),
    ]


def test_resolve_transcript_dates_drops_digests_below_the_floor(tmp_path):
    for name in (
        "research_digest_2026-01-01.txt",
        "research_digest_2026-08-12.txt",
        "research_digest_2026-08-13.txt",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")

    dates = date_range.resolve_transcript_dates(
        str(tmp_path), datetime.date(2026, 8, 13), max_backfill_days=2
    )

    assert dates == [datetime.date(2026, 8, 12), datetime.date(2026, 8, 13)]


def test_resolve_transcript_dates_keeps_digests_past_end_date(tmp_path):
    """A digest produced by a manual --date run for a later day is still
    worth archiving, so only the floor is enforced."""
    (tmp_path / "research_digest_2026-08-20.txt").write_text("x", encoding="utf-8")

    assert date_range.resolve_transcript_dates(
        str(tmp_path), datetime.date(2026, 8, 13)
    ) == [datetime.date(2026, 8, 20)]


def test_resolve_transcript_dates_handles_missing_directory(tmp_path):
    assert (
        date_range.resolve_transcript_dates(
            str(tmp_path / "nope"), datetime.date(2026, 8, 13)
        )
        == []
    )


# --- CLI (what pipeline.py shells out to) ------------------------------------


def _write_webapp_config(path):
    path.write_text(
        "[WebApp]\nAPI_URL = https://fake-api.com\nAPI_KEY = fake_key\n",
        encoding="utf-8",
    )


def test_cli_prints_start_and_end(tmp_path, capsys, mocker):
    config = tmp_path / "config.ini"
    _write_webapp_config(config)
    mocker.patch.object(
        date_range,
        "resolve_default_dates",
        return_value=[datetime.date(2026, 8, 11), datetime.date(2026, 8, 13)],
    )

    assert date_range.main(["--config", str(config)]) == 0
    assert capsys.readouterr().out.strip() == "2026-08-11 2026-08-13"


def test_cli_prints_nothing_when_caught_up(tmp_path, capsys, mocker):
    config = tmp_path / "config.ini"
    _write_webapp_config(config)
    mocker.patch.object(date_range, "resolve_default_dates", return_value=[])

    assert date_range.main(["--config", str(config)]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_cli_exits_nonzero_when_config_is_missing(tmp_path, capsys):
    assert date_range.main(["--config", str(tmp_path / "nope.ini")]) == 1
    assert capsys.readouterr().out.strip() == ""


def test_cli_exits_nonzero_when_webapp_section_is_absent(tmp_path, capsys):
    config = tmp_path / "config.ini"
    config.write_text("[Gmail]\nTOKEN_FILE = token.json\n", encoding="utf-8")

    assert date_range.main(["--config", str(config)]) == 1
    assert capsys.readouterr().out.strip() == ""


def test_cli_passes_max_backfill_days_through(tmp_path, mocker):
    config = tmp_path / "config.ini"
    _write_webapp_config(config)
    mock_resolve = mocker.patch.object(
        date_range, "resolve_default_dates", return_value=[]
    )

    date_range.main(["--config", str(config), "--max-backfill-days", "5"])

    assert mock_resolve.call_args.kwargs["max_backfill_days"] == 5
