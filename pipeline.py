#!/usr/bin/env python3
"""
pipeline.py — daily orchestrator for the audio digest hub.

Cross-platform replacement for the Windows `.bat` workflow. Designed to be
invoked directly by cron on the Ubuntu server, or run by hand on either OS.

Steps, in order:
  1. (Fridays only) `node scripts/cleanup-trigger.js`                            [fatal]
  2. (Fridays only) `node scripts/cleanup-local-files.js`                        [fatal]
  3. `python src/audiobooks/date_range.py` — resolve the date window once
  4. `python src/audiobooks/research_papers/run_research_pipeline.py`           [fatal]
  5. `python src/audiobooks/generate_audiobook.py`                              [fatal]
  6. `python src/audiobooks/research_papers/run_wiki_ingestion.py`          [non-fatal]

Step 3 decides which days everything else processes — normally "every day
since the last audiobook upload, through yesterday" — and steps 4-6 are all
handed that same window as --start-date/--end-date. Resolving it once is what
keeps the stages in agreement: they used to each work it out for themselves,
and disagreed, so a missed day produced an audiobook with no research digest
folded into it. If step 3 can't reach the API, the range is omitted and each
stage falls back to its own default rather than the run being skipped.

Step 6 runs last and is deliberately non-fatal. By default it just archives
the day's transcript verbatim into the wiki repo (no LLM calls, cheap) — see
run_wiki_ingestion.py's docstring for the opt-in `--llm-wiki` full pipeline,
which is NOT run here by default because it was previously the single
biggest contributor to multi-hour pipeline runs. Being last + non-fatal
means this step can never block or fail the audiobook, which by this point
has already been generated and uploaded.

The two Python steps are invoked via the project venv's interpreter directly,
so no shell activation (`source ... activate`) is required — that activation
would not propagate to child processes anyway.

Usage:
    python pipeline.py
    python pipeline.py --skip-cleanup
"""
from __future__ import annotations

import argparse
import datetime
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
AUDIOBOOKS_DIR = REPO_ROOT / "src" / "audiobooks"
SCRIPTS_DIR = REPO_ROOT / "scripts"
SEEN_PAPERS_CSV = AUDIOBOOKS_DIR / "research_papers" / "seen_papers.csv"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def find_venv_python() -> Path:
    """
    Locate the project venv's interpreter. Tries the audiobooks-local venv
    first (matches the existing layout from the .bat), then common fallbacks.
    Falls back to sys.executable when no venv is found (e.g. CI environments
    where packages are installed directly into the system Python).
    """
    candidates = [
        # Project-local venvs under src/audiobooks/
        AUDIOBOOKS_DIR / ".venv" / "bin" / "python",                       # Linux/Mac (Ubuntu server)
        AUDIOBOOKS_DIR / ".venv" / "Scripts" / "python.exe",               # Windows
        AUDIOBOOKS_DIR / "audiogeneratorvenv" / "bin" / "python",          # Linux/Mac (legacy name)
        AUDIOBOOKS_DIR / "audiogeneratorvenv" / "Scripts" / "python.exe",  # Windows .bat default
        # Repo-root fallbacks
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / "venv" / "bin" / "python",
        REPO_ROOT / "venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    logger.warning(
        "No project venv found; falling back to current interpreter (%s). "
        "Looked for:\n  - %s",
        sys.executable,
        "\n  - ".join(str(c) for c in candidates),
    )
    return Path(sys.executable)


def reset_latest_research_day() -> int:
    """
    Drop every row from seen_papers.csv that shares the latest date in the file.
    Useful as a "let me retry today" reset after a downstream pipeline failure
    has left the dedup CSV thinking today's papers are already processed.

    Returns the number of rows removed.
    """
    import csv as _csv

    if not SEEN_PAPERS_CSV.exists():
        logger.info("No seen_papers.csv at %s — nothing to reset.", SEEN_PAPERS_CSV)
        return 0

    with open(SEEN_PAPERS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = _csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not rows:
        logger.info("seen_papers.csv has no data rows — nothing to reset.")
        return 0

    dates = [r["date"] for r in rows if r.get("date")]
    if not dates:
        logger.info("seen_papers.csv has no parseable date column — nothing to reset.")
        return 0

    # Dates are %Y-%m-%d, so lexicographic max == chronological max.
    max_date = max(dates)
    kept = [r for r in rows if r.get("date") != max_date]
    removed = len(rows) - len(kept)

    with open(SEEN_PAPERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    logger.info(
        "Removed %d row(s) for date %s from %s (%d row(s) kept).",
        removed, max_date, SEEN_PAPERS_CSV, len(kept),
    )
    return removed


def resolve_date_range(py: Path) -> Optional[Tuple[str, str]]:
    """Ask date_range.py which days the whole pipeline should process.

    Resolved once, here, so every stage is handed the same explicit
    --start-date/--end-date rather than each working it out for itself. That
    mismatch is what used to leave holes: generate_audiobook.py backfilled
    from the last upload while the research stage only ever did yesterday, so
    a missed day produced an audiobook with no research digest in it.

    Returns (start, end) as YYYY-MM-DD strings, ("", "") when there is
    nothing new to process, or None if the range could not be determined —
    in which case the caller should fall back to per-stage defaults rather
    than skip the run.

    Invoked as a subprocess (not imported) because date_range.py needs the
    venv's `requests`, and pipeline.py itself may be running under a
    different interpreter — the same reason every other step is shelled out.
    """
    script = AUDIOBOOKS_DIR / "date_range.py"
    result = subprocess.run(
        [str(py), str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.stderr:
        logger.info("date_range.py:\n%s", result.stderr.rstrip())
    if result.returncode != 0:
        logger.warning(
            "Could not resolve the date range (exit code %d); each stage will "
            "fall back to its own default.",
            result.returncode,
        )
        return None

    parts = result.stdout.split()
    if not parts:
        return ("", "")
    if len(parts) != 2 or not all(_DATE_RE.match(p) for p in parts):
        logger.warning(
            "Unexpected output from date_range.py (%r); each stage will fall "
            "back to its own default.",
            result.stdout,
        )
        return None
    return (parts[0], parts[1])


def run_step(name: str, argv: List[Union[str, Path]], cwd: Path, fatal: bool = True) -> None:
    """Run one pipeline step.

    When `fatal` is False, a nonzero exit code is logged as an error and
    swallowed instead of raising `SystemExit` — used for steps (like wiki
    ingestion) that must never be able to take the rest of the pipeline
    down with them.
    """
    pretty = " ".join(str(a) for a in argv)
    logger.info("=== %s ===", name)
    logger.info("$ %s   (cwd=%s)", pretty, cwd)
    result = subprocess.run([str(a) for a in argv], cwd=str(cwd))
    if result.returncode != 0:
        signal_info = ""
        if result.returncode < 0:
            import signal as _signal
            signum = -result.returncode
            sig_name = _signal.Signals(signum).name if signum in _signal.Signals._value2member_map_ else f"signal {signum}"
            signal_info = f" (killed by {sig_name} — likely OOM / kernel termination)"
        message = f"{name} failed with exit code {result.returncode}{signal_info}"
        if fatal:
            raise SystemExit(f"{message}; aborting pipeline.")
        logger.error("%s; continuing (non-fatal step).", message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Daily orchestrator for audio-digest-hub.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip the Friday cleanup step even if today is Friday.",
    )
    parser.add_argument(
        "--reset-latest-research-day",
        action="store_true",
        help=(
            "Maintenance mode: drop every row from "
            "src/audiobooks/research_papers/seen_papers.csv that shares the "
            "latest date in the file, then exit without running the pipeline. "
            "Use after a downstream failure so the next run will re-score the "
            "most recent day's papers instead of treating them as duplicates."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.reset_latest_research_day:
        reset_latest_research_day()
        return 0

    py = find_venv_python()
    logger.info("Project venv: %s", py)

    today = datetime.date.today()
    weekday = today.strftime("%A")

    if weekday == "Friday" and not args.skip_cleanup:
        logger.info("Today is Friday — running cleanup")
        run_step(
            "cleanup-trigger",
            ["node", SCRIPTS_DIR / "cleanup-trigger.js"],
            REPO_ROOT,
        )
        run_step(
            "cleanup-local-files",
            ["node", SCRIPTS_DIR / "cleanup-local-files.js"],
            REPO_ROOT,
        )
    else:
        logger.info(
            "Today is %s — skipping cleanup (only runs on Fridays).", weekday
        )

    # Resolve the date range once, then hand the same window to every stage.
    date_window = resolve_date_range(py)
    if date_window == ("", ""):
        # The audiobook watermark is current, but that is not a completion
        # signal for wiki ingestion — it has its own transcript-based
        # default (resolve_transcript_dates) that can still catch up
        # anything left unarchived, e.g. after the wiki submodule was
        # initialised late.
        logger.info(
            "Nothing new to process for the audiobook — running wiki ingestion "
            "with its own transcript-based default in case anything is unarchived."
        )
        run_step(
            "wiki-ingestion",
            [py, AUDIOBOOKS_DIR / "research_papers" / "run_wiki_ingestion.py"],
            REPO_ROOT,
            fatal=False,
        )
        return 0

    date_args: List[Union[str, Path]] = []
    if date_window is not None:
        start, end = date_window
        logger.info("Processing %s through %s", start, end)
        date_args = ["--start-date", start, "--end-date", end]

    run_step(
        "research-pipeline",
        [py, AUDIOBOOKS_DIR / "research_papers" / "run_research_pipeline.py", *date_args],
        REPO_ROOT,
    )

    run_step(
        "generate-audiobook",
        [py, AUDIOBOOKS_DIR / "generate_audiobook.py", *date_args],
        REPO_ROOT,
    )

    # Runs last and non-fatal: the audiobook above is already generated and
    # uploaded by this point, so a slow or failing wiki stage can no longer
    # block or take down the actual deliverable.
    run_step(
        "wiki-ingestion",
        [py, AUDIOBOOKS_DIR / "research_papers" / "run_wiki_ingestion.py", *date_args],
        REPO_ROOT,
        fatal=False,
    )

    logger.info("Pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
