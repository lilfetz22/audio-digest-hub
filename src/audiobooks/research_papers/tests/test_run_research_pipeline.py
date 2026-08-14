import configparser
import datetime
from pathlib import Path

import run_research_pipeline as rrp


def _write_config(path: Path, *, credentials="credentials.json", token="token.json"):
    config = configparser.ConfigParser()
    config["WebApp"] = {
        "API_URL": "https://fake-api.com",
        "API_KEY": "fake-api-key",
    }
    config["Gmail"] = {
        "CREDENTIALS_FILE": credentials,
        "TOKEN_FILE": token,
    }
    config["Gemini"] = {
        "API_KEY": "fake-gemini-key",
        "GENERATION_MODEL": "fake-model",
    }
    config["ResearchPapers"] = {
        "ARXIV_SENDERS": "no-reply@arxiv.org",
        "HUGGINGFACE_SENDERS": "daily@huggingface.co",
    }
    with path.open("w", encoding="utf-8") as fh:
        config.write(fh)


def test_load_config_resolves_paths_relative_to_config_file(tmp_path):
    config_path = tmp_path / "config.ini"
    _write_config(config_path)

    config = rrp.load_config(str(config_path))

    assert config["credentials_file"] == str(tmp_path / "credentials.json")
    assert config["token_file"] == str(tmp_path / "token.json")


def test_load_config_preserves_absolute_paths(tmp_path):
    config_path = tmp_path / "config.ini"
    absolute_credentials = tmp_path / "nested" / "credentials.json"
    absolute_token = tmp_path / "nested" / "token.json"
    _write_config(
        config_path,
        credentials=str(absolute_credentials),
        token=str(absolute_token),
    )

    config = rrp.load_config(str(config_path))

    assert config["credentials_file"] == str(absolute_credentials)
    assert config["token_file"] == str(absolute_token)


# --- Date selection in main() -------------------------------------------------

_FAKE_CONFIG = {
    "api_url": "https://fake-api.com",
    "api_key": "fake-api-key",
    "credentials_file": "credentials.json",
    "token_file": "token.json",
    "gemini_api_key": "fake-gemini-key",
    "generation_model": "fake-model",
    "backup_api_key": None,
    "scoring_model_name": "fake-scoring-model",
    "arxiv_senders": ["no-reply@arxiv.org"],
    "huggingface_senders": ["daily@huggingface.co"],
    "top_n_threshold": 10,
    "top_n_deep_dive": 25,
    "arxiv_delay_seconds": 3,
    "openrouter_api_key": None,
    "openrouter_model": None,
}


def _patch_main(mocker, monkeypatch, argv):
    """Stub out everything main() does apart from choosing dates, and return
    the mock pipeline whose run() calls record the dates processed."""
    monkeypatch.setattr(rrp.sys, "argv", argv)
    mocker.patch.object(rrp, "setup_logging")
    mocker.patch.object(rrp, "load_config", return_value=dict(_FAKE_CONFIG))
    mocker.patch.object(rrp, "authenticate_gmail")
    mocker.patch.object(rrp, "build")
    for name in (
        "ArxivHFEmailParser",
        "PaperContentDownloader",
        "EmbeddingPaperScorer",
        "GeminiTranscriptGenerator",
        "PreferenceProfileManager",
        "FeedbackClient",
    ):
        mocker.patch.object(rrp, name)
    return mocker.patch.object(rrp, "ResearchPaperPipeline").return_value


def _processed_dates(mock_pipeline):
    return [call.args[0] for call in mock_pipeline.run.call_args_list]


def test_main_backfills_from_last_upload_date(mocker, monkeypatch):
    """No date flags: process every day since the last audiobook upload,
    the same window generate_audiobook.py uses."""
    mock_pipeline = _patch_main(mocker, monkeypatch, ["script"])
    mocker.patch.object(
        rrp, "resolve_default_dates",
        return_value=[datetime.date(2026, 8, 11), datetime.date(2026, 8, 12)],
    )

    rrp.main()

    assert _processed_dates(mock_pipeline) == ["2026-08-11", "2026-08-12"]


def test_main_passes_end_date_and_cap_to_resolver(mocker, monkeypatch):
    mock_pipeline = _patch_main(mocker, monkeypatch, ["script", "--max-backfill-days", "5"])
    mock_resolve = mocker.patch.object(
        rrp, "resolve_default_dates", return_value=[datetime.date(2026, 8, 13)]
    )

    rrp.main()

    args, kwargs = mock_resolve.call_args
    assert args[0] == "https://fake-api.com"
    assert args[1] == "fake-api-key"
    assert args[2] == datetime.date.today() - datetime.timedelta(days=1)
    assert kwargs["max_backfill_days"] == 5
    assert _processed_dates(mock_pipeline) == ["2026-08-13"]


def test_main_explicit_date_skips_backfill_lookup(mocker, monkeypatch):
    mock_pipeline = _patch_main(mocker, monkeypatch, ["script", "--date", "2026-08-01"])
    mock_resolve = mocker.patch.object(rrp, "resolve_default_dates")

    rrp.main()

    mock_resolve.assert_not_called()
    assert _processed_dates(mock_pipeline) == ["2026-08-01"]


def test_main_explicit_range_skips_backfill_lookup(mocker, monkeypatch):
    mock_pipeline = _patch_main(
        mocker,
        monkeypatch,
        ["script", "--start-date", "2026-08-01", "--end-date", "2026-08-03"],
    )
    mock_resolve = mocker.patch.object(rrp, "resolve_default_dates")

    rrp.main()

    mock_resolve.assert_not_called()
    assert _processed_dates(mock_pipeline) == ["2026-08-01", "2026-08-02", "2026-08-03"]


def test_main_exits_early_when_there_is_nothing_to_process(mocker, monkeypatch):
    """An empty range means the watermark is already current — don't bother
    authenticating Gmail or wiring up the pipeline."""
    mock_pipeline = _patch_main(mocker, monkeypatch, ["script"])
    mocker.patch.object(rrp, "resolve_default_dates", return_value=[])

    rrp.main()

    rrp.authenticate_gmail.assert_not_called()
    mock_pipeline.run.assert_not_called()


def test_main_continues_after_a_date_fails(mocker, monkeypatch):
    """A backfilled day that blows up must not stop the remaining days."""
    mock_pipeline = _patch_main(mocker, monkeypatch, ["script"])
    mocker.patch.object(
        rrp, "resolve_default_dates",
        return_value=[datetime.date(2026, 8, 11), datetime.date(2026, 8, 12)],
    )
    mock_pipeline.run.side_effect = [RuntimeError("boom"), None]

    rrp.main()  # must not raise

    assert _processed_dates(mock_pipeline) == ["2026-08-11", "2026-08-12"]
