"""Small shared HTTP helpers for the pipeline's calls to the Supabase edge
functions.

Extracted from generate_audiobook.py so date_range.py can make the same
retrying GET without either module importing the other (generate_audiobook
pulls in Kokoro/torch at import time, which is far too heavy for anything
that just wants to call an API).
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)


def requests_get_with_retry(url, headers, timeout=30, max_retries=3, backoff_base=2):
    """Performs a GET request with exponential-backoff retries on transient network errors."""
    if max_retries < 1:
        raise ValueError(f"max_retries must be >= 1, got {max_retries}")
    for attempt in range(max_retries):
        try:
            with requests.Session() as session:
                response = session.get(url, headers=headers, timeout=timeout)
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            if attempt < max_retries - 1:
                wait = backoff_base ** attempt
                logger.warning(
                    f"Transient network error on attempt {attempt + 1}/{max_retries}: {exc}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                raise
