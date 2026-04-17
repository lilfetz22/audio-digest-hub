"""Transcript generator using Gemini (sequential realtime calls with rate limiting)."""

import logging
import random
import time
from pathlib import Path
from typing import List, Tuple

import httpx
from google import genai
from google.genai import errors as genai_errors
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

    FALLBACK_MODELS = [
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
    ]

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.1-flash-lite-preview",
        backup_api_key: str | None = None,
        paid_api_key: str | None = None,
        paid_model_name: str | None = None,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.backup_api_key = backup_api_key
        self.paid_api_key = paid_api_key
        self.paid_model_name = paid_model_name
        self._request_timestamps: List[float] = []
        self._token_usage: List[tuple] = []  # (timestamp, token_count)
        self._resolved_model: str | None = None
        self._resolved_client: genai.Client | None = None

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
        titles: List[str] = []
        client = genai.Client(api_key=self.api_key)
        if deep_dive_papers:
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
                titles.append(paper.title)

                # Log estimated token usage for the response as well
                estimated_output_tokens = len(transcript) // CHARS_PER_TOKEN
                total_tokens = estimated_input_tokens + estimated_output_tokens
                self._record_usage(total_tokens)

                logger.info(
                    f"Paper {i + 1}/{len(deep_dive_papers)} done "
                    f"(~{total_tokens:,} tokens estimated)"
                )

        # Append Interrogator Q&A episode from 5 randomly sampled transcripts
        interrogator_section = ""
        if deep_dive_transcripts:
            sample_size = min(5, len(deep_dive_transcripts))
            indices = random.sample(range(len(deep_dive_transcripts)), sample_size)
            sampled = [(titles[i], deep_dive_transcripts[i]) for i in indices]
            logger.info(
                f"Interrogator: sampling {sample_size} transcripts — "
                + ", ".join(f'"{t}"' for t, _ in sampled)
            )
            interrogator_section = self._generate_interrogator_episode(
                client, sampled, date_str
            )

        parts = [t.strip() for t in deep_dive_transcripts]
        if interrogator_section:
            parts.append(
                f"=== THE INTERROGATOR ===\n\n{interrogator_section.strip()}"
            )
        return "\n\n".join(parts)

    def _load_system_prompt(self) -> str:
        """Load the narrator system prompt."""
        prompt_path = PROMPTS_DIR / "narrator_system.txt"
        return prompt_path.read_text(encoding="utf-8")

    def _load_interrogator_system_prompt(self) -> str:
        """Load the Interrogator Q&A system prompt."""
        prompt_path = PROMPTS_DIR / "interrogator_qa_system.txt"
        return prompt_path.read_text(encoding="utf-8")

    def _generate_interrogator_episode(
        self,
        client: genai.Client,
        sampled: List[Tuple[str, str]],
        date_str: str,
    ) -> str:
        """Generate the Interrogator Q&A episode from 5 sampled transcripts.

        Args:
            client: Gemini client (already authenticated).
            sampled: List of (title, transcript) pairs.
            date_str: Date string for the episode.

        Returns:
            Interrogator episode text with 2 Q&A pairs per paper.
        """
        system_prompt = self._load_interrogator_system_prompt()

        parts = [f"Generate an Interrogator Q&A episode for {date_str}.\n"]
        for title, transcript in sampled:
            parts.append(f"=== {title} ===\n{transcript.strip()}\n")
        user_prompt = "\n".join(parts)

        estimated_input_tokens = (
            len(system_prompt) + len(user_prompt)
        ) // CHARS_PER_TOKEN
        self._wait_for_rate_limit(estimated_input_tokens)

        logger.info("Generating Interrogator episode...")
        result = self._generate_realtime(client, system_prompt, user_prompt)

        estimated_output_tokens = len(result) // CHARS_PER_TOKEN
        self._record_usage(estimated_input_tokens + estimated_output_tokens)

        logger.info("Interrogator episode complete")
        return result

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
        """Generate transcript using realtime API, with retries and model fallback.

        On the first call the full model chain is tried (10 retries each).
        Whichever model succeeds is locked in for all subsequent calls.
        If the locked-in model later fails, the full chain is re-entered.

        When a 429 quota-exhausted error is hit on a free-tier API key, the
        backup API key is tried with the same model chain before falling back
        to the paid key.
        """
        # If a model was already resolved, try it first; on failure reset and
        # fall through to the full fallback chain.
        if self._resolved_model is not None:
            try:
                return self._try_model(
                    self._resolved_client, self._resolved_model,
                    system_prompt, user_prompt,
                )
            except genai_errors.ClientError as e:
                if getattr(e, "code", None) == 429:
                    logger.warning(
                        f"Quota exhausted (429) for locked-in model "
                        f"{self._resolved_model}. Re-entering fallback chain..."
                    )
                else:
                    logger.warning(
                        f"Client error for locked-in model "
                        f"{self._resolved_model}: {e}. Re-entering fallback chain..."
                    )
                self._resolved_model = None
                self._resolved_client = None
            except (genai_errors.ServerError, httpx.ReadError, httpx.ConnectError,
                    httpx.RemoteProtocolError, ConnectionError, OSError):
                logger.warning(
                    f"Locked-in model {self._resolved_model} failed. "
                    f"Re-entering full fallback chain..."
                )
                self._resolved_model = None
                self._resolved_client = None

        free_models = [self.model_name] + [
            m for m in self.FALLBACK_MODELS if m != self.model_name
        ]

        # Build ordered list of (api_key, models_to_try) tiers
        api_key_tiers: List[Tuple[str, List[str]]] = [
            (self.api_key, free_models),
        ]
        if self.backup_api_key:
            api_key_tiers.append((self.backup_api_key, free_models))

        for tier_idx, (key, models) in enumerate(api_key_tiers):
            tier_client = genai.Client(api_key=key)
            key_label = "primary" if tier_idx == 0 else "backup"

            for model_idx, model in enumerate(models):
                try:
                    result = self._try_model(
                        tier_client, model, system_prompt, user_prompt
                    )
                    self._resolved_model = model
                    self._resolved_client = tier_client
                    logger.info(
                        f"Locked in model: {model} ({key_label} API key)"
                    )
                    return result
                except genai_errors.ClientError as e:
                    if getattr(e, "code", None) == 429:
                        logger.warning(
                            f"Quota exhausted (429) for {model} on "
                            f"{key_label} API key. "
                            f"Switching to next API key tier..."
                        )
                        break  # skip remaining models on this key
                    raise
                except (genai_errors.ServerError, httpx.ReadError,
                        httpx.ConnectError, httpx.RemoteProtocolError,
                        ConnectionError, OSError):
                    if model_idx < len(models) - 1:
                        next_model = models[model_idx + 1]
                        logger.warning(
                            f"All retries exhausted for {model}. "
                            f"Falling back to {next_model}..."
                        )
                    else:
                        logger.warning(
                            f"All retries exhausted for {model} "
                            f"(last free model on {key_label} key)."
                        )

        # Last resort: paid API key + paid model
        if self.paid_api_key and self.paid_model_name:
            logger.warning(
                f"All free models/keys failed. Falling back to paid model "
                f"{self.paid_model_name}..."
            )
            paid_client = genai.Client(api_key=self.paid_api_key)
            result = self._try_model(
                paid_client, self.paid_model_name, system_prompt, user_prompt
            )
            self._resolved_model = self.paid_model_name
            self._resolved_client = paid_client
            logger.info(f"Locked in paid model: {self.paid_model_name}")
            return result

        raise RuntimeError(
            "All free models/keys failed and no paid API key configured."
        )

    def _try_model(
        self,
        client: genai.Client,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Try generating with a single model, retrying up to 10 times with exponential backoff.

        Raises genai_errors.ClientError immediately on 429 (quota exhausted)
        so the caller can swap API keys without wasting retries.
        """
        max_retries = 10
        base_delay = 30  # seconds; doubles each attempt, capped at max_delay
        max_delay = 600  # 10 minutes

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7,
                    ),
                )
                return response.text
            except genai_errors.ClientError as e:
                # 429 quota exhausted — bubble up immediately for API key swap
                if getattr(e, "code", None) == 429:
                    raise
                raise
            except genai_errors.ServerError as e:
                is_retryable = getattr(e, "code", None) == 503
                if is_retryable and attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"Gemini API unavailable (503) for {model}. "
                        f"Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                else:
                    raise
            except (httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError, ConnectionError, OSError) as e:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"Network error for {model}: {e}. "
                        f"Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                else:
                    raise

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
