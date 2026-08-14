"""Tests for run_wiki_ingestion.py — the standalone wiki-archiving CLI entry
point, deliberately decoupled from run_research_pipeline.py so this stage
can never block or take down audiobook generation.

Default behavior is the cheap, no-LLM verbatim archive
(WikiIngestionEngine.archive_raw_summary). The old full LLM classify+extract
pipeline (WikiIngestionEngine.ingest_transcript) is opt-in via --llm-wiki.
"""

import run_wiki_ingestion as rwi


_FAKE_CONFIG = {
    "gemini_api_key": "fake-gemini-key",
    "wiki_model": "fake-model",
    "wiki_backup_api_key": None,
    "openrouter_api_key": None,
    "openrouter_model": None,
    "wiki_auto_commit": False,
    "wiki_auto_push": False,
    "wiki_push_parent": False,
}


def _patch_common(mocker, monkeypatch, argv):
    monkeypatch.setattr(rwi.sys, "argv", argv)
    mocker.patch.object(rwi, "setup_logging")
    mocker.patch.object(rwi, "load_config", return_value=dict(_FAKE_CONFIG))
    mock_engine_cls = mocker.patch.object(rwi, "WikiIngestionEngine")
    mock_engine = mock_engine_cls.return_value
    mock_engine.archive_raw_summary.return_value = "fake/path.md"
    mock_engine.ingest_transcript.return_value = {
        "concepts_created": ["A"],
        "concepts_updated": [],
    }
    return mock_engine


def _fake_exists(done_exists: bool, transcript_exists: bool):
    """Build an os.path.exists stand-in keyed on path suffix, avoiding any
    dependency on the real filesystem or run_wiki_ingestion.py's own
    __file__-derived directory layout. Matches whichever "already done"
    marker is relevant for the mode under test (wiki/raw_summary/ by
    default, wiki/sources/ under --llm-wiki)."""

    def fake_exists(path):
        normalized = str(path).replace("\\", "/")
        if normalized.endswith("/wiki/.git"):
            # Simulate an initialised wiki submodule so the submodule guard
            # in main() doesn't short-circuit these tests.
            return True
        if "/wiki/sources/" in normalized or "/wiki/raw_summary/" in normalized:
            return done_exists
        if "/raw_content/" in normalized:
            return transcript_exists
        return False

    return fake_exists


# --- Default (no-LLM raw_summary archive) path ------------------------------


def test_default_skips_when_already_archived(mocker, monkeypatch):
    """A date already archived to wiki/raw_summary/ is skipped entirely."""
    mock_engine = _patch_common(mocker, monkeypatch, ["script", "--date", "2026-04-10"])
    mocker.patch.object(
        rwi.os.path, "exists", side_effect=_fake_exists(done_exists=True, transcript_exists=True)
    )

    rwi.main()

    mock_engine.archive_raw_summary.assert_not_called()
    mock_engine.ingest_transcript.assert_not_called()


def test_default_skips_when_no_transcript(mocker, monkeypatch):
    """A date with no research_digest transcript on disk is skipped."""
    mock_engine = _patch_common(mocker, monkeypatch, ["script", "--date", "2026-04-10"])
    mocker.patch.object(
        rwi.os.path, "exists", side_effect=_fake_exists(done_exists=False, transcript_exists=False)
    )

    rwi.main()

    mock_engine.archive_raw_summary.assert_not_called()
    mock_engine.ingest_transcript.assert_not_called()


def test_default_archives_happy_path(mocker, monkeypatch):
    """Not yet archived + transcript present -> archive_raw_summary runs
    once, and the old LLM path is never touched."""
    mock_engine = _patch_common(mocker, monkeypatch, ["script", "--date", "2026-04-10"])
    mocker.patch.object(
        rwi.os.path, "exists", side_effect=_fake_exists(done_exists=False, transcript_exists=True)
    )

    rwi.main()

    mock_engine.archive_raw_summary.assert_called_once()
    call_args = mock_engine.archive_raw_summary.call_args.args
    assert call_args[1] == "2026-04-10"
    assert call_args[0].endswith("research_digest_2026-04-10.txt")
    mock_engine.ingest_transcript.assert_not_called()


def test_default_date_range_processes_each_date(mocker, monkeypatch):
    """--start-date/--end-date iterates over the whole inclusive range."""
    mock_engine = _patch_common(
        mocker,
        monkeypatch,
        ["script", "--start-date", "2026-04-10", "--end-date", "2026-04-11"],
    )
    mocker.patch.object(
        rwi.os.path, "exists", side_effect=_fake_exists(done_exists=False, transcript_exists=True)
    )

    rwi.main()

    assert mock_engine.archive_raw_summary.call_count == 2
    processed_dates = {
        call.args[1] for call in mock_engine.archive_raw_summary.call_args_list
    }
    assert processed_dates == {"2026-04-10", "2026-04-11"}


def test_default_archive_failure_is_isolated_per_date(mocker, monkeypatch):
    """One date raising during archiving must not stop the others."""
    mock_engine = _patch_common(
        mocker,
        monkeypatch,
        ["script", "--start-date", "2026-04-10", "--end-date", "2026-04-11"],
    )
    mocker.patch.object(
        rwi.os.path, "exists", side_effect=_fake_exists(done_exists=False, transcript_exists=True)
    )
    mock_engine.archive_raw_summary.side_effect = [RuntimeError("boom"), "fake/path.md"]

    rwi.main()  # must not raise

    assert mock_engine.archive_raw_summary.call_count == 2


# --- Opt-in --llm-wiki path ---------------------------------------------------


def test_llm_wiki_flag_uses_full_pipeline(mocker, monkeypatch):
    """--llm-wiki switches to ingest_transcript and never touches the
    default archive method."""
    mock_engine = _patch_common(
        mocker, monkeypatch, ["script", "--date", "2026-04-10", "--llm-wiki"]
    )
    mocker.patch.object(
        rwi.os.path, "exists", side_effect=_fake_exists(done_exists=False, transcript_exists=True)
    )

    rwi.main()

    mock_engine.ingest_transcript.assert_called_once()
    call_args = mock_engine.ingest_transcript.call_args.args
    assert call_args[1] == "2026-04-10"
    mock_engine.archive_raw_summary.assert_not_called()


def test_llm_wiki_skips_when_source_already_ingested(mocker, monkeypatch):
    """--llm-wiki checks wiki/sources/ (not wiki/raw_summary/) for its own
    idempotency marker."""
    mock_engine = _patch_common(
        mocker, monkeypatch, ["script", "--date", "2026-04-10", "--llm-wiki"]
    )
    mocker.patch.object(
        rwi.os.path, "exists", side_effect=_fake_exists(done_exists=True, transcript_exists=True)
    )

    rwi.main()

    mock_engine.ingest_transcript.assert_not_called()
