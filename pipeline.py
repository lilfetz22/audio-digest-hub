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


def find_venv_python() -> Path:
    """
    Locate the project venv's interpreter. Tries the audiobooks-local venv
    first (matches the existing layout from the .bat), then common fallbacks.
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
    raise FileNotFoundError(
        "No project venv found. Looked for:\n  - "
        + "\n  - ".join(str(c) for c in candidates)
    )


def run_step(name: str, argv: List[Union[str, Path]], cwd: Path) -> None:
    pretty = " ".join(str(a) for a in argv)
    logger.info("=== %s ===", name)
    logger.info("$ %s   (cwd=%s)", pretty, cwd)
    result = subprocess.run([str(a) for a in argv], cwd=str(cwd))
    if result.returncode != 0:
        raise SystemExit(
            f"{name} failed with exit code {result.returncode}; aborting pipeline."
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
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

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
        AUDIOBOOKS_DIR,
    )

    run_step(
        "generate-audiobook",
        [py, AUDIOBOOKS_DIR / "generate_audiobook.py"],
        AUDIOBOOKS_DIR,
    )

    logger.info("Pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
