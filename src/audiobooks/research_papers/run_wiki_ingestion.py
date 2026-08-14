"""CLI entry point for archiving the research digest into the wiki repo —
deliberately separate from run_research_pipeline.py.

Reads the transcript that run_research_pipeline.py already wrote to
raw_content/research_digest_{date}.txt.

Default behavior: archive it verbatim into wiki/raw_summary/ with no LLM
calls at all (WikiIngestionEngine.archive_raw_summary) — just a durable
record of each day's papers.

Opt-in (--llm-wiki): run the older, much slower and less reliable full LLM
wiki pipeline instead (one classify+extract LLM call per transcript
section, routed through OpenRouter, then concept-page upsert). That path is
kept around in case the LLM wiki is revisited later, but is not used by
default — it was the single biggest contributor to multi-hour pipeline
runs (see the ingestion.py / gemini_client.py history for why).

Either way, this runs as its own pipeline step, after generate_audiobook.py,
non-fatal to the rest of the pipeline (see pipeline.py's
run_step(fatal=False)) — so even a hiccup here can never block or delay
the audiobook.
"""

import argparse
import datetime
import logging
import os
import sys

# Add parent directory to path so we can import from the audiobooks package,
# matching run_research_pipeline.py's sys.path setup.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research_papers.run_research_pipeline import load_config
from research_papers.wiki_engine.ingestion import WikiIngestionEngine

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging for the wiki ingestion step (its own log file, kept
    separate from research_pipeline.log so a slow/failing wiki run doesn't
    get lost in the main pipeline's log)."""
    log_file = "wiki_ingestion.log"
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    logger.info("Wiki ingestion starting...")


def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="Archive the research digest into the wiki repo")
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--date", help="Process a single date (YYYY-MM-DD)")
    date_group.add_argument("--start-date", help="Start of date range (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End of date range (YYYY-MM-DD)")
    parser.add_argument(
        "--llm-wiki",
        action="store_true",
        help=(
            "Opt into the old full LLM wiki pipeline (classify+extract per "
            "section, concept-page upsert) instead of the default cheap "
            "verbatim archive. Off by default — see module docstring."
        ),
    )
    args = parser.parse_args()

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    dates_to_process = []

    if args.date:
        dates_to_process.append(
            datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
        )
    elif args.start_date:
        start = datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end = (
            datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()
            if args.end_date
            else yesterday
        )
        current = start
        while current <= end:
            dates_to_process.append(current)
            current += datetime.timedelta(days=1)
    else:
        dates_to_process.append(yesterday)

    logger.info(
        f"Processing dates: {[d.strftime('%Y-%m-%d') for d in dates_to_process]}"
    )

    config = load_config()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(os.path.dirname(script_dir), "raw_content")
    wiki_dir = os.path.join(script_dir, "wiki")
    # parent_root is the audio-digest-hub repo root (3 levels above script_dir:
    # research_papers/ -> audiobooks/ -> src/ -> audio-digest-hub/)
    parent_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    wiki_engine = WikiIngestionEngine(
        wiki_dir=wiki_dir,
        repo_root=wiki_dir,  # wiki is its own git repo (submodule); commit inside it
        parent_root=parent_root,
        api_key=config["gemini_api_key"],
        model_name=config["wiki_model"],
        backup_api_key=config["wiki_backup_api_key"],
        openrouter_api_key=config.get("openrouter_api_key"),
        openrouter_model=config.get("openrouter_model"),
        auto_commit=config["wiki_auto_commit"],
        auto_push=config["wiki_auto_push"],
        push_parent=config["wiki_push_parent"],
    )

    if args.llm_wiki:
        logger.info("--llm-wiki set: using the full LLM classify+extract pipeline.")
    else:
        logger.info("Using the default no-LLM raw_summary archive.")

    for date in dates_to_process:
        date_str = date.strftime("%Y-%m-%d")
        transcript_path = os.path.join(output_dir, f"research_digest_{date_str}.txt")
        if args.llm_wiki:
            done_marker_path = os.path.join(wiki_dir, "sources", f"digest_{date_str}.md")
        else:
            done_marker_path = os.path.join(wiki_dir, "raw_summary", f"digest_{date_str}.md")

        if os.path.exists(done_marker_path):
            logger.info(f"Already processed for {date_str}, skipping.")
            continue
        if not os.path.exists(transcript_path):
            logger.info(f"No transcript found for {date_str}, skipping.")
            continue

        try:
            if args.llm_wiki:
                result = wiki_engine.ingest_transcript(transcript_path, date_str)
                logger.info(
                    f"Wiki ingestion for {date_str}: "
                    f"{len(result['concepts_created'])} concepts created, "
                    f"{len(result['concepts_updated'])} updated"
                )
            else:
                wiki_engine.archive_raw_summary(transcript_path, date_str)
                logger.info(f"Archived raw summary for {date_str}.")
        except Exception as e:
            logger.error(f"Processing failed for {date_str}: {e}", exc_info=True)

    logger.info("Wiki ingestion finished.")


if __name__ == "__main__":
    main()
