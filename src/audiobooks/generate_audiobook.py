# generate_audiobook.py

import os
import sys
import argparse
import configparser
import datetime
import json
import base64
import re
import logging  # Use standard logging
import traceback

# 3rd Party Libraries
import requests
import torch
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydub import AudioSegment
from TTS.api import TTS

# --- Configuration & Constants ---

# Configure logging to output to both a file and the console
logger = logging.getLogger(__name__)

# Gmail API Scopes: Read-only access is sufficient.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Temporary file names
TEMP_AUDIO_WAV = "temp_output.wav"
TEMP_AUDIO_MP3 = "temp_output.mp3"

# Coqui-TTS model configuration
TTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"

# Global TTS client, initialized once.
TTS_CLIENT = None

# --- Helper Functions ---


def setup_logging():
    """Configures the root logger for console and file output."""
    log_file = "audiobook_generator.log"
    # Use basicConfig to set up handlers and formatting
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )
    logger.info(f"Logging initialized. Output will be saved to {log_file}")


# --- Core Functions ---


def load_config(config_path="config.ini"):
    """Reads configuration from the INI file."""
    if not os.path.exists(config_path):
        logger.error(f"Configuration file '{config_path}' not found.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        app_config = {
            "api_url": config["WebApp"]["API_URL"],
            "api_key": config["WebApp"]["API_KEY"],
            "supabase_anon_key": config["WebApp"]["SUPABASE_ANON_KEY"],
            "credentials_file": config["Gmail"]["CREDENTIALS_FILE"],
            "token_file": config["Gmail"]["TOKEN_FILE"],
            # Optional TTS setting for voice cloning
            "reference_voice_file": config.get(
                "TTS", "REFERENCE_VOICE_FILE", fallback=None
            ),
        }
        return app_config
    except KeyError as e:
        logger.error(
            f"Missing key in config.ini: {e}. Ensure API_URL, API_KEY, and SUPABASE_ANON_KEY are in the [WebApp] section."
        )
        sys.exit(1)


def initialize_tts_model():
    """Loads the Coqui-TTS model into memory."""
    global TTS_CLIENT
    if TTS_CLIENT is None:
        logger.info(f"Loading Coqui-TTS model: {TTS_MODEL}")
        logger.info("This may take a moment and require significant RAM...")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")
            TTS_CLIENT = TTS(TTS_MODEL).to(device)
            logger.info("Coqui-TTS model loaded successfully.")
        except Exception as e:
            logger.error("Failed to load the TTS model.", exc_info=True)
            logger.error("Please ensure Coqui-TTS and PyTorch are installed correctly.")
            sys.exit(1)


def authenticate_gmail(token_file, credentials_file):
    """Handles Google OAuth2 flow and returns API credentials."""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token...")
            creds.refresh(Request())
        else:
            logger.info("Performing first-time Google authentication...")
            if not os.path.exists(credentials_file):
                logger.error(
                    f"Gmail credentials file ('{credentials_file}') not found."
                )
                logger.error(
                    "Please get it from Google Cloud Console and place it here."
                )
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())
            logger.info(f"Gmail token saved to '{token_file}'.")

    return creds


def fetch_sources(api_url, api_key, supabase_anon_key):
    """
    Fetches newsletter sources, with robust, detailed logging for all failure modes.
    """
    logger.info("Fetching newsletter sources from Web App...")
    headers = {"Authorization": f"Bearer {api_key}", "apikey": supabase_anon_key}
    url = f"{api_url}/api/v1/sources"

    try:
        # Make the request with a reasonable timeout
        response = requests.get(url, headers=headers, timeout=30)

        # Immediately check for bad HTTP status codes
        response.raise_for_status()

        # If the status is OK (2xx), then try to parse the JSON.
        return response.json()

    except requests.exceptions.JSONDecodeError:
        logger.error("CRITICAL: Failed to decode JSON from the API response.")
        logger.error("This means the server did not return valid JSON data.")
        logger.error(f"URL: {url}")
        logger.error(f"Status Code: {response.status_code}")
        logger.error(f"Response Body Received: {response.text[:500]}...")
        logger.error("Traceback:", exc_info=True)
        sys.exit(1)

    except requests.exceptions.HTTPError as e:
        logger.error(
            "HTTP Error occurred. The server responded with a non-200 status code."
        )
        logger.error(f"URL: {url}")
        logger.error(f"Status Code: {e.response.status_code}")
        logger.error(f"Response Body: {e.response.text[:500]}...")
        logger.error("Traceback:", exc_info=True)
        sys.exit(1)

    except requests.exceptions.RequestException as e:
        logger.error(
            "A fundamental network error occurred. Could not reach the server."
        )
        logger.error(f"URL: {url}")
        logger.error(f"Error: {e}")
        logger.error("Traceback:", exc_info=True)
        sys.exit(1)


def process_emails(service, sources, target_date_str):
    """Fetches and processes emails from Gmail for a given date and source list."""
    logger.info(f"Processing emails for date: {target_date_str}")

    sender_emails = [source["sender_email"] for source in sources]
    if not sender_emails:
        logger.info("No sources configured. Nothing to process.")
        return "", []

    sender_query = " OR ".join([f"from:{email}" for email in sender_emails])
    target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
    after_date = target_date.strftime("%Y/%m/%d")
    before_date = (target_date + datetime.timedelta(days=1)).strftime("%Y/%m/%d")

    query = f"({sender_query}) after:{after_date} before:{before_date}"
    logger.info(f"Using Gmail query: {query}")

    try:
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
    except HttpError as error:
        logger.error(f"An error occurred fetching emails: {error}", exc_info=True)
        return "", []

    if not messages:
        logger.info("No matching emails found for the specified date and senders.")
        return "", []

    all_text_blocks = []
    sender_to_custom_name = {
        s["sender_email"].lower(): s["custom_name"] for s in sources
    }

    for message_info in reversed(messages):
        msg = (
            service.users().messages().get(userId="me", id=message_info["id"]).execute()
        )
        payload = msg["payload"]
        headers = payload["headers"]

        sender_email = ""
        for h in headers:
            if h["name"] == "From":
                match = re.search(r"<(.+?)>", h["value"])
                sender_email = match.group(1).lower() if match else h["value"].lower()

        custom_name = sender_to_custom_name.get(sender_email, "Unknown Source")
        received_date_str = target_date.strftime("%B %d, %Y")
        body_text = ""

        try:
            if "parts" in payload:
                part = next(
                    (p for p in payload["parts"] if p["mimeType"] == "text/plain"),
                    next(
                        (p for p in payload["parts"] if p["mimeType"] == "text/html"),
                        None,
                    ),
                )
                if part:
                    data = part["body"]["data"]
                    body_text = base64.urlsafe_b64decode(data).decode("utf-8")
                    if part["mimeType"] == "text/html":
                        # Replace block-level tags with spaces to avoid words running together.
                        body_text = re.sub(
                            r"</(p|h[1-6]|div|li|tr|br)>",
                            " ",
                            body_text,
                            flags=re.IGNORECASE,
                        )
                        # Then strip all remaining tags
                        body_text = re.sub("<[^<]+?>", "", body_text)
                        # Consolidate whitespace
                        body_text = re.sub(r"\s+", " ", body_text).strip()
                else:
                    body_text = "Could not find a readable text part."
            elif "data" in payload["body"]:
                data = payload["body"]["data"]
                body_text = base64.urlsafe_b64decode(data).decode("utf-8")

            text_block = f"\n\nNewsletter from: {custom_name}. Received on: {received_date_str}.\n\n{body_text.strip()}"
            all_text_blocks.append({"text": text_block, "title": custom_name})

        except Exception as e:
            custom_name = sender_to_custom_name.get(sender_email, "Unknown Source")
            logger.error(f"Failed to parse email from {custom_name}", exc_info=True)
            error_block = (
                f"\n\n{custom_name} could not be processed and has been skipped.\n\n"
            )
            all_text_blocks.append(
                {"text": error_block, "title": f"{custom_name} (Error)"}
            )

    concatenated_text = "".join([block["text"] for block in all_text_blocks])
    return concatenated_text, all_text_blocks


def generate_audio(text_content, reference_voice_path):
    """Generates an MP3 file from text using the Coqui-TTS Python API."""
    if not text_content.strip():
        logger.info("No text content to synthesize. Skipping audio generation.")
        return False

    logger.info("Starting Coqui-TTS audio generation using Python API...")

    # Check if a valid reference voice file is provided for cloning
    speaker_wav = None
    if reference_voice_path and os.path.exists(reference_voice_path):
        logger.info(f"Using reference voice: {reference_voice_path}")
        speaker_wav = reference_voice_path
    else:
        logger.info("No valid reference voice found. Using the model's default voice.")

    try:
        # Generate speech to a WAV file (default for the API)
        TTS_CLIENT.tts_to_file(
            text=text_content,
            speaker_wav=speaker_wav,
            language="en",
            file_path=TEMP_AUDIO_WAV,
            speed=1.0,
        )

        logger.info(f"WAV file generated successfully: {TEMP_AUDIO_WAV}")
        logger.info(f"Converting WAV to MP3: {TEMP_AUDIO_MP3}")

        # Convert the WAV file to MP3 for upload
        sound = AudioSegment.from_wav(TEMP_AUDIO_WAV)
        sound.export(TEMP_AUDIO_MP3, format="mp3")

        logger.info("MP3 conversion successful.")
        return True

    except Exception as e:
        logger.error("Coqui-TTS API failed with an error.", exc_info=True)
        return False


def generate_metadata(text_blocks):
    """Generates metadata including duration and chapter markers from the MP3."""
    if not os.path.exists(TEMP_AUDIO_MP3):
        logger.info("MP3 file does not exist, skipping metadata generation.")
        return None

    logger.info("Generating metadata...")
    audio = AudioSegment.from_mp3(TEMP_AUDIO_MP3)
    total_duration_s = len(audio) / 1000.0
    total_chars = sum(len(block["text"]) for block in text_blocks)
    chapters = []
    cumulative_chars = 0

    for block in text_blocks:
        start_time = (
            (cumulative_chars / total_chars) * total_duration_s
            if total_chars > 0
            else 0
        )
        chapters.append({"title": block["title"], "start_time": int(start_time)})
        cumulative_chars += len(block["text"])

    metadata = {
        "title": f"Daily Digest for {datetime.datetime.now().strftime('%Y-%m-%d')}",
        "duration": int(total_duration_s),
        "chapters_json": json.dumps(chapters),
    }
    return metadata


def upload_audiobook(api_url, api_key, supabase_anon_key, metadata):
    """Uploads the MP3 and its metadata to the Web App API."""
    logger.info("Uploading audiobook to the web application...")
    headers = {"Authorization": f"Bearer {api_key}", "apikey": supabase_anon_key}
    url = f"{api_url}/api/v1/audiobooks"

    try:
        with open(TEMP_AUDIO_MP3, "rb") as audio_file:

            files = {
                "audio_file": (TEMP_AUDIO_MP3, audio_file, "audio/mpeg"),
                "metadata": (None, json.dumps(metadata), "application/json"),
            }

            response = requests.post(url, headers=headers, files=files, timeout=300)
        response.raise_for_status()
        logger.info("Upload successful.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error occurred while uploading audiobook to {url}: {e}")
        logger.error(f"Status Code: {e.response.status_code}")
        logger.error(f"Response Body: {e.response.text[:500]}...")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.error(
            f"A network error occurred while uploading audiobook to {url}: {e}"
        )
        sys.exit(1)


def cleanup():
    """Removes temporary files."""
    logger.info("Cleaning up temporary files...")
    for f in [TEMP_AUDIO_WAV, TEMP_AUDIO_MP3]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError as e:
            logger.error(f"Could not remove temporary file {f}: {e}")


# --- Main Execution Logic ---


def main():
    """Main execution function."""
    setup_logging()  # Initialize logging first

    parser = argparse.ArgumentParser(
        description="Generate and upload a daily audio digest from email newsletters."
    )
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    parser.add_argument(
        "--date",
        default=yesterday,
        help=f"The date to process emails for in YYYY-MM-DD format (default: {yesterday}).",
    )
    # Use parse_known_args to ignore args that might be passed by test runners
    args, _ = parser.parse_known_args()

    try:
        # 1. Load Configuration
        config = load_config()

        # 2. Initialize TTS Model (once)
        initialize_tts_model()

        # 3. Fetch Sources from Web App
        sources = fetch_sources(
            config["api_url"], config["api_key"], config["supabase_anon_key"]
        )
        if not sources:
            logger.info("No sources returned from API. Exiting.")
            return

        # 4. Authenticate with Google
        gmail_creds = authenticate_gmail(
            config["token_file"], config["credentials_file"]
        )
        gmail_service = build("gmail", "v1", credentials=gmail_creds)

        # 5. Process Emails
        full_text, text_blocks = process_emails(gmail_service, sources, args.date)
        if not full_text.strip():
            logger.info(f"No content generated for {args.date}. Exiting.")
            return

        # 6. Generate Audio with Coqui-TTS API
        if not generate_audio(full_text, config["reference_voice_file"]):
            logger.error("Audio generation failed. Halting process.")
            return

        # 7. Generate Metadata
        metadata = generate_metadata(text_blocks)
        if not metadata:
            logger.error("Could not generate metadata. Halting before upload.")
            return

        # 8. Upload to Web App
        upload_audiobook(
            config["api_url"], config["api_key"], config["supabase_anon_key"], metadata
        )

        logger.info(f"Audiobook for {args.date} generated and uploaded successfully.")

    except Exception:
        # Use logger.critical for top-level uncaught exceptions
        logger.critical(
            "An unexpected error occurred in the main process.", exc_info=True
        )
        sys.exit(1)
    finally:
        # 9. Cleanup
        cleanup()


if __name__ == "__main__":
    main()
