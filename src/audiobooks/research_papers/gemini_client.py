"""Shared Gemini LLM client with multi-tier model/key fallback.

Both GeminiTranscriptGenerator and WikiIngestionEngine use this class so that
quota exhaustion, transient errors, and model unavailability are handled
consistently in one place.

Fallback order:
  1. Primary API key  – preferred model, then FALLBACK_MODELS in order
  2. Backup API key   – same model chain (skipped if not configured)
  3. Paid API key     – paid model (last resort, skipped if not configured)

Within each model attempt, up to 10 retries with exponential back-off are
made for retryable server/network errors. A 429 quota error immediately
moves to the next API-key tier without burning retry budget.
"""

import logging
import time
from typing import List, Tuple

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiClientWithFallback:
    """Gemini client that walks through API-key and model tiers on failure."""

    FALLBACK_MODELS: List[str] = [
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
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.backup_api_key = backup_api_key
        self.paid_api_key = paid_api_key
        self.paid_model_name = paid_model_name
        self._resolved_model: str | None = None
        self._resolved_client: genai.Client | None = None

    def generate(self, user_prompt: str, system_prompt: str | None = None) -> str:
        """Generate content with full fallback chain.

        On the first call every tier is tried in order.  Whichever
        (client, model) succeeds is "locked in" for subsequent calls,
        so we avoid re-running the full chain on every request.  If the
        locked-in combination later fails the full chain is re-entered.

        Args:
            user_prompt: The user/content part of the prompt.
            system_prompt: Optional system instruction.

        Returns:
            Generated text.

        Raises:
            RuntimeError: When all tiers are exhausted.
        """
        # Fast path: try locked-in model first
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
                    self._resolved_model = model
                    self._resolved_client = tier_client
                    logger.info(f"Locked in model: {model} ({key_label} API key)")
                    return result
                except genai_errors.ClientError as e:
                    if getattr(e, "code", None) == 429:
                        logger.warning(
                            f"Quota exhausted (429) for {model} on "
                            f"{key_label} API key. Switching to next API key tier..."
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
        system_prompt: str | None,
        user_prompt: str,
    ) -> str:
        """Try a single model with exponential back-off retries (up to 10).

        Raises genai_errors.ClientError immediately on 429 so the caller
        can swap API keys without wasting the retry budget.
        """
        max_retries = 10
        base_delay = 30   # seconds; doubles per attempt
        max_delay = 600   # 10 minutes cap

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
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"Gemini API unavailable (503) for {model}. "
                        f"Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                else:
                    raise
            except (httpx.ReadError, httpx.ConnectError,
                    httpx.RemoteProtocolError, ConnectionError, OSError) as e:
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
