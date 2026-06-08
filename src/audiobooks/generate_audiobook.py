
import os
import sys
import logging
import webbrowser
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --- Configuration ---
# Define SCOPES for Gmail API access
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Setup basic logging configuration
log_file_path = os.path.join(os.getcwd(), "audiobook_generation.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout) # Also log to stdout
    ]
)
logger = logging.getLogger(__name__)

def authenticate_gmail(token_file, credentials_file):
    """Authenticates with Google Gmail API.
    Logs detailed steps and errors.
    """
    logger.info("Starting Gmail authentication process.")
    logger.info(f"Attempting to load token from: {token_file}")
    creds = None
    if os.path.exists(token_file):
        logger.info("Token file found. Attempting to load credentials.")
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            logger.info("Credentials loaded from token file.")
        except Exception as e:
            logger.error(f"Failed to load credentials from {token_file}: {e}")
            # If token file is corrupted or invalid, proceed to re-authentication
            creds = None

    # If credentials are not valid or not found, refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Credentials expired. Attempting to refresh token.")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully.")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                # Proceed to re-authentication if refresh fails
                creds = None
        # If still no valid credentials, initiate the authentication flow
        if not creds:
            logger.info("No valid credentials found or token refresh failed. Initiating new authentication flow.")
            if not os.path.exists(credentials_file):
                logger.error(f"Credentials file '{credentials_file}' not found.")
                # Fallback to search in current working directory
                credentials_file_fallback = os.path.join(os.getcwd(), "credentials.json")
                if os.path.exists(credentials_file_fallback):
                    logger.warning(f"Using credentials from current working directory: {credentials_file_fallback}")
                    credentials_file = credentials_file_fallback
                else:
                    logger.error("Credentials file not found in script directory or current working directory. Exiting.")
                    sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            try:
                # Attempt to use run_local_server first, which might work in some environments
                logger.info("Attempting local server authentication with open_browser=False...")
                creds = flow.run_local_server(port=8080, open_browser=False)
                logger.info("Local server authentication successful.")
            except webbrowser.Error:
                # This exception might still occur if run_local_server itself fails,
                # but the primary goal is to avoid calling run_console().
                logger.error(f"An error occurred during local server authentication setup: {e}")
                logger.error("Could not complete authentication. Please check your network configuration and ensure port 8080 is accessible.")
                sys.exit(1)
            except Exception as e:
                logger.error(f"An unexpected error occurred during authentication: {e}", exc_info=True)
                sys.exit(1)

        # Save credentials if a valid creds object was obtained
        if creds:
            logger.info(f"Saving authentication token to {token_file}")
            try:
                with open(token_file, "w") as token:
                    token.write(creds.to_json())
                logger.info("Token saved successfully.")
            except Exception as e:
                logger.error(f"Failed to save token to {token_file}: {e}")
        else:
            logger.error("Failed to obtain valid credentials after all attempts.")
            sys.exit(1)

    return creds


def generate_audio_from_file(input_file_path, output_file_path, engine_type="google"):
    """Generates audiobook from a text file.
    Includes detailed logging for process steps and errors.
    """
    logger.info(f"Starting audiobook generation process for: {input_file_path}")
    logger.info(f"Output file will be: {output_file_path}")
    logger.info(f"Using text-to-speech engine: {engine_type}")

    if not os.path.exists(input_file_path):
        logger.error(f"Input file not found at: {input_file_path}")
        raise FileNotFoundError(f"Input file not found: {input_file_path}")

    try:
        # Placeholder for actual text-to-speech logic
        # Example: Read content from input_file_path
        with open(input_file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        logger.info(f"Successfully read content from {input_file_path}. Content length: {len(text_content)} characters.")

        # Placeholder for TTS call - replace with actual TTS implementation
        # For demonstration, we'll just log that it would be called.
        # Example using a hypothetical tts_client:
        # tts_client = TTSClient(engine_type=engine_type)
        # audio_data = tts_client.synthesize(text_content)
        # with open(output_file_path, 'wb') as audio_file:
        #     audio_file.write(audio_data)

        # Simulate successful file writing
        logger.info(f"Simulating audio synthesis and writing to {output_file_path}.")
        with open(output_file_path, 'w') as f:
            f.write("Simulated audio content.")
        logger.info(f"Simulated audio content written to {output_file_path}.")

        logger.info(f"Audiobook generation for {input_file_path} completed successfully.")
        return output_file_path

    except FileNotFoundError:
        # Already logged in the check above, but good practice to catch explicitly
        raise
    except Exception as e:
        logger.error(f"An error occurred during audiobook generation from {input_file_path}: {e}", exc_info=True)
        # Re-raise the exception to be caught by the main handler
        raise


def main():
    """Main function to orchestrate audiobook generation.
    Handles authentication and calls the generation function.
    """
    logger.info("Starting the audiobook generation process via main function.")

    # --- Configuration ---
    # Define paths for token and credentials files
    # Uses current working directory for token file if not absolute
    token_file = os.path.join(os.getcwd(), "token.json")
    # Assumes credentials.json is relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_file = os.path.join(script_dir, "credentials.json")
    logger.info(f"Using token file path: {token_file}")
    logger.info(f"Attempting to use credentials file from: {credentials_file}")

    # --- Authentication ---
    creds = None
    try:
        creds = authenticate_gmail(token_file, credentials_file)
        logger.info("Gmail authentication successful.")
    except Exception as e:
        logger.error(f"Critical error: Failed to authenticate with Gmail. Please check credentials and token. Error: {e}", exc_info=True)
        sys.exit(1) # Exit if authentication fails

    # --- Audiobook Generation ---
    try:
        # --- !!! IMPORTANT: MODIFY THESE PATHS AS NEEDED !!! ---
        # Example usage: replace with actual file paths and desired output
        input_book_source_path = "example_input.txt" # Replace with the actual path to your text file
        final_audiobook_path = "my_audiobook.mp3"  # Replace with desired output file path

        logger.info(f"Book source path set to: {input_book_source_path}")
        logger.info(f"Target audiobook path set to: {final_audiobook_path}")

        # Check if input file exists before proceeding
        if not os.path.exists(input_book_source_path):
            logger.error(f"Input source file not found at '{input_book_source_path}'. Please ensure the path is correct and the file exists.")
            sys.exit(1)

        # Call the generation function
        generate_audio_from_file(input_book_source_path, final_audiobook_path)

        logger.info(f"Audiobook successfully generated at: {final_audiobook_path}")

    except FileNotFoundError as fnf_error:
        logger.error(f"Process stopped due to missing file: {fnf_error}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred during the audiobook generation phase: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Audiobook generation script finished execution.")


if __name__ == "__main__":
    main()
