"""Transcript generator using Gemini (sequential realtime calls with rate limiting)."""

import logging
import time
from pathlib import Path
from typing import List

from google import genai
from google.genai import types

from .interfaces import TranscriptGenerator
from .models import PaperContent

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Free-tier rate limits for gemini-3.1-flash-lite-preview
MAX_REQUESTS_PER_MINUTE = 15
MAX_TOKENS_PER_MINUTE = 1_000_000
# Rough chars-to-tokens ratio (1 token ≈ 4 chars is a conservative estimate)
CHARS_PER_TOKEN = 4


class GeminiTranscriptGenerator(TranscriptGenerator):
    """Generates podcast transcripts using Gemini.

    Each deep-dive paper is sent individually via sequential realtime API calls
    with rate limiting to stay within the free tier (15 RPM, 1M TPM).
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.1-flash-lite-preview",
    ):
        self.api_key = api_key
        self.model_name = model_name
        self._request_timestamps: List[float] = []
        self._token_usage: List[tuple] = []  # (timestamp, token_count)

    def generate(
        self,
        deep_dive_papers: List[PaperContent],
        date_str: str,
    ) -> str:
        """Generate a podcast transcript from deep-dive paper content.

        Each deep-dive paper gets its own sequential LLM call with rate
        limiting to stay within the free tier.

        Args:
            deep_dive_papers: Papers with full text for detailed narration.
            date_str: Date string for the digest.

        Returns:
            Complete transcript text.
        """
        system_prompt = self._load_system_prompt()

        deep_dive_transcripts: List[str] = []
        if deep_dive_papers:
            client = genai.Client(api_key=self.api_key)
            for i, paper in enumerate(deep_dive_papers):
                prompt = self._build_single_paper_prompt(paper, date_str)
                estimated_input_tokens = (
                    len(system_prompt) + len(prompt)
                ) // CHARS_PER_TOKEN

                self._wait_for_rate_limit(estimated_input_tokens)

                logger.info(
                    f"Generating transcript for paper {i + 1}/{len(deep_dive_papers)}: "
                    f"{paper.title}"
                )
                transcript = self._generate_realtime(
                    client, system_prompt, prompt
                )
                deep_dive_transcripts.append(transcript)

                # Log estimated token usage for the response as well
                estimated_output_tokens = len(transcript) // CHARS_PER_TOKEN
                total_tokens = estimated_input_tokens + estimated_output_tokens
                self._record_usage(total_tokens)

                logger.info(
                    f"Paper {i + 1}/{len(deep_dive_papers)} done "
                    f"(~{total_tokens:,} tokens estimated)"
                )

        return "\n\n".join(t.strip() for t in deep_dive_transcripts)

    def _load_system_prompt(self) -> str:
        """Load the narrator system prompt."""
        prompt_path = PROMPTS_DIR / "narrator_system.txt"
        return prompt_path.read_text(encoding="utf-8")

    def _build_single_paper_prompt(
        self, paper: PaperContent, date_str: str
    ) -> str:
        """Build a user prompt for a deep dive into a single paper."""
        sections = [
            f"Generate a deep-dive research digest segment for {date_str}.\n",
            f"--- Paper: {paper.title} ---",
            f"Source: {paper.source}",
            f"URL: {paper.url}",
            f"Abstract: {paper.abstract}",
            f"Full Text:\n{paper.full_text}\n",
        ]
        return "\n".join(sections)

    def _generate_realtime(
        self, client: genai.Client, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate transcript using realtime API."""
        response = client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            ),
        )
        return response.text

    def _wait_for_rate_limit(self, estimated_tokens: int) -> None:
        """Block until sending another request would stay within free-tier limits."""
        now = time.time()
        window_start = now - 60

        # Prune old entries outside the 1-minute window
        self._request_timestamps = [
            t for t in self._request_timestamps if t > window_start
        ]
        self._token_usage = [
            (t, c) for t, c in self._token_usage if t > window_start
        ]

        # Check request count limit
        while len(self._request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
            oldest = self._request_timestamps[0]
            wait_time = oldest - window_start
            logger.info(
                f"Rate limit: {len(self._request_timestamps)} requests in last 60s, "
                f"waiting {wait_time:.1f}s..."
            )
            time.sleep(wait_time + 0.1)
            now = time.time()
            window_start = now - 60
            self._request_timestamps = [
                t for t in self._request_timestamps if t > window_start
            ]
            self._token_usage = [
                (t, c) for t, c in self._token_usage if t > window_start
            ]

        # Check token count limit
        tokens_in_window = sum(c for _, c in self._token_usage)
        while tokens_in_window + estimated_tokens > MAX_TOKENS_PER_MINUTE:
            oldest_ts = self._token_usage[0][0]
            wait_time = oldest_ts - window_start
            logger.info(
                f"Rate limit: ~{tokens_in_window:,} tokens in last 60s, "
                f"waiting {wait_time:.1f}s..."
            )
            time.sleep(wait_time + 0.1)
            now = time.time()
            window_start = now - 60
            self._token_usage = [
                (t, c) for t, c in self._token_usage if t > window_start
            ]
            tokens_in_window = sum(c for _, c in self._token_usage)

        # Record this request's timestamp
        self._request_timestamps.append(time.time())

    def _record_usage(self, token_count: int) -> None:
        """Record token usage for rate limiting."""
        self._token_usage.append((time.time(), token_count))
