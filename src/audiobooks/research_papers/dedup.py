"""Rolling deduplication via a local CSV of recently-seen arXiv paper URLs.

The CSV (``seen_papers.csv``) lives next to the pipeline code and keeps a
14-day rolling window.  Before papers are scored each day, the pipeline calls
``deduplicate()`` which:

1. Loads the CSV and discards rows older than 14 days.
2. Removes any papers whose URL already appears in the CSV.
3. Appends the *new* papers (with today's date) to the CSV.
4. Returns only the non-duplicate papers.
"""

import csv
import datetime
import logging
import os
from typing import List

from .models import PaperReference

logger = logging.getLogger(__name__)

_CSV_FILENAME = "seen_papers.csv"
_RETENTION_DAYS = 14
_FIELDNAMES = ["date", "url", "title", "source", "category"]


def _csv_path() -> str:
    return os.path.join(os.path.dirname(__file__), _CSV_FILENAME)


def _load_csv() -> List[dict]:
    """Load existing rows, discarding entries older than the retention window."""
    path = _csv_path()
    if not os.path.exists(path):
        return []

    cutoff = datetime.date.today() - datetime.timedelta(days=_RETENTION_DAYS)
    rows: List[dict] = []
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row_date = datetime.datetime.strptime(
                        row["date"], "%Y-%m-%d"
                    ).date()
                    if row_date >= cutoff:
                        rows.append(row)
                except (KeyError, ValueError):
                    continue
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e}")
    return rows


def _save_csv(rows: List[dict]) -> None:
    """Write rows back to the CSV (overwrites)."""
    path = _csv_path()
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")


def deduplicate(
    papers: List[PaperReference], date_str: str
) -> List[PaperReference]:
    """Remove papers already seen in the past 14 days and record the new ones.

    Args:
        papers: All papers fetched for *date_str*.
        date_str: The pipeline date in ``YYYY-MM-DD`` format.

    Returns:
        The subset of *papers* that have **not** been seen before.
    """
    existing_rows = _load_csv()
    seen_urls = {row["url"] for row in existing_rows}

    new_papers: List[PaperReference] = []
    new_rows: List[dict] = []

    for paper in papers:
        if paper.url in seen_urls:
            continue
        new_papers.append(paper)
        seen_urls.add(paper.url)
        new_rows.append(
            {
                "date": date_str,
                "url": paper.url,
                "title": paper.title,
                "source": paper.source,
                "category": paper.category,
            }
        )

    removed_count = len(papers) - len(new_papers)
    if removed_count:
        logger.info(
            f"Dedup: removed {removed_count} previously-seen papers, "
            f"{len(new_papers)} new papers remain"
        )
    else:
        logger.info(f"Dedup: all {len(new_papers)} papers are new")

    # Persist: old rows (already pruned to 14 days) + today's new rows
    _save_csv(existing_rows + new_rows)

    return new_papers
