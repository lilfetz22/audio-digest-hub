# test_manual_upload.py
import os
import sys
import json
import configparser
import requests
import argparse
import time
from pydub import AudioSegment

# --- Configuration & Constants ---
CONFIG_FILE = "config.ini"


def load_config(config_path=CONFIG_FILE):
    """Reads configuration from the INI file."""
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
    """
    Uploads a single audio file and its metadata with a retry mechanism for server errors.
    (This function is a direct copy from the main script for accurate testing)
    """
    print(f"Preparing to upload '{filepath}' to the web application...")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{api_url}/audiobooks"

    max_retries = 5
    base_delay_seconds = 10  # The initial delay, doubles after each failure

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
                return True  # Success, so we exit the function

        except requests.exceptions.HTTPError as e:
            if 500 <= e.response.status_code < 600:
                print(
                    f"WARNING: Server error ({e.response.status_code}) on attempt {attempt + 1}."
                )
                if attempt < max_retries - 1:
                    delay = base_delay_seconds * (2**attempt)
                    print(f"Waiting for {delay} seconds before retrying.")
                    time.sleep(delay)
                continue  # Go to the next attempt
            else:
                print(f"ERROR: A non-retriable HTTP error occurred: {e}")
                return False  # Fail immediately for client errors

        except requests.exceptions.RequestException as e:
            print(f"WARNING: A network error occurred on attempt {attempt + 1}: {e}.")
            if attempt < max_retries - 1:
                delay = base_delay_seconds * (2**attempt)
                print(f"Waiting for {delay} seconds before retrying.")
                time.sleep(delay)
            continue  # Go to the next attempt

        except FileNotFoundError:
            print(f"ERROR: Upload failed: The file '{filepath}' was not found.")
            return False

    print(f"ERROR: Failed to upload '{filepath}' after {max_retries} attempts.")
    return False


def main():
    """Main execution function to upload a specific MP3 file."""
    parser = argparse.ArgumentParser(
        description="Manually upload an audiobook MP3 file with retry logic.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "mp3_filepath",
        help="The full path to the MP3 file you want to upload.",
    )
    args = parser.parse_args()

    mp3_file = args.mp3_filepath
    print(f"--- Starting Manual Audiobook Upload for: {mp3_file} ---")

    # 1. Verify the source MP3 file exists
    if not os.path.exists(mp3_file):
        print(f"ERROR: The source audio file '{mp3_file}' was not found.")
        sys.exit(1)

    # 2. Load API configuration
    config = load_config()
    print("Configuration loaded successfully.")

    # 3. Get audio duration and create metadata
    try:
        print("Reading audio file to generate metadata...")
        audio = AudioSegment.from_mp3(mp3_file)
        duration_s = len(audio) / 1000.0

        # Create metadata similar to the main script's format
        # The chapter format is a JSON string of a dictionary: {"Title": startTimeInSeconds}
        chapters_dict = {
            "Part Start": 0,
        }

        metadata = {
            "title": f"Manual Re-upload: {os.path.basename(mp3_file)}",
            "duration_seconds": int(duration_s),
            "chapters_json": json.dumps(chapters_dict),
        }
        print("Generated metadata for upload:")
        print(json.dumps(metadata, indent=2))

    except Exception as e:
        print(f"ERROR: Failed to read MP3 file and create metadata. Details: {e}")
        sys.exit(1)

    # 4. Attempt the upload using the resilient function
    success = upload_audiobook(config["api_url"], config["api_key"], mp3_file, metadata)

    # 5. Report final status
    if success:
        print("\n--- Test finished successfully! ---")
    else:
        print("\n--- Test failed. Please check the error messages above. ---")
        sys.exit(1)


if __name__ == "__main__":
    main()
