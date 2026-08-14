#!/usr/bin/env python3
"""
reauth_gmail.py

Standalone Google OAuth re-authorization for the audio digest pipeline.

Does exactly what `generate_audiobook.py --reauth` does — same SCOPES, same
InstalledAppFlow, same token.json output — but without importing the TTS stack
(numpy/soundfile/tqdm/torch) or requiring a config.ini. That makes it
runnable on a bare interpreter with only two dependencies:

    pip install google-auth-oauthlib google-api-python-client

Use this when the refresh token in GitHub Secrets has been revoked and the
daily workflow is failing with:

    google.auth.exceptions.RefreshError: invalid_grant: Token has been expired
    or revoked.

Requires a browser on this machine — the OAuth redirect lands on a loopback
port that Google must be able to reach.

Usage:
    python reauth_gmail.py
    python reauth_gmail.py --credentials path/to/credentials.json
    python reauth_gmail.py --print-token   # echo the new token to stdout
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Must stay in sync with generate_audiobook.py and
# research_papers/run_research_pipeline.py — a token minted with a narrower
# set will be rejected by whichever script asks for more.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CREDENTIALS_FILE = os.path.join(_SCRIPT_DIR, "credentials.json")
DEFAULT_TOKEN_FILE = os.path.join(_SCRIPT_DIR, "token.json")


def reauth(credentials_file: str, token_file: str, print_token: bool) -> int:
    if not os.path.exists(credentials_file):
        logger.error("Credentials file not found: %s", credentials_file)
        return 1

    # Move any existing token aside so the browser sign-in always runs rather
    # than silently reusing the old (possibly revoked) account credentials.
    # It is restored if the flow fails, so a failed re-auth never leaves the
    # machine with no credentials at all.
    backup = None
    if os.path.exists(token_file):
        backup = token_file + ".bak"
        logger.info("Setting existing token aside to force a fresh sign-in: %s", token_file)
        os.replace(token_file, backup)

    logger.info("Starting Google OAuth flow — a browser window will open...")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        creds = flow.run_local_server(port=0)
    except Exception:
        if backup:
            os.replace(backup, token_file)
            logger.error("OAuth flow failed; restored the previous token.")
        raise

    # 0600 — the file holds a long-lived refresh token for gmail.modify/send.
    fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(creds.to_json())
    logger.info("Fresh token written to: %s", token_file)
    if backup and os.path.exists(backup):
        os.remove(backup)

    try:
        profile = build("gmail", "v1", credentials=creds).users().getProfile(userId="me").execute()
        logger.info(
            "OK: Authentication successful. Connected Gmail account: %s",
            profile.get("emailAddress", "unknown"),
        )
    except HttpError as e:
        logger.warning("Token written, but could not fetch account profile: %s", e)

    if not creds.refresh_token:
        logger.warning(
            "No refresh_token in the response. The daily workflow needs one to run "
            "unattended. Revoke this app under Google Account > Security > "
            "Third-party apps and re-run to force a new consent grant."
        )

    if print_token:
        logger.warning(
            "Printing live credentials (refresh_token, client_secret) — do not "
            "run this with output captured, redirected, or logged."
        )
        with open(token_file) as fh:
            token_json = fh.read()
        print("\n" + "=" * 72)
        print("Copy everything between the lines into the GOOGLE_TOKEN_JSON secret:")
        print("=" * 72)
        print(json.dumps(json.loads(token_json), indent=2))
        print("=" * 72)

    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(
        description="Force a fresh Google OAuth flow and write a new token.json.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--credentials", default=DEFAULT_CREDENTIALS_FILE, help="OAuth client secrets file.")
    parser.add_argument("--token", default=DEFAULT_TOKEN_FILE, help="Where to write the resulting token.")
    parser.add_argument(
        "--print-token",
        action="store_true",
        help="Print the new token to stdout for pasting into the GOOGLE_TOKEN_JSON secret.",
    )
    args = parser.parse_args()

    return reauth(args.credentials, args.token, args.print_token)


if __name__ == "__main__":
    sys.exit(main())
