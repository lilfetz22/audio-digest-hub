# generate_audiobook.py
import numpy as np
import os
import sys
import argparse
import configparser
import datetime
import json
import base64
import re
import logging
import math
import subprocess
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
logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

TEMP_WAV_FILE = "temp_output.wav"
UPLOAD_MP3_BASENAME = "temp_output"

TTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
TTS_CLIENT = None
MAX_UPLOAD_SIZE_MB = 15.0

# NEW: Define a default speaker to use if no reference voice file is provided.
DEFAULT_SPEAKER = "Claribel Dervla"


# --- Core Functions (No changes in this section) ---


def setup_logging():
    """Configures the root logger for console and file output with UTF-8 encoding."""
    log_file = "audiobook_generator.log"
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.info("-" * 50)
    logger.info("Starting new run of audiobook generator.")
    logger.info(f"Logging initialized. Output will be saved to {log_file}")


def load_config(config_path="config.ini"):
    """Reads configuration from the INI file."""
    if not os.path.exists(config_path):
        logger.error(f"Configuration file '{config_path}' not found.")
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(config_path)
    try:
        return {
            "api_url": config["WebApp"]["API_URL"],
            "api_key": config["WebApp"]["API_KEY"],
            "credentials_file": config["Gmail"]["CREDENTIALS_FILE"],
            "token_file": config["Gmail"]["TOKEN_FILE"],
            "reference_voice_file": config.get(
                "TTS", "REFERENCE_VOICE_FILE", fallback=None
            ),
        }
    except KeyError as e:
        logger.error(f"Missing key in config.ini: {e}")
        sys.exit(1)


def verify_authentication(api_url, api_key):
    """
    Performs a pre-flight check to verify the API key is valid.
    Tries to fetch sources and exits gracefully if authentication fails.
    """
    logger.info("Performing pre-flight authentication check...")
    test_url = f"{api_url}/sources"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(test_url, headers=headers, timeout=15)

        if response.status_code == 200:
            logger.info("✅ Authentication successful.")
            return True

        elif response.status_code == 401:
            logger.critical("-" * 60)
            logger.critical("FATAL: AUTHENTICATION FAILED (401 Unauthorized).")
            logger.critical(
                "The API_KEY in your config.ini is incorrect, expired, or revoked."
            )
            logger.critical(
                "Please get a valid service_role key from your Supabase dashboard."
            )
            logger.critical("-" * 60)
            return False

        else:
            logger.error(
                f"Pre-flight check failed with unexpected status code: {response.status_code}"
            )
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(
            "A network error occurred during the pre-flight check.", exc_info=True
        )
        return False


def fetch_sources(api_url, api_key):
    """Fetches newsletter sources from the Supabase Edge Function."""
    logger.info("Fetching newsletter sources from Web App...")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{api_url}/sources"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"A network error occurred calling {url}", exc_info=True)
        sys.exit(1)


def upload_audiobook(api_url, api_key, filepath, metadata):
    """Uploads a single audio file and its metadata."""
    logger.info(f"Uploading '{filepath}' to the web application...")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{api_url}/audiobooks"
    try:
        with open(filepath, "rb") as audio_file:
            files = {
                "audio_file": (os.path.basename(filepath), audio_file, "audio/mpeg"),
                "metadata": (None, json.dumps(metadata), "application/json"),
            }
            response = requests.post(url, headers=headers, files=files, timeout=300)
            response.raise_for_status()
            logger.info(f"Upload successful. Server response: {response.json()}")
            return True
    except FileNotFoundError:
        logger.error(f"Upload failed: The file '{filepath}' was not found.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(
            f"A network/HTTP error occurred while uploading '{filepath}' to {url}",
            exc_info=True,
        )
        return False


def initialize_tts_model():
    """Loads the Coqui-TTS model into memory."""
    global TTS_CLIENT
    if TTS_CLIENT is None:
        logger.info(f"Loading Coqui-TTS model: {TTS_MODEL}")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")
            TTS_CLIENT = TTS(TTS_MODEL).to(device)
            logger.info("Coqui-TTS model loaded successfully.")
        except Exception:
            logger.error("Failed to load the TTS model.", exc_info=True)
            sys.exit(1)


def authenticate_gmail(token_file, credentials_file):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                logger.error(f"Credentials file '{credentials_file}' not found.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return creds


def remove_markdown_links(text):
    return re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)


def process_emails(service, sources, target_date_str):
    logger.info(f"Processing emails for date: {target_date_str}")
    sender_emails = [source["sender_email"] for source in sources]
    if not sender_emails:
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
        return "", []
    all_text_blocks = []
    sender_to_custom_name = {
        s["sender_email"].lower(): s["custom_name"] for s in sources
    }
    for msg_info in reversed(messages):
        msg = service.users().messages().get(userId="me", id=msg_info["id"]).execute()
        if "UNREAD" in msg.get("labelIds", []):
            try:
                subject = next(
                    (
                        h["value"]
                        for h in msg["payload"]["headers"]
                        if h["name"] == "Subject"
                    ),
                    "No Subject",
                )
                logger.info(
                    f"Marking email as read: '{subject[:50]}...' (ID: {msg_info['id']})"
                )
                service.users().messages().modify(
                    userId="me", id=msg_info["id"], body={"removeLabelIds": ["UNREAD"]}
                ).execute()
            except HttpError as e:
                logger.warning(
                    f"Could not mark email {msg_info['id']} as read. Error: {e}. Continuing."
                )
        headers = msg["payload"]["headers"]
        sender_email = next(
            (
                re.search(r"<(.+?)>", h["value"]).group(1).lower()
                for h in headers
                if h["name"] == "From" and re.search(r"<(.+?)>", h["value"])
            ),
            "",
        )
        custom_name = sender_to_custom_name.get(sender_email, "Unknown Source")
        body_text = ""
        try:
            if "parts" in msg["payload"]:
                part = next(
                    (
                        p
                        for p in msg["payload"]["parts"]
                        if p["mimeType"] in ["text/plain", "text/html"]
                    ),
                    None,
                )
                if part:
                    data = base64.urlsafe_b64decode(part["body"]["data"])
                    body_text = data.decode("utf-8", errors="replace")
                    if part["mimeType"] == "text/html":
                        body_text = re.sub("<[^<]+?>", "", body_text)
            else:
                data = base64.urlsafe_b64decode(msg["payload"]["body"]["data"])
                body_text = data.decode("utf-8", errors="replace")
            text_block = f"\n\nNewsletter from: {custom_name}.\n\n{body_text.strip()}"
            all_text_blocks.append({"text": text_block, "title": custom_name})
        except Exception:
            logger.error(f"Failed to parse email from {custom_name}", exc_info=True)
            all_text_blocks.append(
                {
                    "text": f"\n\n{custom_name} could not be processed.\n\n",
                    "title": f"{custom_name} (Error)",
                }
            )
    return "".join([b["text"] for b in all_text_blocks]), all_text_blocks


def validate_and_process_chunk(chunk, max_len=250):
    cleaned_chunk = re.sub(r"https?://\S+", "", chunk).strip()
    if not cleaned_chunk:
        return []
    if len(cleaned_chunk) <= max_len:
        return [cleaned_chunk]
    sub_chunks = []
    while len(cleaned_chunk) > max_len:
        split_pos = cleaned_chunk.rfind(" ", 0, max_len)
        if split_pos == -1:
            split_pos = max_len
        sub_chunks.append(cleaned_chunk[:split_pos])
        cleaned_chunk = cleaned_chunk[split_pos:].lstrip()
    sub_chunks.append(cleaned_chunk)
    return sub_chunks


def generate_and_upload_audio(text_content, text_blocks, config, date_str):
    """
    Generates audio, converts to MP3, and handles chunking/uploading.
    Returns a list of file paths created for cleanup.
    """
    if not text_content.strip():
        logger.info("No text content to synthesize. Skipping audio generation.")
        return []
    date_specific_basename = f"digest_{date_str}"

    logger.info(f"Using base filename: '{date_specific_basename}' for this run.")

    logger.info("Starting Coqui-TTS audio generation...")
    # Determine which voice to use: custom file or default speaker
    speaker_wav = (
        config.get("reference_voice_file")
        if config.get("reference_voice_file")
        and os.path.exists(config["reference_voice_file"])
        else None
    )

    tts_kwargs = {}
    if speaker_wav:
        logger.info(f"Using reference voice file for TTS: {speaker_wav}")
        tts_kwargs["speaker_wav"] = speaker_wav
    else:
        logger.info(
            f"Reference voice file not found or specified. Using default speaker: '{DEFAULT_SPEAKER}'"
        )
        tts_kwargs["speaker"] = DEFAULT_SPEAKER

    try:
        paragraphs = text_content.split("\n")
        initial_chunks = [
            c
            for p in paragraphs
            if p.strip()
            for c in TTS_CLIENT.synthesizer.split_into_sentences(p)
        ]
        final_chunks = [
            sc for chunk in initial_chunks for sc in validate_and_process_chunk(chunk)
        ]
        audio_chunks = []
        for i, sentence in enumerate(final_chunks):
            logger.info(
                f"Synthesizing chunk {i + 1}/{len(final_chunks)}: '{sentence[:80]}...'"
            )
            # Use the determined TTS arguments
            wav_chunk = TTS_CLIENT.tts(text=sentence, language="en", **tts_kwargs)
            audio_chunks.append(np.array(wav_chunk))

        if not audio_chunks:
            logger.warning("No audio generated, content may be empty after cleaning.")
            return []

        full_audio_np = np.concatenate(audio_chunks)
        TTS_CLIENT.synthesizer.save_wav(wav=full_audio_np, path=TEMP_WAV_FILE)
        logger.info(f"Full audio saved to temporary WAV: {TEMP_WAV_FILE}")

        full_audio_segment = AudioSegment.from_wav(TEMP_WAV_FILE)
        with open(TEMP_WAV_FILE, "rb") as f:
            mp3_data_size = len(AudioSegment.from_wav(f).export(format="mp3").read())
        mp3_size_mb = mp3_data_size / (1024 * 1024)
        logger.info(f"Estimated full MP3 size is {mp3_size_mb:.2f} MB.")

        files_to_cleanup = [TEMP_WAV_FILE]
        base_title = f"Daily Digest for {date_str}"
        if mp3_size_mb <= MAX_UPLOAD_SIZE_MB:
            logger.info("MP3 size is within the limit. Uploading as a single file.")
            filepath = f"{date_specific_basename}.mp3"
            full_audio_segment.export(filepath, format="mp3")
            files_to_cleanup.append(filepath)
            metadata = _create_metadata(base_title, full_audio_segment, text_blocks)
            if not upload_audiobook(
                config["api_url"], config["api_key"], filepath, metadata
            ):
                logger.error("Single file upload failed.")
        else:
            num_chunks = math.ceil(mp3_size_mb / MAX_UPLOAD_SIZE_MB)
            logger.warning(
                f"MP3 size exceeds {MAX_UPLOAD_SIZE_MB:.1f} MB. Splitting into {num_chunks} chunks."
            )
            chunk_duration_ms = math.ceil(len(full_audio_segment) / num_chunks)
            original_chapters = _create_chapter_list(
                len(full_audio_segment), text_blocks
            )
            for i in range(num_chunks):
                start_ms = i * chunk_duration_ms
                end_ms = min((i + 1) * chunk_duration_ms, len(full_audio_segment))
                audio_chunk = full_audio_segment[start_ms:end_ms]
                chunk_filepath = (
                    f"{date_specific_basename}_part_{i+1}_of_{num_chunks}.mp3"
                )
                logger.info(
                    f"Exporting chunk {i+1}: {chunk_filepath} ({start_ms}ms to {end_ms}ms)"
                )
                audio_chunk.export(chunk_filepath, format="mp3")
                files_to_cleanup.append(chunk_filepath)
                chunk_title = f"{base_title} (Part {i+1} of {num_chunks})"
                chunk_metadata = _create_metadata_for_chunk(
                    chunk_title, audio_chunk, original_chapters, start_ms
                )
                if not upload_audiobook(
                    config["api_url"], config["api_key"], chunk_filepath, chunk_metadata
                ):
                    logger.error(
                        f"Upload failed for chunk {i+1}. Stopping further uploads."
                    )
                    break

        return files_to_cleanup
    except Exception:
        logger.error(
            "An error occurred during audio generation or uploading.", exc_info=True
        )
        return [
            f
            for f in [TEMP_WAV_FILE, f"{UPLOAD_MP3_BASENAME}*.mp3"]
            if os.path.exists(f)
        ]


def _create_chapter_list(total_duration_ms, text_blocks):
    total_chars = sum(len(block["text"]) for block in text_blocks)
    chapters = []
    cumulative_chars = 0
    for block in text_blocks:
        start_time_ms = (
            (cumulative_chars / total_chars) * total_duration_ms
            if total_chars > 0
            else 0
        )
        chapters.append({"title": block["title"], "start_time_ms": start_time_ms})
        cumulative_chars += len(block["text"])
    return chapters


def _create_metadata(title, audio_segment, text_blocks):
    duration_s = len(audio_segment) / 1000.0
    chapters = _create_chapter_list(len(audio_segment), text_blocks)

    # --- CHANGED: Create a dictionary {title: start_time} instead of a list of objects ---
    # This creates the format {"Chapter Title": 123, "Another Title": 456}
    chapters_dict = {c["title"]: int(c["start_time_ms"] / 1000) for c in chapters}

    return {
        "title": title,
        "duration_seconds": int(duration_s),
        # --- CHANGED: Dump the new dictionary to JSON ---
        "chapters_json": json.dumps(chapters_dict),
    }


def _create_metadata_for_chunk(
    title, audio_chunk_segment, original_chapters, chunk_start_ms
):
    chunk_duration_s = len(audio_chunk_segment) / 1000.0
    chunk_end_ms = chunk_start_ms + len(audio_chunk_segment)
    chunk_chapters = []
    for chapter in original_chapters:
        if chunk_start_ms <= chapter["start_time_ms"] < chunk_end_ms:
            relative_start_time_s = int(
                (chapter["start_time_ms"] - chunk_start_ms) / 1000
            )
            # This part still creates a list of dicts temporarily, which is fine
            chunk_chapters.append(
                {"title": chapter["title"], "start_time": relative_start_time_s}
            )

    # This logic to ensure a chapter at time 0 is correct
    if chunk_chapters and chunk_chapters[0]["start_time"] != 0:
        first_title = chunk_chapters[0]["title"]
        if not any(c["start_time"] == 0 for c in chunk_chapters):
            chunk_chapters.insert(0, {"title": first_title, "start_time": 0})

    # --- CHANGED: Convert the list of chapter dicts to the required {title: start_time} format ---
    chapters_dict = {
        chapter["title"]: chapter["start_time"] for chapter in chunk_chapters
    }

    return {
        "title": title,
        "duration_seconds": int(chunk_duration_s),
        # --- CHANGED: Dump the final dictionary to JSON ---
        "chapters_json": json.dumps(chapters_dict),
    }


# In generate_audiobook.py


def cleanup(files_to_remove):
    """
    Cleans up temporary audio files based on their type.
    - Deletes .wav files.
    - Unpins .mp3 files from OneDrive (for testing).
    """
    if not files_to_remove:
        return
    logger.info("Cleaning up temporary files...")
    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                # Check the file extension to decide the action
                if file_path.lower().endswith(".wav"):
                    os.remove(file_path)
                    logger.info(f"Deleted temporary file: {file_path}")
                elif file_path.lower().endswith(".mp3"):
                    # For MP3s, unpin them instead of deleting
                    unpin_file_from_onedrive(Path(file_path))
                    # The unpin function has its own logging, so we don't need another message here.
                else:
                    logger.warning(
                        f"Skipping unknown file type during cleanup: {file_path}"
                    )
            else:
                logger.warning(
                    f"File not found for cleanup, already removed?: {file_path}"
                )
        except OSError as e:
            logger.error(f"Could not process temporary file {file_path}: {e}")


def unpin_file_from_onedrive(file_path: Path) -> None:
    """
    Executes the 'attrib' command to mark a file as 'cloud-only' in OneDrive.
    This unpins the file from the local device, freeing up space. This is a
    Windows-specific command.
    """
    # On non-Windows systems, this will fail gracefully.
    if sys.platform != "win32":
        # We can just delete the file on non-windows systems, or do nothing.
        # Here we'll just log and return.
        # logging.warning(f"Unpinning is a Windows-only feature. Skipping for {file_path}.")
        try:
            os.remove(file_path)
            logging.info(f"Deleted temporary MP3 file: {file_path}")
        except OSError as e:
            logging.error(f"Could not delete temporary MP3 file {file_path}: {e}")
        return

    try:
        # The '+U' attribute marks the file as not being fully present on the local machine.
        # The '-P' attribute removes the 'pinned' status, ensuring it can be dehydrated.
        subprocess.run(
            ["attrib", "+U", "-P", str(file_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        logging.info(f"Successfully unpinned '{file_path}' from local storage.")
    except FileNotFoundError:
        logging.error(
            "The 'attrib' command was not found. This function is intended for Windows."
        )
    except subprocess.CalledProcessError as e:
        logging.error(
            f"Failed to execute 'attrib' command for '{file_path}'.\n"
            f"Return code: {e.returncode}\n"
            f"Stderr: {e.stderr}"
        )


# --- Main Execution Logic ---


def main():
    """
    Main execution function.
    Processes emails for a single day or a date range and generates audiobooks.
    """
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Generate and upload a daily audio digest from emails.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--date", help="Process a single specific date (YYYY-MM-DD)."
    )
    date_group.add_argument(
        "--start-date",
        help="Process a date range starting from this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        help="The end of the date range (YYYY-MM-DD). Defaults to yesterday if --start-date is used.",
    )

    args = parser.parse_args()

    dates_to_process = []
    try:
        if args.date:
            # Single date mode
            process_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
            dates_to_process.append(process_date)
        else:
            # Range mode or default mode
            yesterday = datetime.date.today() - datetime.timedelta(days=1)
            end_date = (
                datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()
                if args.end_date
                else yesterday
            )
            start_date = (
                datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
                if args.start_date
                else end_date
            )

            if start_date > end_date:
                logger.error(
                    f"Error: Start date ({start_date}) cannot be after end date ({end_date})."
                )
                sys.exit(1)

            current_date = start_date
            while current_date <= end_date:
                dates_to_process.append(current_date)
                current_date += datetime.timedelta(days=1)

    except ValueError as e:
        logger.error(f"Error: Invalid date format. Please use YYYY-MM-DD. Details: {e}")
        sys.exit(1)

    if not dates_to_process:
        logger.info("No dates selected for processing. Exiting.")
        return

    logger.info(
        f"Will process the following date(s): {[d.strftime('%Y-%m-%d') for d in dates_to_process]}"
    )

    try:
        config = load_config()

        if not verify_authentication(config["api_url"], config["api_key"]):
            sys.exit(1)

        initialize_tts_model()
        sources = fetch_sources(config["api_url"], config["api_key"])

        if not sources:
            logger.info("No sources returned from API. Exiting.")
            return

        gmail_creds = authenticate_gmail(
            config["token_file"], config["credentials_file"]
        )
        gmail_service = build("gmail", "v1", credentials=gmail_creds)

        for process_date in dates_to_process:
            date_str = process_date.strftime("%Y-%m-%d")
            logger.info(f"--- Starting process for date: {date_str} ---")
            files_created = []

            try:
                full_text, text_blocks = process_emails(
                    gmail_service, sources, date_str
                )
                if not full_text.strip():
                    logger.info(f"No email content found for {date_str}. Skipping.")
                    continue

                cleaned_full_text = remove_markdown_links(full_text)
                for block in text_blocks:
                    block["text"] = remove_markdown_links(block["text"])

                files_created = generate_and_upload_audio(
                    cleaned_full_text, text_blocks, config, date_str
                )
                logger.info(f"Successfully completed process for {date_str}.")

            except Exception as e:
                logger.error(
                    f"An error occurred while processing {date_str}. Moving to next date.",
                    exc_info=True,
                )
            finally:
                # Cleanup files for the current date before starting the next
                cleanup(files_created)

    except Exception:
        logger.critical(
            "A fatal, non-recoverable error occurred in the main process.",
            exc_info=True,
        )
        sys.exit(1)
    finally:
        logger.info("All processing runs finished.")


if __name__ == "__main__":
    main()
