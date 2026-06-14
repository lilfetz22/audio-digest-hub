#!/usr/bin/env python3
"""
pipeline.py — daily orchestrator for the audio digest hub.

Cross-platform replacement for the Windows `.bat` workflow. Designed to be
invoked directly by cron on the Ubuntu server, or run by hand on either OS.

Steps, in order, with fail-fast semantics:
  1. (Fridays only) `node scripts/cleanup-trigger.js`
  2. (Fridays only) `node scripts/cleanup-local-files.js`
  3. `python src/audiobooks/research_papers/run_research_pipeline.py`
  4. `python src/audiobooks/generate_audiobook.py`

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
import subprocess
import sys
from pathlib import Path
from typing import List, Union

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
AUDIOBOOKS_DIR = REPO_ROOT / "src" / "audiobooks"
SCRIPTS_DIR = REPO_ROOT / "scripts"
SEEN_PAPERS_CSV = AUDIOBOOKS_DIR / "research_papers" / "seen_papers.csv"


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


def run_step(name: str, argv: List[Union[str, Path]], cwd: Path) -> None:
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
        raise SystemExit(
            f"{name} failed with exit code {result.returncode}{signal_info}; aborting pipeline."
        )


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

    run_step(
        "research-pipeline",
        [py, AUDIOBOOKS_DIR / "research_papers" / "run_research_pipeline.py"],
        REPO_ROOT,
    )

    run_step(
        "generate-audiobook",
        [py, AUDIOBOOKS_DIR / "generate_audiobook.py"],
        REPO_ROOT,
    )

    logger.info("Pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
