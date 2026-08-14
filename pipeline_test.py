"""Tests for pipeline.py's date-range orchestration.

The point of resolving the range here is that every stage gets handed the
same window. Each stage can still work it out for itself (that's the fallback
when the API is unreachable), but when they each did it independently they
disagreed — generate_audiobook.py backfilled from the last upload while the
research stage only ever did yesterday, so a missed day produced an audiobook
with no research digest folded into it.

Run with:  python -m pytest pipeline_test.py
"""

import subprocess

import pytest

import pipeline


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


# --- resolve_date_range -------------------------------------------------------


def test_resolve_date_range_parses_start_and_end(mocker):
    mocker.patch.object(
        pipeline.subprocess, "run", return_value=_completed(stdout="2026-08-11 2026-08-13\n")
    )

    assert pipeline.resolve_date_range(pipeline.Path("python")) == (
        "2026-08-11",
        "2026-08-13",
    )


def test_resolve_date_range_empty_stdout_means_nothing_to_do(mocker):
    mocker.patch.object(pipeline.subprocess, "run", return_value=_completed(stdout="\n"))

    assert pipeline.resolve_date_range(pipeline.Path("python")) == ("", "")


@pytest.mark.parametrize(
    "result",
    [
        _completed(returncode=1, stderr="config missing"),
        _completed(stdout="2026-08-11"),  # only one date
        _completed(stdout="a b c"),
        _completed(stdout="a b"),  # two tokens, but not dates
    ],
)
def test_resolve_date_range_returns_none_when_undeterminable(mocker, result):
    """None means "fall back to per-stage defaults", which is different from
    ("", "") meaning "there is genuinely nothing to process"."""
    mocker.patch.object(pipeline.subprocess, "run", return_value=result)

    assert pipeline.resolve_date_range(pipeline.Path("python")) is None


# --- main() wiring ------------------------------------------------------------


@pytest.fixture
def stub_main(mocker):
    """Stub main()'s side effects and collect the argv of each step it runs."""
    mocker.patch.object(pipeline, "find_venv_python", return_value=pipeline.Path("py"))
    mocker.patch.object(pipeline.logging, "basicConfig")
    calls = {}

    def fake_run_step(name, argv, cwd, fatal=True):
        calls[name] = [str(a) for a in argv]

    mocker.patch.object(pipeline, "run_step", side_effect=fake_run_step)
    return calls


_STAGES = ("research-pipeline", "generate-audiobook", "wiki-ingestion")


def test_main_passes_the_same_range_to_every_stage(mocker, stub_main):
    mocker.patch.object(
        pipeline, "resolve_date_range", return_value=("2026-08-11", "2026-08-13")
    )
    mocker.patch.object(pipeline.sys, "argv", ["pipeline.py"])

    assert pipeline.main() == 0

    for stage in _STAGES:
        argv = stub_main[stage]
        assert argv[-4:] == [
            "--start-date",
            "2026-08-11",
            "--end-date",
            "2026-08-13",
        ], stage


def test_main_skips_audiobook_stages_but_still_runs_wiki_when_caught_up(mocker, stub_main):
    """The audiobook watermark being current isn't a completion signal for
    wiki ingestion, which has its own transcript-based default and can still
    catch up anything left unarchived."""
    mocker.patch.object(pipeline, "resolve_date_range", return_value=("", ""))
    mocker.patch.object(pipeline.sys, "argv", ["pipeline.py"])

    assert pipeline.main() == 0

    assert "research-pipeline" not in stub_main
    assert "generate-audiobook" not in stub_main
    assert "wiki-ingestion" in stub_main
    assert "--start-date" not in stub_main["wiki-ingestion"]


def test_main_omits_date_flags_when_range_is_undeterminable(mocker, stub_main):
    """API unreachable: still run, letting each stage resolve its own dates."""
    mocker.patch.object(pipeline, "resolve_date_range", return_value=None)
    mocker.patch.object(pipeline.sys, "argv", ["pipeline.py"])

    assert pipeline.main() == 0

    for stage in _STAGES:
        argv = stub_main[stage]
        assert "--start-date" not in argv, stage
        assert "--end-date" not in argv, stage


def test_main_reset_flag_short_circuits_before_resolving(mocker, stub_main):
    mock_resolve = mocker.patch.object(pipeline, "resolve_date_range")
    mocker.patch.object(pipeline, "reset_latest_research_day")
    mocker.patch.object(pipeline.sys, "argv", ["pipeline.py", "--reset-latest-research-day"])

    assert pipeline.main() == 0

    mock_resolve.assert_not_called()
    assert stub_main == {}
