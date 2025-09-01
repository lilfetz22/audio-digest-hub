#!/usr/bin/env python3
"""
upload_mp3.py

Simple CLI to upload a local .mp3 file to the audiobooks API. If the file
is larger than the configured MAX_UPLOAD_SIZE_MB it will be split into parts
and each part uploaded separately.

Usage examples:
  python upload_mp3.py "C:\\path\\to\\my_audio.mp3"
"""
import os
import sys
import json
import math
import time
import argparse
import configparser
from pathlib import Path
from pydub import AudioSegment
import requests

# Local defaults (kept small and explicit so this script is lightweight)
CONFIG_FILE = ".\\src\\audiobooks\\config.ini"
ARCHIVE_FOLDER = "archive_mp3"
MAX_UPLOAD_SIZE_MB = 15.0


def load_config(config_path=CONFIG_FILE):
    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file '{config_path}' not found.")
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(config_path)
    try:
        return {
            "api_url": config["WebApp"]["API_URL"],
            "api_key": config["WebApp"]["API_KEY"],
        }
    except KeyError as e:
        print(f"ERROR: Missing key in {config_path}: {e}")
        sys.exit(1)


def upload_audiobook(api_url, api_key, filepath, metadata):
    """Upload helper with retry/backoff (copied & simplified from project).
    Returns True on success.
    """
    print(f"Preparing to upload '{filepath}' to the web application...")
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

                print(f"Attempt {attempt + 1} of {max_retries}: Uploading...")
                response = requests.post(url, headers=headers, files=files, timeout=300)
                response.raise_for_status()

                print(f"Upload successful. Server response: {response.json()}")
                return True

        except requests.exceptions.HTTPError as e:
            if e.response is not None and 500 <= e.response.status_code < 600:
                print(
                    f"WARNING: Server error ({e.response.status_code}) on attempt {attempt + 1}."
                )
                if attempt < max_retries - 1:
                    delay = base_delay_seconds * (2**attempt)
                    print(f"Waiting for {delay} seconds before retrying.")
                    time.sleep(delay)
                continue
            else:
                print(f"ERROR: A non-retriable HTTP error occurred: {e}")
                try:
                    print("Response body:", e.response.text)
                except Exception:
                    pass
                return False

        except requests.exceptions.RequestException as e:
            print(f"WARNING: A network error occurred on attempt {attempt + 1}: {e}.")
            if attempt < max_retries - 1:
                delay = base_delay_seconds * (2**attempt)
                print(f"Waiting for {delay} seconds before retrying.")
                time.sleep(delay)
            continue

        except FileNotFoundError:
            print(f"ERROR: Upload failed: The file '{filepath}' was not found.")
            return False

    print(f"ERROR: Failed to upload '{filepath}' after {max_retries} attempts.")
    return False


def create_metadata(title, audio_segment):
    duration_s = len(audio_segment) / 1000.0
    # Simple single-chapter metadata to make it playable in the web UI
    chapters_dict = {"Part Start": 0}
    return {
        "title": title,
        "duration_seconds": int(duration_s),
        "chapters_json": json.dumps(chapters_dict),
    }


def main():
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
        print(f"ERROR: File not found: {mp3_path}")
        sys.exit(1)

    # Load config
    config = load_config()

    # Prepare archive folder
    os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

    try:
        # Use file size on disk as quick heuristic
        file_size_mb = mp3_path.stat().st_size / (1024 * 1024)
        print(f"Detected MP3 size: {file_size_mb:.2f} MB")

        audio = AudioSegment.from_mp3(mp3_path)

        base_title = f"Manual Upload: {mp3_path.name}"

        if file_size_mb <= MAX_UPLOAD_SIZE_MB:
            # Upload single file
            print("File size is within the upload limit; uploading directly.")
            metadata = create_metadata(base_title, audio)
            success = upload_audiobook(
                config["api_url"], config["api_key"], str(mp3_path), metadata
            )
            if not success:
                print("ERROR: Upload failed.")
                sys.exit(1)
            print("Done.")
            return

        # Need to split into chunks
        num_chunks = math.ceil(file_size_mb / MAX_UPLOAD_SIZE_MB)
        print(
            f"File exceeds {MAX_UPLOAD_SIZE_MB:.1f} MB. Splitting into {num_chunks} parts."
        )
        chunk_duration_ms = math.ceil(len(audio) / num_chunks)

        for i in range(num_chunks):
            start_ms = i * chunk_duration_ms
            end_ms = min((i + 1) * chunk_duration_ms, len(audio))
            chunk = audio[start_ms:end_ms]
            chunk_filename = os.path.join(
                ARCHIVE_FOLDER, f"{mp3_path.stem}_part_{i+1}_of_{num_chunks}.mp3"
            )
            print(
                f"Exporting chunk {i+1}: {chunk_filename} ({start_ms}ms to {end_ms}ms)"
            )
            chunk.export(chunk_filename, format="mp3")

            chunk_title = f"{base_title} (Part {i+1} of {num_chunks})"
            metadata = create_metadata(chunk_title, chunk)

            success = upload_audiobook(
                config["api_url"], config["api_key"], chunk_filename, metadata
            )
            if not success:
                print(
                    f"ERROR: Upload failed for chunk {i+1}. Stopping further uploads."
                )
                sys.exit(1)

        print("All parts uploaded successfully.")

    except Exception as e:
        print(f"ERROR: Unexpected error while processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
