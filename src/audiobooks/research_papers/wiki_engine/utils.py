"""Shared utilities for the wiki engine."""

import logging
import re
from pathlib import Path

import yaml

from .models import WikiPageMeta

logger = logging.getLogger(__name__)


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
