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
from research_papers.paper_scorer import GeminiPaperScorer
from research_papers.transcript_generator import GeminiTranscriptGenerator
from research_papers.feedback import PreferenceProfileManager, FeedbackClient
from research_papers.pipeline import ResearchPaperPipeline

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


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


def load_config(config_path="config.ini"):
    """Load configuration from INI file."""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        return {
            "api_url": config["WebApp"]["API_URL"],
            "api_key": config["WebApp"]["API_KEY"],
            "credentials_file": config["Gmail"]["CREDENTIALS_FILE"],
            "token_file": config["Gmail"]["TOKEN_FILE"],
            "gemini_api_key": config["Gemini"]["API_KEY"],
            "scoring_model": config["Gemini"]["SCORING_MODEL"],
            "generation_model": config["Gemini"]["GENERATION_MODEL"],
            "arxiv_senders": [
                s.strip()
                for s in config["ResearchPapers"]["ARXIV_SENDERS"].split(",")
            ],
            "huggingface_senders": [
                s.strip()
                for s in config["ResearchPapers"]["HUGGINGFACE_SENDERS"].split(",")
            ],
            "top_n_threshold": config.getint(
                "ResearchPapers", "TOP_N_THRESHOLD", fallback=10
            ),
            "arxiv_delay_seconds": config.getint(
                "ResearchPapers", "ARXIV_DELAY_SECONDS", fallback=3
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
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return creds


def main():
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Research paper digest pipeline"
    )
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--date", help="Process a single date (YYYY-MM-DD)")
    date_group.add_argument("--start-date", help="Start of date range (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End of date range (YYYY-MM-DD)")
    args = parser.parse_args()

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
    creds = authenticate_gmail(config["credentials_file"], config["token_file"])
    gmail_service = build("gmail", "v1", credentials=creds)

    # Wire up components
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(os.path.dirname(script_dir), "raw_content")
    profile_path = os.path.join(script_dir, "preference_profile.json")

    email_parser = ArxivHFEmailParser(
        arxiv_senders=config["arxiv_senders"],
        huggingface_senders=config["huggingface_senders"],
    )
    paper_downloader = PaperContentDownloader(
        delay_seconds=config["arxiv_delay_seconds"]
    )
    paper_scorer = GeminiPaperScorer(
        api_key=config["gemini_api_key"],
        model_name=config["scoring_model"],
        top_n=config["top_n_threshold"],
    )
    transcript_generator = GeminiTranscriptGenerator(
        api_key=config["gemini_api_key"],
        model_name=config["generation_model"],
        use_batch=True,
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
    )

    # Run pipeline for each date
    for date in dates_to_process:
        date_str = date.strftime("%Y-%m-%d")
        try:
            pipeline.run(date_str)
        except Exception as e:
            logger.error(f"Pipeline failed for {date_str}: {e}", exc_info=True)

    logger.info("Research paper pipeline finished.")


if __name__ == "__main__":
    main()
