#!/usr/bin/env python3
"""
upload_mp3.py

Simple CLI to upload a local .mp3 file to the audiobooks API. If the file
is larger than the configured MAX_UPLOAD_SIZE_MB it will be split into parts
and each part uploaded separately.

Usage examples:
  python upload_mp3.py "C:\\path\\to\\my_audio.mp3"
"""
import argparse
import configparser
import json
import logging
import math
import os
import sys
import time
from pathlib import Path

from pydub import AudioSegment
import requests

# Local defaults (kept small and explicit so this script is lightweight)
CONFIG_FILE = ".\\src\\audiobooks\\config.ini"
ARCHIVE_FOLDER = "archive_mp3"
MAX_UPLOAD_SIZE_MB = 35.0


logger = logging.getLogger(__name__)


def load_config(config_path=CONFIG_FILE):
    if not os.path.exists(config_path):
        logger.error("Configuration file '%s' not found.", config_path)
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(config_path)
    try:
        return {
            "api_url": config["WebApp"]["API_URL"],
            "api_key": config["WebApp"]["API_KEY"],
        }
    except KeyError as e:
        logger.error("Missing key in %s: %s", config_path, e)
        sys.exit(1)


def upload_single_file(api_url, api_key, filepath, metadata):
    """Upload a single file with retry/backoff (copied & simplified from project).
    Returns True on success.
    """
    logger.info("Preparing to upload '%s' to the web application...", filepath)
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{api_url}/audiobooks"

    max_retries = 5
    base_delay_seconds = 10

    for attempt in range(max_retries):
        try:
            with open(filepath, "rb") as audio_file:
                files = {
                    "audio_file": (
                        os.path.basename(filepath),
                        audio_file,
                        "audio/mpeg",
                    ),
                    "metadata": (None, json.dumps(metadata), "application/json"),
                }

                logger.info("Attempt %s of %s: Uploading...", attempt + 1, max_retries)
                response = requests.post(url, headers=headers, files=files, timeout=300)
                response.raise_for_status()

                logger.info("Upload successful. Server response: %s", response.json())
                return True

        except requests.exceptions.HTTPError as e:
            if e.response is not None and 500 <= e.response.status_code < 600:
                logger.warning(
                    "Server error (%s) on attempt %s.",
                    e.response.status_code,
                    attempt + 1,
                )
                if attempt < max_retries - 1:
                    delay = base_delay_seconds * (2**attempt)
                    logger.info("Waiting for %s seconds before retrying.", delay)
                    time.sleep(delay)
                continue
            else:
                logger.error("A non-retriable HTTP error occurred: %s", e)
                try:
                    logger.error("Response body: %s", e.response.text)
                except Exception:
                    pass
                return False

        except requests.exceptions.RequestException as e:
            logger.warning(
                "A network error occurred on attempt %s: %s.", attempt + 1, e
            )
            if attempt < max_retries - 1:
                delay = base_delay_seconds * (2**attempt)
                logger.info("Waiting for %s seconds before retrying.", delay)
                time.sleep(delay)
            continue

        except FileNotFoundError:
            logger.error("Upload failed: The file '%s' was not found.", filepath)
            return False

    logger.error("Failed to upload '%s' after %s attempts.", filepath, max_retries)
    return False


def upload_audiobook(api_url, api_key, mp3_path, base_title=None, text_blocks=None):
    """Upload an audiobook, automatically handling chunking if file is too large.

    Args:
        api_url (str): The API URL for uploads
        api_key (str): The API key for authentication
        mp3_path (str or Path): Path to the MP3 file to upload
        base_title (str, optional): Title for the audiobook. If None, uses filename.
        text_blocks (list, optional): Blocks of text used to build chapter metadata.

    Returns:
        bool: True if upload(s) successful, False otherwise
    """
    mp3_path = Path(mp3_path)
    if not mp3_path.exists():
        logger.error("File not found: %s", mp3_path)
        return False

    # Prepare archive folder
    os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

    try:
        # Use file size on disk as quick heuristic
        file_size_mb = mp3_path.stat().st_size / (1024 * 1024)
        logger.info("Detected MP3 size: %.2f MB", file_size_mb)

        audio = AudioSegment.from_mp3(mp3_path)

        if base_title is None:
            base_title = f"Manual Upload: {mp3_path.name}"

        if file_size_mb <= MAX_UPLOAD_SIZE_MB:
            # Upload single file
            logger.info("File size is within the upload limit; uploading directly.")
            metadata = (
                _create_metadata(base_title, audio, text_blocks)
                if text_blocks
                else create_metadata(base_title, audio)
            )
            success = upload_single_file(api_url, api_key, str(mp3_path), metadata)
            if not success:
                logger.error("Upload failed.")
                return False
            logger.info("Done.")
            return True
        else:
            # Split and upload chunks
            return split_and_upload_chunks(
                api_url,
                api_key,
                mp3_path,
                audio,
                base_title,
                file_size_mb,
                text_blocks,
            )

    except Exception as e:
        logger.error("Unexpected error while processing file: %s", e)
        return False


def split_and_upload_chunks(
    api_url, api_key, mp3_path, audio, base_title, file_size_mb, text_blocks=None
):
    """Split audio into chunks and upload each chunk separately.
    Returns True if all chunks uploaded successfully, False otherwise.
    """
    num_chunks = math.ceil(file_size_mb / MAX_UPLOAD_SIZE_MB)
    logger.info(
        "File exceeds %.1f MB. Splitting into %s parts.", MAX_UPLOAD_SIZE_MB, num_chunks
    )
    chunk_duration_ms = math.ceil(len(audio) / num_chunks)

    for i in range(num_chunks):
        start_ms = i * chunk_duration_ms
        end_ms = min((i + 1) * chunk_duration_ms, len(audio))
        chunk = audio[start_ms:end_ms]
        chunk_filename = os.path.join(
            ARCHIVE_FOLDER, f"{mp3_path.stem}_part_{i+1}_of_{num_chunks}.mp3"
        )
        logger.info(
            "Exporting chunk %s: %s (%sms to %sms)",
            i + 1,
            chunk_filename,
            start_ms,
            end_ms,
        )
        chunk.export(chunk_filename, format="mp3")

        chunk_title = f"{base_title} (Part {i+1} of {num_chunks})"
        metadata = (
            _create_metadata(chunk_title, chunk, text_blocks)
            if text_blocks
            else create_metadata(chunk_title, chunk)
        )

        success = upload_single_file(api_url, api_key, chunk_filename, metadata)
        if not success:
            logger.error("Upload failed for chunk %s. Stopping further uploads.", i + 1)
            return False

    logger.info("All parts uploaded successfully.")
    return True


def create_metadata(title, audio_segment):
    duration_s = len(audio_segment) / 1000.0
    # Simple single-chapter metadata to make it playable in the web UI
    chapters_dict = {"Part Start": 0}
    return {
        "title": title,
        "duration_seconds": int(duration_s),
        "chapters_json": json.dumps(chapters_dict),
    }


def _create_chapter_list(total_duration_ms, text_blocks):
    """Create chapters with proportional start times based on text lengths."""
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
    """Create chapter-aware metadata for an audiobook."""
    duration_s = len(audio_segment) / 1000.0
    chapters = _create_chapter_list(len(audio_segment), text_blocks)

    chapters_dict = {c["title"]: int(c["start_time_ms"] / 1000) for c in chapters}

    return {
        "title": title,
        "duration_seconds": int(duration_s),
        "chapters_json": json.dumps(chapters_dict),
    }


def main():
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
    parser = argparse.ArgumentParser(
        description="Upload a local MP3 to the audiobooks API; splits by size when needed."
    )
    parser.add_argument(
        "mp3_filepath",
        help="Path to the MP3 file to upload. If the path contains spaces, quote it.",
    )
    args = parser.parse_args()

    mp3_path = Path(args.mp3_filepath).expanduser()
    if not mp3_path.exists():
        logger.error("File not found: %s", mp3_path)
        sys.exit(1)

    # Load config
    config = load_config()

    # Upload the audiobook (handles chunking automatically)
    success = upload_audiobook(config["api_url"], config["api_key"], mp3_path)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
