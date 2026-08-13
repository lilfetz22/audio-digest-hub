"""Shared Gemini LLM client with multi-tier model/key fallback.

Both GeminiTranscriptGenerator and WikiIngestionEngine use this class so that
quota exhaustion, transient errors, and model unavailability are handled
consistently in one place.

Fallback order:
  1. Primary API key  – preferred model, then FALLBACK_MODELS in order
  2. Backup API key   – same model chain (skipped if not configured)
  3. OpenRouter       – final fallback for any Gemini failure (skipped if
                        not configured)

When ``openrouter_only`` is set, the Gemini tiers are bypassed entirely and
OpenRouter becomes the single option (used by the wiki ingestion engine).

Within each model attempt, up to 4 retries with exponential back-off are
made for retryable server/network errors. Any Gemini failure that exhausts
the API-key tiers falls through to OpenRouter as a last resort.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Tuple

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)


def _parse_retry_after(value: str) -> float | None:
    """Parse a Retry-After header value into seconds to wait.

    Supports both delta-seconds (e.g. "12") and HTTP-date
    (e.g. "Wed, 21 Oct 2015 07:28:00 GMT") forms. Returns None if
    ``value`` is absent, empty, or unparseable.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    try:
        # Servers (and proxies) can emit negative values; never hand a
        # negative delay to time.sleep().
        return max(float(int(value)), 0.0)
    except ValueError:
        pass
    try:
        retry_date = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_date.tzinfo is None:
        retry_date = retry_date.replace(tzinfo=timezone.utc)
    return max((retry_date - datetime.now(timezone.utc)).total_seconds(), 0.0)


class GeminiClientWithFallback:
    """Gemini client that walks through API-key and model tiers on failure."""

    FALLBACK_MODELS: List[str] = [
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
    ]

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.1-flash-lite",
        backup_api_key: str | None = None,
        openrouter_api_key: str | None = None,
        openrouter_model: str | None = None,
        openrouter_only: bool = False,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.backup_api_key = backup_api_key
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_model = openrouter_model
        self.openrouter_only = openrouter_only
        # Stored as one tuple so concurrent callers can never observe a
        # half-updated client/model combination.
        self._resolved: Tuple[genai.Client, str] | None = None
        self._resolve_lock = threading.RLock()

    def generate(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        response_format: dict | None = None,
    ) -> str:
        """Generate content with full fallback chain.

        On the first call every tier is tried in order.  Whichever
        (client, model) succeeds is "locked in" for subsequent calls,
        so we avoid re-running the full chain on every request.  If the
        locked-in combination later fails the full chain is re-entered.
        Safe to call from multiple threads.

        Args:
            user_prompt: The user/content part of the prompt.
            system_prompt: Optional system instruction.
            response_format: Optional OpenAI-style ``response_format`` (e.g. a
                ``{"type": "json_schema", ...}`` structured-output spec).  Only
                applied on the OpenRouter path; ignored by the Gemini tiers.

        Returns:
            Generated text.

        Raises:
            RuntimeError: When all tiers are exhausted.
        """
        # OpenRouter-only mode: bypass the Gemini tiers entirely.
        if self.openrouter_only:
            if not (self.openrouter_api_key and self.openrouter_model):
                raise RuntimeError(
                    "openrouter_only is set but OpenRouter API key/model "
                    "are not configured."
                )
            return self._try_openrouter(system_prompt, user_prompt, response_format)

        resolved = self._resolved
        if resolved is not None:
            result = self._try_resolved(resolved, system_prompt, user_prompt)
            if result is not None:
                return result

        # Only one thread walks the tier chain at a time; the rest wait and
        # then reuse whatever combination the winner locked in.
        with self._resolve_lock:
            resolved = self._resolved
            if resolved is not None:
                result = self._try_resolved(resolved, system_prompt, user_prompt)
                if result is not None:
                    return result
            return self._walk_tier_chain(system_prompt, user_prompt, response_format)

    def _try_resolved(
        self,
        resolved: Tuple[genai.Client, str],
        system_prompt: str | None,
        user_prompt: str,
    ) -> str | None:
        """Call the locked-in (client, model) pair.

        Returns None when that pair failed and the full tier chain should be
        re-entered.
        """
        client, model = resolved
        try:
            return self._try_model(client, model, system_prompt, user_prompt)
        except genai_errors.ClientError as e:
            if getattr(e, "code", None) == 429:
                logger.warning(
                    f"Quota exhausted (429) for locked-in model {model}. "
                    f"Re-entering fallback chain..."
                )
            else:
                logger.warning(
                    f"Client error for locked-in model {model}: {e}. "
                    f"Re-entering fallback chain..."
                )
        except (
            genai_errors.ServerError,
            httpx.ReadError,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            ConnectionError,
            OSError,
        ):
            logger.warning(
                f"Locked-in model {model} failed. Re-entering full fallback chain..."
            )
        self._invalidate_resolved(resolved)
        return None

    def _invalidate_resolved(self, expected: Tuple[genai.Client, str]) -> None:
        """Drop the locked-in pair unless another thread already replaced it."""
        with self._resolve_lock:
            if self._resolved is expected:
                self._resolved = None

    def _walk_tier_chain(
        self,
        system_prompt: str | None,
        user_prompt: str,
        response_format: dict | None = None,
    ) -> str:
        """Try every API-key/model tier in order, then OpenRouter as a last resort.

        Callers must hold ``self._resolve_lock``.
        """
        free_models = [self.model_name] + [
            m for m in self.FALLBACK_MODELS if m != self.model_name
        ]

        api_key_tiers: List[Tuple[str, List[str]]] = [(self.api_key, free_models)]
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
                    self._resolved = (tier_client, model)
                    logger.info(f"Locked in model: {model} ({key_label} API key)")
                    return result
                except genai_errors.ClientError as e:
                    code = getattr(e, "code", None)
                    if code == 429:
                        logger.warning(
                            f"Quota exhausted (429) for {model} on "
                            f"{key_label} API key. Switching to next API key tier..."
                        )
                        break  # quota is key-wide; skip remaining models on this key
                    # Model-specific error: try the next model on this same key.
                    logger.warning(
                        f"Client error ({code}) for {model} on {key_label} API "
                        f"key: {e}. Trying next model..."
                    )
                    continue
                except (
                    genai_errors.ServerError,
                    httpx.ReadError,
                    httpx.ConnectError,
                    httpx.RemoteProtocolError,
                    ConnectionError,
                    OSError,
                ):
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

        # Final fallback: OpenRouter (last resort for any Gemini failure)
        if self.openrouter_api_key and self.openrouter_model:
            logger.warning(
                f"All Gemini models/keys failed. Falling back to OpenRouter "
                f"model {self.openrouter_model}..."
            )
            return self._try_openrouter(system_prompt, user_prompt, response_format)

        raise RuntimeError(
            "All Gemini models/keys failed and no OpenRouter fallback configured."
        )

    def _try_model(
        self,
        client: genai.Client,
        model: str,
        system_prompt: str | None,
        user_prompt: str,
    ) -> str:
        """Try a single model with exponential back-off retries (up to 4).

        Raises genai_errors.ClientError immediately on 429 so the caller
        can swap API keys without wasting the retry budget.
        """
        max_retries = 4
        base_delay = 5  # seconds; doubles per attempt
        max_delay = 60  # 1 minute cap

        config_kwargs: dict = {"temperature": 0.7}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
                return response.text
            except genai_errors.ClientError:
                raise  # includes 429 — bubble up immediately
            except genai_errors.ServerError as e:
                is_retryable = getattr(e, "code", None) == 503
                if is_retryable and attempt < max_retries - 1:
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        f"Gemini API unavailable (503) for {model}. "
                        f"Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                else:
                    raise
            except (
                httpx.ReadError,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                ConnectionError,
                OSError,
            ) as e:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        f"Network error for {model}: {e}. "
                        f"Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                else:
                    raise

    def _try_openrouter(
        self,
        system_prompt: str | None,
        user_prompt: str,
        response_format: dict | None = None,
    ) -> str:
        """Call OpenRouter (OpenAI-compatible) with exponential back-off retries.

        Retries on 429/5xx and transient network errors up to 4 times,
        honoring a server-supplied ``Retry-After`` header when present.

        ``response_format`` is forwarded verbatim (e.g. a ``json_schema``
        structured-output spec) when provided.
        """
        max_retries = 4
        base_delay = 5  # seconds; doubles per attempt
        max_delay = 60  # 1 minute cap

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        headers = {"Authorization": f"Bearer {self.openrouter_api_key}"}
        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": 0.7,
        }
        if response_format:
            payload["response_format"] = response_format

        for attempt in range(max_retries):
            try:
                response = httpx.post(
                    self.OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries - 1:
                        retry_after = _parse_retry_after(
                            response.headers.get("Retry-After", "")
                        )
                        if retry_after is not None:
                            source = "server Retry-After"
                            delay = max(retry_after, 0.0)
                            if delay > max_delay:
                                logger.warning(
                                    f"Server-supplied Retry-After of "
                                    f"{delay:.0f}s exceeds cap; clamping to "
                                    f"{max_delay}s."
                                )
                                delay = max_delay
                        else:
                            source = "exponential backoff"
                            delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            f"OpenRouter returned {response.status_code} for "
                            f"{self.openrouter_model}. Retrying in {delay:.0f}s "
                            f"via {source} "
                            f"(attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(delay)
                        continue
                response.raise_for_status()
                data = response.json()
                # OpenRouter can return HTTP 200 with an error payload or an
                # empty choices list (common on free/rate-limited models).
                choices = data.get("choices")
                if not choices:
                    err = data.get("error")
                    raise RuntimeError(
                        f"OpenRouter returned no choices for "
                        f"{self.openrouter_model}" + (f": {err}" if err else "")
                    )
                content = choices[0].get("message", {}).get("content")
                if not content:
                    raise RuntimeError(
                        f"OpenRouter returned empty content for "
                        f"{self.openrouter_model}"
                    )
                logger.info(f"OpenRouter model succeeded: {self.openrouter_model}")
                return content
            except (
                httpx.ReadError,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.TimeoutException,
                ConnectionError,
                OSError,
            ) as e:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        f"Network error for OpenRouter {self.openrouter_model}: "
                        f"{e}. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                else:
                    raise
        raise RuntimeError(
            f"OpenRouter model {self.openrouter_model} failed after "
            f"{max_retries} attempts."
        )
