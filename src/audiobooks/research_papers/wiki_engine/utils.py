"""Shared utilities for the wiki engine."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Optional

import yaml
from pydantic import BaseModel

from .models import WikiPageMeta

logger = logging.getLogger(__name__)

# Sentinel distinguishing a genuine JSON ``null`` from a parse failure.
_PARSE_FAILED = object()


def _inline_refs(schema: dict) -> dict:
    """Inline pydantic ``$defs``/``$ref`` so validators without ref support work.

    Pydantic emits ``$ref`` entries (into ``$defs``) for nested models; some
    providers reached via OpenRouter only accept fully self-contained schemas.
    """
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                return resolve(dict(defs.get(ref.split("/")[-1], {})))
            # Drop ``title`` — harmless to OpenAI-strict validators but rejected
            # by some providers reached via OpenRouter.
            return {k: resolve(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


def build_response_format(name: str, model: type[BaseModel]) -> dict:
    """Build an OpenRouter ``json_schema`` response_format from a pydantic model.

    The model is the single source of truth for both the structured-output
    schema (via this function) and response validation.  Models must use
    ``ConfigDict(extra="forbid")`` and declare no field defaults so the schema
    satisfies strict mode (all properties required, no extra keys).
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": _inline_refs(model.model_json_schema()),
        },
    }


def _strip_code_fences(text: str) -> str:
    """Remove a surrounding ```json ... ``` markdown fence if present."""
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if "```" in text:
            text = text.rsplit("```", 1)[0]
    return text.strip()


def _salvage_json(text: str) -> Any:
    """Best-effort extraction of the first JSON object/array embedded in text."""
    # Prefer whichever bracket the payload actually starts with.
    pairs = (
        (("{", "}"), ("[", "]"))
        if text.lstrip()[:1] == "{"
        else (("[", "]"), ("{", "}"))
    )
    for open_ch, close_ch in pairs:
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return _PARSE_FAILED


def _loads_lenient(raw: str) -> Any:
    """Parse ``raw`` as JSON, tolerating code fences and surrounding prose."""
    text = _strip_code_fences(raw.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _salvage_json(text)


def parse_json_response(
    generate_fn: Callable[[], Optional[str]],
    *,
    retries: int = 1,
    context: str = "",
) -> Any:
    """Invoke an LLM generation callable and parse its output as JSON.

    ``generate_fn`` is a zero-argument callable returning the raw model text
    (or ``None``).  On an empty or unparseable response it is re-invoked up to
    ``retries`` additional times before giving up.  Code fences and surrounding
    prose are tolerated.  Returns the parsed object/list, or ``None`` when every
    attempt fails.
    """
    label = f" [{context}]" if context else ""
    last_raw: Optional[str] = None
    for attempt in range(retries + 1):
        try:
            raw = generate_fn()
        except Exception as e:  # LLM boundary: a client failure must not crash ingestion
            last_raw = None
            if attempt < retries:
                logger.warning(
                    "LLM generation raised%s (attempt %d/%d); retrying... (%s)",
                    label,
                    attempt + 1,
                    retries + 1,
                    e,
                )
                continue
            logger.warning(
                "LLM generation raised%s after %d attempt(s); giving up: %s",
                label,
                retries + 1,
                e,
            )
            return None
        last_raw = raw
        if raw and raw.strip():
            parsed = _loads_lenient(raw)
            if parsed is not _PARSE_FAILED:
                return parsed
            reason = "invalid JSON"
        else:
            reason = "empty response"
        if attempt < retries:
            logger.warning(
                "LLM returned %s%s (attempt %d/%d); retrying...",
                reason,
                label,
                attempt + 1,
                retries + 1,
            )
    snippet = (last_raw or "")[:200].replace("\n", " ")
    logger.warning(
        "LLM returned invalid JSON%s after %d attempt(s); giving up. Raw: %r",
        label,
        retries + 1,
        snippet,
    )
    return None


def coerce_json_list(data: Any, key: str) -> list:
    """Normalize a structured-output payload into a plain list.

    Handles three shapes the model may return for a "list of things":
    a bare JSON array, an object wrapping the array under ``key`` (required
    when a provider enforces an object root for json_schema), or a single
    object (wrapped into a one-element list).
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, list):
            return value
        return [data]
    return []


def load_prompt(prompts_dir: Path, filename: str, fallback: str) -> str:
    """Load a prompt template from disk with a safe fallback."""
    try:
        path = prompts_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        logger.warning("Failed loading prompt %s", filename)
    return fallback


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s]+", "_", slug)
    return slug


def format_page(meta: WikiPageMeta, body: str) -> str:
    """Format a wiki page with YAML frontmatter."""
    frontmatter = yaml.dump(meta.to_dict(), default_flow_style=False, sort_keys=False)
    return f"---\n{frontmatter}---\n\n{body}\n"
