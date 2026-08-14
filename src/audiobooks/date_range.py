"""The pipeline's single source of truth for "which days should we process?".

Every stage used to answer this for itself, and they disagreed:
generate_audiobook.py backfilled from the last audiobook upload, while
run_research_pipeline.py and run_wiki_ingestion.py only ever did yesterday.
A missed run (server down, failed run, CI outage) therefore left a permanent
hole — the audiobook for the skipped day still got built, just with no
research digest folded into it.

Now `pipeline.py` resolves the range **once**, before any stage runs, and
passes the same explicit `--start-date`/`--end-date` to all three. The
per-stage defaults here are the fallback for running a stage by hand, or for
when the orchestrator could not reach the API.

The last *audiobook upload* date is the watermark, because that is the
durable, shared record of what has actually shipped. Note that
/research-papers has no "list all dates" endpoint (only a single date, or
clicked-paper feedback), so it could not supply one even if we wanted a
research-specific watermark.

Run as a script, this prints the resolved range for `pipeline.py` to consume:

    $ python src/audiobooks/date_range.py
    2026-08-11 2026-08-13

Stdout carries only the range (empty when there is nothing to do); logging
goes to stderr so the caller can parse stdout safely.
"""

import argparse
import configparser
import datetime
import glob
import logging
import os
import re
import sys
from typing import List, Optional

import requests

from http_utils import requests_get_with_retry

logger = logging.getLogger(__name__)

# Audiobook titles carry their content date, e.g. "Daily Digest for 2026-08-13".
_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")

# Default ceiling on how far back a single run will reach. 14 days matches
# dedup.py's rolling window — past that, seen_papers.csv no longer has the
# state that would stop a backfill from re-processing papers as if new. It
# also keeps a long-dormant deployment from waking up and synthesizing
# months of TTS in one go.
DEFAULT_MAX_BACKFILL_DAYS = 14


class WatermarkUnavailable(Exception):
    """The audiobooks API could not be reached or returned an unusable body.

    Raised only by `resolve_default_dates(..., strict=True)` — the CLI's
    contract with `pipeline.py`. Everywhere else, "could not determine the
    watermark" is treated as "no previous uploads" and degrades to
    processing `end_date` only.
    """


def find_last_upload_date(api_url: str, api_key: str) -> Optional[datetime.date]:
    """Finds the last date when an audiobook was uploaded by querying the API.

    Returns None (rather than raising) on any API or parsing problem, so a
    flaky backend degrades to "yesterday only" instead of failing the run.
    """
    logger.info("Finding the last upload date from existing audiobooks...")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{api_url}/audiobooks"

    try:
        response = requests_get_with_retry(url, headers, timeout=30)
        if response.status_code != 200:
            logger.warning(
                f"API returned status {response.status_code}. Using yesterday as default start date."
            )
            return None

        audiobooks = response.json()
        if not audiobooks:
            logger.info("No existing audiobooks found. Using yesterday as default start date.")
            return None
        if not isinstance(audiobooks, list):
            logger.warning(
                f"Unexpected /audiobooks payload type {type(audiobooks).__name__}; "
                "using yesterday as default start date."
            )
            return None

        last_date = None
        for audiobook in audiobooks:
            if not isinstance(audiobook, dict):
                logger.warning(f"Skipping non-object audiobook entry: {audiobook!r}")
                continue
            title = audiobook.get("title", "")
            match = _DATE_PATTERN.search(title)
            if not match:
                continue
            try:
                audiobook_date = datetime.datetime.strptime(
                    match.group(1), "%Y-%m-%d"
                ).date()
            except ValueError:
                logger.warning(f"Could not parse date from title: {title}")
                continue
            if last_date is None or audiobook_date > last_date:
                last_date = audiobook_date

        if last_date:
            logger.info(f"Found last upload date: {last_date}")
            return last_date

        logger.info("No valid dates found in existing audiobooks. Using yesterday as default start date.")
        return None

    except (requests.exceptions.RequestException, ValueError, TypeError, AttributeError) as e:
        logger.error(f"Error fetching audiobooks to find last upload date: {e}")
        logger.info("Using yesterday as default start date due to API error.")
        return None


def resolve_default_dates(
    api_url: str,
    api_key: str,
    end_date: datetime.date,
    max_backfill_days: int = DEFAULT_MAX_BACKFILL_DAYS,
    strict: bool = False,
) -> List[datetime.date]:
    """Dates to process when the caller passed no explicit date flags.

    Every day from the day after the last audiobook upload through
    `end_date` (normally yesterday), inclusive. Returns an empty list when
    the watermark is already current — every stage is individually
    idempotent, but there is no point spinning them up with nothing to do.

    `strict=True` is the CLI's contract with `pipeline.py`: rather than
    silently degrading to "process `end_date` only" when the watermark
    can't be determined, it raises `WatermarkUnavailable` so `date_range.py`
    exits non-zero and `pipeline.py` omits the range entirely, letting each
    stage fall back to its own default instead of having a yesterday-only
    window pinned onto it. Other callers (generate_audiobook.py,
    run_research_pipeline.py) keep the lenient default.
    """
    if max_backfill_days < 0:
        raise ValueError(f"max_backfill_days must be >= 0, got {max_backfill_days}")

    last_upload_date = find_last_upload_date(api_url, api_key)
    if last_upload_date is None:
        if strict:
            raise WatermarkUnavailable(
                "Could not determine the last upload date from the audiobooks API."
            )
        logger.info(
            "No previous uploads found or error determining last upload date. "
            f"Processing {end_date.strftime('%Y-%m-%d')} only."
        )
        return [end_date]

    start_date = last_upload_date + datetime.timedelta(days=1)
    if start_date > end_date:
        logger.info(
            f"Last upload date ({last_upload_date}) is recent. No new dates to process."
        )
        return []

    if max_backfill_days > 0:
        earliest_allowed = end_date - datetime.timedelta(days=max_backfill_days - 1)
        if start_date < earliest_allowed:
            logger.warning(
                f"Backfill from {start_date} would exceed the "
                f"{max_backfill_days}-day limit; skipping "
                f"{start_date}..{earliest_allowed - datetime.timedelta(days=1)}. "
                "Re-run with --start-date to process them anyway."
            )
            start_date = earliest_allowed

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += datetime.timedelta(days=1)

    logger.info(
        "Adjusted date range based on last upload: "
        f"{[d.strftime('%Y-%m-%d') for d in dates]}"
    )
    return dates


def resolve_transcript_dates(
    raw_content_dir: str,
    end_date: datetime.date,
    max_backfill_days: int = DEFAULT_MAX_BACKFILL_DAYS,
) -> List[datetime.date]:
    """Dates that have a research digest on disk — the standalone default for
    run_wiki_ingestion.py.

    Deliberately *not* keyed off the audiobook watermark. Wiki ingestion is
    the last pipeline step, running after generate_audiobook.py has already
    uploaded the backfilled days, so by the time it looks the watermark has
    advanced past exactly the dates it still needs to archive.

    The transcripts themselves are the honest signal: run_research_pipeline.py
    wrote one per day it processed, and the caller skips any date it has
    already archived. Only the floor is bounded (`max_backfill_days` back from
    `end_date`) — a transcript dated later than `end_date` is still worth
    archiving, e.g. one produced by a manual `--date` run.
    """
    if max_backfill_days < 0:
        raise ValueError(f"max_backfill_days must be >= 0, got {max_backfill_days}")

    floor = (
        end_date - datetime.timedelta(days=max_backfill_days - 1)
        if max_backfill_days > 0
        else None
    )

    dates = []
    for path in glob.glob(os.path.join(raw_content_dir, "research_digest_*.txt")):
        match = _DATE_PATTERN.search(os.path.basename(path))
        if not match:
            continue
        try:
            transcript_date = datetime.datetime.strptime(
                match.group(1), "%Y-%m-%d"
            ).date()
        except ValueError:
            logger.warning(f"Could not parse date from transcript filename: {path}")
            continue
        if floor is not None and transcript_date < floor:
            continue
        dates.append(transcript_date)

    dates.sort()
    if not dates:
        logger.info(f"No research digests found in {raw_content_dir}.")
    else:
        logger.info(
            f"Found research digests for: {[d.strftime('%Y-%m-%d') for d in dates]}"
        )
    return dates


def _load_webapp_config(config_path: Optional[str] = None) -> tuple:
    """Read just the [WebApp] credentials out of config.ini.

    Deliberately not research_papers.run_research_pipeline.load_config: that
    pulls in the Gmail/Gemini stack and validates keys this script does not
    need, and it would make date_range.py import a module that imports it.
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)
    return config["WebApp"]["API_URL"], config["WebApp"]["API_KEY"]


def main(argv=None) -> int:
    """Print the resolved date range as `START END` for pipeline.py.

    Prints nothing when there is nothing to process. Exits non-zero only when
    the range could not be determined at all, which tells the orchestrator to
    fall back to letting each stage resolve its own dates.
    """
    parser = argparse.ArgumentParser(
        description="Print the date range the pipeline should process, as 'START END'."
    )
    parser.add_argument("--config", help="Path to config.ini")
    parser.add_argument(
        "--max-backfill-days",
        type=int,
        default=DEFAULT_MAX_BACKFILL_DAYS,
        help="Cap on how far back to reach (0 disables the cap).",
    )
    args = parser.parse_args(argv)

    # stderr, so stdout carries only the range.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    try:
        api_url, api_key = _load_webapp_config(args.config)
    except (FileNotFoundError, KeyError) as e:
        logger.error(f"Could not read [WebApp] config: {e}")
        return 1

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    try:
        dates = resolve_default_dates(
            api_url,
            api_key,
            yesterday,
            max_backfill_days=args.max_backfill_days,
            strict=True,
        )
    except WatermarkUnavailable as e:
        logger.error("%s Each stage will resolve its own dates.", e)
        return 1
    if dates:
        print(f"{dates[0].strftime('%Y-%m-%d')} {dates[-1].strftime('%Y-%m-%d')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
