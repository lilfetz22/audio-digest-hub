# test_upload.py
import os
import sys
import json
import configparser
import requests
from pydub import AudioSegment

# --- Configuration & Constants ---
INPUT_WAV_FILE = "temp_output.wav"
UPLOAD_MP3_FILE = "temp_output.mp3"  # We will create and upload this
CONFIG_FILE = "config.ini"

# --- Replicated Functions from your original script ---


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


def upload_audiobook(api_url, api_key, metadata):
    print(f"Uploading '{UPLOAD_MP3_FILE}' to the web application...")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{api_url}/audiobooks"
    try:
        # IMPORTANT: Open and upload the MP3 file
        with open(UPLOAD_MP3_FILE, "rb") as audio_file:
            files = {
                # Ensure the filename and MIME type match the MP3 format
                "audio_file": (UPLOAD_MP3_FILE, audio_file, "audio/mpeg"),
                "metadata": (None, json.dumps(metadata), "application/json"),
            }
            response = requests.post(url, headers=headers, files=files, timeout=300)
            response.raise_for_status()
            print(f"Upload successful. Server response: {response.json()}")
            return True
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        return False


# --- Main Test Logic ---


def main():
    print("--- Starting Audiobook Upload Test (with MP3 conversion) ---")

    # 1. Verify the source WAV file exists
    if not os.path.exists(INPUT_WAV_FILE):
        print(f"ERROR: The source audio file '{INPUT_WAV_FILE}' was not found.")
        sys.exit(1)

    print(f"Found source audio file: {INPUT_WAV_FILE}")

    # 2. Convert WAV to MP3
    try:
        print("Converting WAV to MP3... (This requires ffmpeg)")
        audio = AudioSegment.from_wav(INPUT_WAV_FILE)
        audio.export(UPLOAD_MP3_FILE, format="mp3")
        mp3_size = os.path.getsize(UPLOAD_MP3_FILE) / (1024 * 1024)
        print(f"Successfully created '{UPLOAD_MP3_FILE}' (Size: {mp3_size:.2f} MB)")
    except Exception as e:
        print(f"ERROR: Failed to convert WAV to MP3. Is ffmpeg installed correctly?")
        print(f"Details: {e}")
        sys.exit(1)

    # 3. Load API configuration
    config = load_config()
    print("Configuration loaded successfully.")

    # 4. Create the mock metadata object
    print("Creating mock metadata for the upload...")
    total_duration_s = len(audio) / 1000.0
    chapters = [
        {"title": "Test Chapter 1: Introduction", "start_time": 0},
        {"title": "Test Chapter 2: Main Content", "start_time": 60},
    ]
    test_metadata = {
        "title": f"Manual MP3 Test - {os.path.basename(UPLOAD_MP3_FILE)}",
        "duration_seconds": int(total_duration_s),
        "chapters_json": json.dumps(chapters),
    }
    print("Generated metadata:")
    print(json.dumps(test_metadata, indent=2))

    # 5. Attempt the upload
    success = upload_audiobook(config["api_url"], config["api_key"], test_metadata)

    # 6. Cleanup the temporary MP3
    if os.path.exists(UPLOAD_MP3_FILE):
        os.remove(UPLOAD_MP3_FILE)
        print(f"Cleaned up temporary file: {UPLOAD_MP3_FILE}")

    if success:
        print("\n--- Test finished successfully! ---")
    else:
        print("\n--- Test failed. Please check the error messages above. ---")
        sys.exit(1)


if __name__ == "__main__":
    main()
