"""CLI entry point for the research paper pipeline."""

import argparse
import configparser
import datetime
import logging
import os
import sys

# Add parent directory to path so we can import from the audiobooks package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from research_papers.email_parser import ArxivHFEmailParser
from research_papers.paper_downloader import PaperContentDownloader
from research_papers.paper_scorer import EmbeddingPaperScorer
from research_papers.paths import RAW_CONTENT_DIR
from research_papers.transcript_generator import GeminiTranscriptGenerator
from research_papers.feedback import PreferenceProfileManager, FeedbackClient
from research_papers.pipeline import ResearchPaperPipeline

logger = logging.getLogger(__name__)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def _resolve_config_relative_path(config_dir, path_value):
    """Resolve config-relative paths without altering absolute paths."""
    if not path_value:
        return path_value
    return (
        os.path.normpath(path_value)
        if os.path.isabs(path_value)
        else os.path.normpath(os.path.join(config_dir, path_value))
    )


def setup_logging():
    """Configure logging for the research pipeline."""
    log_file = "research_pipeline.log"
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
    logger.info("Research paper pipeline starting...")


def load_config(config_path=None):
    """Load configuration from INI file."""
    if config_path is None:
        # config.ini lives one directory up from this script (src/audiobooks/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(script_dir), "config.ini")
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)
    config_dir = os.path.dirname(os.path.abspath(config_path))

    try:
        return {
            "api_url": config["WebApp"]["API_URL"],
            "api_key": config["WebApp"]["API_KEY"],
            "credentials_file": _resolve_config_relative_path(
                config_dir, config["Gmail"]["CREDENTIALS_FILE"]
            ),
            "token_file": _resolve_config_relative_path(
                config_dir, config["Gmail"]["TOKEN_FILE"]
            ),
            "gemini_api_key": config["Gemini"]["API_KEY"],
            "generation_model": config["Gemini"]["GENERATION_MODEL"],
            "backup_api_key": config.get("Gemini", "BACKUP_API_KEY", fallback=None),
            "scoring_model_name": config.get(
                "Scoring", "MODEL_NAME", fallback="all-MiniLM-L6-v2"
            ),
            "arxiv_senders": [
                s.strip() for s in config["ResearchPapers"]["ARXIV_SENDERS"].split(",")
            ],
            "huggingface_senders": [
                s.strip()
                for s in config["ResearchPapers"]["HUGGINGFACE_SENDERS"].split(",")
            ],
            "top_n_threshold": config.getint(
                "ResearchPapers", "TOP_N_THRESHOLD", fallback=10
            ),
            "top_n_deep_dive": config.getint(
                "ResearchPapers", "TOP_N_DEEP_DIVE", fallback=25
            ),
            "arxiv_delay_seconds": config.getint(
                "ResearchPapers", "ARXIV_DELAY_SECONDS", fallback=3
            ),
            "wiki_auto_commit": config.getboolean(
                "Wiki", "AUTO_COMMIT", fallback=False
            ),
            "wiki_auto_push": config.getboolean("Wiki", "AUTO_PUSH", fallback=False),
            "wiki_push_parent": config.getboolean(
                "Wiki", "PUSH_PARENT", fallback=False
            ),
            "wiki_model": config.get(
                "Wiki", "WIKI_MODEL", fallback=config.get("Gemini", "GENERATION_MODEL")
            ),
            "wiki_backup_api_key": config.get(
                "Wiki",
                "BACKUP_API_KEY",
                fallback=config.get("Gemini", "BACKUP_API_KEY", fallback=None),
            ),
            "openrouter_api_key": config.get(
                "OpenRouter", "OPENROUTER_API_KEY", fallback=None
            ),
            "openrouter_model": config.get(
                "OpenRouter", "OPENROUTER_MODEL", fallback=None
            ),
        }
    except KeyError as e:
        logger.error(f"Missing config key: {e}")
        sys.exit(1)


def authenticate_gmail(token_file, credentials_file):
    """Authenticate with Gmail API (reused pattern from generate_audiobook.py)."""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                logger.error(f"Credentials file not found: {credentials_file}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=8080, open_browser=False)
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return creds


def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="Research paper digest pipeline")
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--date", help="Process a single date (YYYY-MM-DD)")
    date_group.add_argument("--start-date", help="Start of date range (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End of date range (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.end_date and not args.start_date:
        parser.error("--end-date requires --start-date")

    # Determine dates to process
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

    # Load config
    config = load_config()

    # Authenticate Gmail
    creds = authenticate_gmail(config["token_file"], config["credentials_file"])
    gmail_service = build("gmail", "v1", credentials=creds)

    # Wire up components
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = RAW_CONTENT_DIR
    profile_path = os.path.join(script_dir, "preference_profile.json")

    email_parser = ArxivHFEmailParser(
        arxiv_senders=config["arxiv_senders"],
        huggingface_senders=config["huggingface_senders"],
    )
    paper_downloader = PaperContentDownloader(
        delay_seconds=config["arxiv_delay_seconds"]
    )
    interest_profile_path = os.path.join(script_dir, "prompts", "interest_profile.txt")
    paper_scorer = EmbeddingPaperScorer(
        model_name=config["scoring_model_name"],
        top_n=config["top_n_threshold"],
        interest_profile_path=interest_profile_path,
    )
    transcript_generator = GeminiTranscriptGenerator(
        api_key=config["gemini_api_key"],
        model_name=config["generation_model"],
        backup_api_key=config.get("backup_api_key"),
        openrouter_api_key=config.get("openrouter_api_key"),
        openrouter_model=config.get("openrouter_model"),
    )
    feedback_manager = PreferenceProfileManager(
        profile_path=profile_path,
        api_key=config["gemini_api_key"],
    )
    feedback_client = FeedbackClient(
        api_url=config["api_url"],
        api_key=config["api_key"],
    )

    pipeline = ResearchPaperPipeline(
        email_parser=email_parser,
        paper_downloader=paper_downloader,
        paper_scorer=paper_scorer,
        transcript_generator=transcript_generator,
        feedback_manager=feedback_manager,
        feedback_client=feedback_client,
        gmail_service=gmail_service,
        api_url=config["api_url"],
        api_key=config["api_key"],
        output_dir=output_dir,
        top_n_deep_dive=config["top_n_deep_dive"],
    )

    # Run pipeline for each date. Wiki ingestion is intentionally not run
    # here — it's a separate, slower, less reliable stage (LLM-per-section
    # over OpenRouter) that must not be able to block or delay the
    # audiobook. See run_wiki_ingestion.py, invoked as its own later step.
    for date in dates_to_process:
        date_str = date.strftime("%Y-%m-%d")
        try:
            pipeline.run(date_str)
        except Exception as e:
            logger.error(f"Pipeline failed for {date_str}: {e}", exc_info=True)
            continue

    logger.info("Research paper pipeline finished.")


if __name__ == "__main__":
    main()
