#!/usr/bin/env python3
"""
tts_on_demand.py

Runner for pasted-text TTS jobs. Started by .github/workflows/tts-on-demand.yml
with a job id. It fetches the text from the tts-jobs API, synthesizes it with
the same Kokoro pipeline the daily digest uses, reports progress back to the
API as it goes, and uploads the MP3 to /audiobooks so it appears in the library.

Progress mapping: synthesis fills 0-90%, the upload fills 90-100%.

Usage:
    python tts_on_demand.py --job-id <uuid>
"""
import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

import requests

from generate_tts_audio import generate_audio_from_text
from http_utils import requests_get_with_retry
from upload_mp3 import load_config, upload_audiobook

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")

# Share of the bar given to synthesis; the remainder belongs to the upload.
SYNTH_PERCENT_SHARE = 90
FALLBACK_TITLE_CHARS = 60

logger = logging.getLogger(__name__)


def map_synthesis_percent(done, total):
    """Scale chunk progress into the synthesis share of the bar."""
    if total <= 0:
        return 0
    return int(done * SYNTH_PERCENT_SHARE / total)


def fallback_title(text):
    """Title for a job submitted without one: the start of the text."""
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if len(first_line) <= FALLBACK_TITLE_CHARS:
        return first_line or "Pasted text"
    return first_line[:FALLBACK_TITLE_CHARS].rstrip() + "..."


class ProgressReporter:
    """Sends status updates to the tts-jobs API.

    Percent only moves forward. The worker-pool fallback restarts synthesis
    from zero, and without this clamp the bar would jump backwards.

    Intermediate updates are best-effort: a dropped one just means the page
    shows a slightly stale number. Terminal updates ("done"/"failed") are
    retried, because a lost "done" would leave the page spinning forever.
    """

    def __init__(self, api_url, api_key, job_id):
        self._url = f"{api_url}/tts-jobs/{job_id}"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._last_percent = 0

    def _patch(self, body):
        response = requests.patch(self._url, headers=self._headers, json=body, timeout=30)
        response.raise_for_status()

    def update(self, status, percent=None):
        body = {"status": status}
        if percent is not None:
            self._last_percent = max(percent, self._last_percent)
            body["percent"] = self._last_percent
        try:
            self._patch(body)
        except requests.RequestException as exc:
            logger.warning("Could not report status '%s' (ignored): %s", status, exc)

    def finish(self, status, percent=None, error=None):
        body = {"status": status}
        if percent is not None:
            body["percent"] = max(percent, self._last_percent)
        if error is not None:
            body["error"] = error[:500]
        last_exc = None
        for attempt in range(3):
            try:
                self._patch(body)
                return
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning("Terminal status report failed (attempt %d): %s", attempt + 1, exc)
        raise RuntimeError(f"Could not record final status '{status}': {last_exc}")


def fetch_job_input(api_url, api_key, job_id):
    """Return (title_or_None, text) for the job. The API checks that the job
    belongs to the same user as the API key."""
    response = requests_get_with_retry(
        f"{api_url}/tts-jobs/{job_id}/input",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    response.raise_for_status()
    body = response.json()
    return body.get("title") or None, body["text"]


def run_job(job_id):
    config = load_config(CONFIG_PATH)
    api_url, api_key = config["api_url"], config["api_key"]
    reporter = ProgressReporter(api_url, api_key, job_id)

    reporter.update("starting", 0)
    try:
        try:
            title, text = fetch_job_input(api_url, api_key, job_id)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 409:
                logger.info("Job %s already finished; nothing to do.", job_id)
                return 0
            raise
        title = title or fallback_title(text)
        logger.info("Job %s: '%s' (%d chars)", job_id, title, len(text))

        def on_progress(done, total):
            reporter.update("synthesizing", map_synthesis_percent(done, total))

        with tempfile.TemporaryDirectory() as tmp_dir:
            mp3_path = Path(tmp_dir) / f"tts_{job_id}.mp3"
            reporter.update("synthesizing", 0)
            generate_audio_from_text(text, mp3_path, progress_callback=on_progress)

            reporter.update("uploading", SYNTH_PERCENT_SHARE)
            if not upload_audiobook(api_url, api_key, mp3_path, base_title=title):
                raise RuntimeError("Upload to the audiobooks API failed")

        reporter.finish("done", 100)
        logger.info("Job %s complete.", job_id)
        return 0
    except Exception as exc:  # noqa: BLE001 — every failure must reach the job row
        logger.exception("Job %s failed", job_id)
        try:
            reporter.finish("failed", error=f"{type(exc).__name__}: {exc}")
        except RuntimeError as report_exc:
            logger.error("Could not record failure: %s", report_exc)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize one pasted-text TTS job.")
    parser.add_argument("--job-id", required=True, help="tts_jobs row id")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    return run_job(args.job_id)


if __name__ == "__main__":
    sys.exit(main())
