# generate_audiobook.py

### Document 2: Specification for the Local Processor Application (API Version) ###

# Project Title: Daily Digest Audio - Local Processor
#
# 1.0 Project Vision
# To create a Python script that runs on a user's local machine. Its purpose is to
# automate the process of fetching specific email newsletters from a Gmail account,
# converting their content into a single MP3 audiobook using the Coqui-TTS Python API,
# and uploading the final file to a remote web application. The script must be
# non-interactive and suitable for execution via a scheduled task (cron job).
#
# 2.0 Core Functions
# *   Configuration Retrieval: Fetch the list of target newsletter senders from the Web App API.
# *   Email Processing: Fetch and parse the full text of emails from specified senders.
# *   TTS Generation: Use the Coqui-TTS Python API to convert aggregated text into a high-quality audio file.
# *   Metadata Generation: Create chapter markers and calculate the total duration.
# *   Secure Upload: Upload the final MP3 and its metadata to the remote Web App API.
#
# 3.0 Detailed Functional Specification
#
# 3.1 Setup and Configuration
# *   The application will be a Python script (`generate_audiobook.py`).
# *   It requires a `config.ini` file in the same directory:
#     ```ini
#     [WebApp]
#     API_URL = https://your-webapp-url.com
#     API_KEY = your_super_secret_api_key_from_the_webapp
#
#     [Gmail]
#     CREDENTIALS_FILE = credentials.json
#     TOKEN_FILE = token.json
#
#     [TTS]
#     # Optional: Path to a 6-15 second WAV file for voice cloning.
#     # If blank or file not found, a default voice will be used.
#     REFERENCE_VOICE_FILE = path/to/your/reference_voice.wav
#     ```
# *   The user is responsible for installing Python 3.9+, all required libraries,
#     and Coqui-TTS with PyTorch.
#
# 3.2 Google Authentication (First-Time Run)
# *   The script implements the Google API "Installed App" OAuth flow.
# *   If `token.json` is missing or invalid, it will guide the user through a
#     browser-based authentication and save the new token.
#
# 3.3 Script Execution Logic
# The script will be executable from the command line, e.g., `python generate_audiobook.py`.
#
# 1.  Argument Parsing: Use `argparse` for an optional `--date YYYY-MM-DD` argument.
# 2.  Load Configuration: Read API settings and TTS configuration from `config.ini`.
# 3.  Initialize TTS Model: Load the Coqui-TTS model into memory once at the start.
# 4.  Fetch Sources: GET the list of newsletter sources from the Web App API.
# 5.  Authenticate with Google: Initialize the Gmail API service.
# 6.  Process Emails: Fetch, parse, and concatenate email content into a single text string.
# 7.  Generate Audio with Coqui-TTS API:
#     *   Directly call the `TTS.api` function with the concatenated text.
#     *   Use the `tts_models/multilingual/multi-dataset/xtts_v2` model.
#     *   If a `REFERENCE_VOICE_FILE` is provided and valid, use it for voice cloning.
#     *   Save the output to a temporary WAV file (e.g., `temp_output.wav`).
#     *   Convert the WAV file to MP3 format (e.g., `temp_output.mp3`) using `pydub`.
# 8.  Generate Metadata: Calculate total duration and chapter timestamps from the MP3 file.
# 9.  Upload to Web App: POST the `temp_output.mp3` file and metadata to the Web App API.
# 10. Cleanup: Delete all temporary audio files (`.wav` and `.mp3`).
# 11. Console Output: Log progress and provide clear success or error messages.
#
# 4.0 Technical Stack & Libraries
# *   Language: Python 3.9+
# *   Required Libraries:
#     *   `TTS` (from Coqui-TTS)
#     *   `torch`
#     *   `requests`
#     *   `google-api-python-client`
#     *   `google-auth-oauthlib`
#     *   `pydub`

import os
import sys
import argparse
import configparser
import datetime
import json
import base64
import re
from pathlib import Path

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


def log_info(message):
    """Prints an informational message to stdout."""
    print(f"INFO: {message}")


def log_error(message):
    """Prints an error message to stderr."""
    print(f"ERROR: {message}", file=sys.stderr)


# --- Core Functions ---


def load_config(config_path="config.ini"):
    """Reads configuration from the INI file."""
    if not os.path.exists(config_path):
        log_error(f"Configuration file '{config_path}' not found.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        app_config = {
            "api_url": config["WebApp"]["API_URL"],
            "api_key": config["WebApp"]["API_KEY"],
            "credentials_file": config["Gmail"]["CREDENTIALS_FILE"],
            "token_file": config["Gmail"]["TOKEN_FILE"],
            # Optional TTS setting for voice cloning
            "reference_voice_file": config.get(
                "TTS", "REFERENCE_VOICE_FILE", fallback=None
            ),
        }
        return app_config
    except KeyError as e:
        log_error(f"Missing key in config.ini: {e}")
        sys.exit(1)


def initialize_tts_model():
    """Loads the Coqui-TTS model into memory."""
    global TTS_CLIENT
    if TTS_CLIENT is None:
        log_info(f"Loading Coqui-TTS model: {TTS_MODEL}")
        log_info("This may take a moment and require significant RAM...")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            log_info(f"Using device: {device}")
            TTS_CLIENT = TTS(TTS_MODEL).to(device)
            log_info("Coqui-TTS model loaded successfully.")
        except Exception as e:
            log_error(f"Failed to load the TTS model: {e}")
            log_error("Please ensure Coqui-TTS and PyTorch are installed correctly.")
            sys.exit(1)


def authenticate_gmail(token_file, credentials_file):
    """Handles Google OAuth2 flow and returns API credentials."""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log_info("Refreshing expired Gmail token...")
            creds.refresh(Request())
        else:
            log_info("Performing first-time Google authentication...")
            if not os.path.exists(credentials_file):
                log_error(f"Gmail credentials file ('{credentials_file}') not found.")
                log_error("Please get it from Google Cloud Console and place it here.")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())
            log_info(f"Gmail token saved to '{token_file}'.")

    return creds


def fetch_sources(api_url, api_key):
    """Fetches the list of newsletter sources from the Web App API."""
    log_info("Fetching newsletter sources from Web App...")
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(f"{api_url}/api/v1/sources", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log_error(f"Failed to fetch sources from API: {e}")
        sys.exit(1)


def process_emails(service, sources, target_date_str):
    """Fetches and processes emails from Gmail for a given date and source list."""
    log_info(f"Processing emails for date: {target_date_str}")

    sender_emails = [source["sender_email"] for source in sources]
    if not sender_emails:
        log_info("No sources configured. Nothing to process.")
        return "", []

    sender_query = " OR ".join([f"from:{email}" for email in sender_emails])
    target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
    after_date = target_date.strftime("%Y/%m/%d")
    before_date = (target_date + datetime.timedelta(days=1)).strftime("%Y/%m/%d")

    query = f"({sender_query}) after:{after_date} before:{before_date}"
    log_info(f"Using Gmail query: {query}")

    try:
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
    except HttpError as error:
        log_error(f"An error occurred fetching emails: {error}")
        return "", []

    if not messages:
        log_info("No matching emails found for the specified date and senders.")
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
            else:
                data = payload["body"]["data"]
                body_text = base64.urlsafe_b64decode(data).decode("utf-8")

            text_block = f"\n\nNewsletter from: {custom_name}. Received on: {received_date_str}.\n\n{body_text.strip()}"
            all_text_blocks.append({"text": text_block, "title": custom_name})

        except Exception as e:
            log_error(f"Failed to parse email from {custom_name}: {e}")
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
        log_info("No text content to synthesize. Skipping audio generation.")
        return False

    log_info("Starting Coqui-TTS audio generation using Python API...")

    # Check if a valid reference voice file is provided for cloning
    speaker_wav = None
    if reference_voice_path and os.path.exists(reference_voice_path):
        log_info(f"Using reference voice: {reference_voice_path}")
        speaker_wav = reference_voice_path
    else:
        log_info("No valid reference voice found. Using the model's default voice.")

    try:
        # Generate speech to a WAV file (default for the API)
        TTS_CLIENT.tts_to_file(
            text=text_content,
            speaker_wav=speaker_wav,
            language="en",
            file_path=TEMP_AUDIO_WAV,
            speed=1.0,
        )

        log_info(f"WAV file generated successfully: {TEMP_AUDIO_WAV}")
        log_info(f"Converting WAV to MP3: {TEMP_AUDIO_MP3}")

        # Convert the WAV file to MP3 for upload
        sound = AudioSegment.from_wav(TEMP_AUDIO_WAV)
        sound.export(TEMP_AUDIO_MP3, format="mp3")

        log_info("MP3 conversion successful.")
        return True

    except Exception as e:
        log_error(f"Coqui-TTS API failed with an error: {e}")
        return False


def generate_metadata(text_blocks):
    """Generates metadata including duration and chapter markers from the MP3."""
    if not os.path.exists(TEMP_AUDIO_MP3):
        log_info("MP3 file does not exist, skipping metadata generation.")
        return None

    log_info("Generating metadata...")
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


def upload_audiobook(api_url, api_key, metadata):
    """Uploads the MP3 and its metadata to the Web App API."""
    log_info("Uploading audiobook to the web application...")
    headers = {"Authorization": f"Bearer {api_key}"}

    files = {
        "audio_file": (TEMP_AUDIO_MP3, open(TEMP_AUDIO_MP3, "rb"), "audio/mpeg"),
        "metadata": (None, json.dumps(metadata), "application/json"),
    }

    try:
        response = requests.post(
            f"{api_url}/api/v1/audiobooks", headers=headers, files=files
        )
        response.raise_for_status()
        log_info("Upload successful.")
    except requests.exceptions.RequestException as e:
        log_error(f"Failed to upload audiobook: {e}")
        if hasattr(e, "response") and e.response is not None:
            log_error(f"Response body: {e.response.text}")
        sys.exit(1)


def cleanup():
    """Removes temporary files."""
    log_info("Cleaning up temporary files...")
    for f in [TEMP_AUDIO_WAV, TEMP_AUDIO_MP3]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError as e:
            log_error(f"Could not remove temporary file {f}: {e}")


# --- Main Execution Logic ---


def main():
    """Main execution function."""
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
    # Use parse_known_args to ignore args that might be passed by test runners like pytest
    args, _ = parser.parse_known_args()

    try:
        # 1. Load Configuration
        config = load_config()

        # 2. Initialize TTS Model (once)
        initialize_tts_model()

        # 3. Fetch Sources from Web App
        sources = fetch_sources(config["api_url"], config["api_key"])
        if not sources:
            log_info("No sources returned from API. Exiting.")
            return

        # 4. Authenticate with Google
        gmail_creds = authenticate_gmail(
            config["token_file"], config["credentials_file"]
        )
        gmail_service = build("gmail", "v1", credentials=gmail_creds)

        # 5. Process Emails
        full_text, text_blocks = process_emails(gmail_service, sources, args.date)
        if not full_text.strip():
            log_info(f"No content generated for {args.date}. Exiting.")
            return

        # 6. Generate Audio with Coqui-TTS API
        if not generate_audio(full_text, config["reference_voice_file"]):
            log_error("Audio generation failed. Halting process.")
            return

        # 7. Generate Metadata
        metadata = generate_metadata(text_blocks)
        if not metadata:
            log_error("Could not generate metadata. Halting before upload.")
            return

        # 8. Upload to Web App
        upload_audiobook(config["api_url"], config["api_key"], metadata)

        log_info(f"Audiobook for {args.date} generated and uploaded successfully.")

    except Exception as e:
        log_error(f"An unexpected error occurred in the main process: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # 9. Cleanup
        cleanup()


if __name__ == "__main__":
    main()
