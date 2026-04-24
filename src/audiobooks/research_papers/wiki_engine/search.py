"""Search integration — wraps qmd for hybrid search over wiki Markdown files."""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class WikiSearchResult:
    """A single search result from qmd."""

    title: str
    path: str
    score: float = 0.0
    snippet: str = ""


class WikiSearch:
    """Search interface for the wiki using qmd."""

    def __init__(self, wiki_dir: str):
        self.wiki_dir = Path(wiki_dir)
        self._qmd_available_cache: Optional[bool] = None

    def query(self, question: str, limit: int = 10) -> List[WikiSearchResult]:
        """Search the wiki using qmd.

        Args:
            question: Natural language query.
            limit: Max number of results.

        Returns:
            List of WikiSearchResult objects ranked by relevance.
        """
        if not self._qmd_available():
            logger.warning("qmd not installed, falling back to simple search")
            return self._fallback_search(question, limit)

        try:
            cmd = [
                "qmd", "query", question,
                "--dir", str(self.wiki_dir),
                "--json",
                "--limit", str(limit),
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning(f"qmd query failed: {result.stderr}")
                return self._fallback_search(question, limit)

            data = json.loads(result.stdout)
            results = []
            for item in data.get("results", []):
                results.append(WikiSearchResult(
                    title=item.get("title", ""),
                    path=item.get("path", ""),
                    score=item.get("score", 0.0),
                    snippet=item.get("snippet", ""),
                ))
            return results[:limit]

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"qmd search error: {e}")
            return self._fallback_search(question, limit)

    def _qmd_available(self) -> bool:
        """Check if qmd is installed and available. Result is cached for the instance lifetime."""
        if self._qmd_available_cache is None:
            try:
                result = subprocess.run(
                    ["qmd", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self._qmd_available_cache = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._qmd_available_cache = False
        return self._qmd_available_cache

    def _fallback_search(self, question: str, limit: int) -> List[WikiSearchResult]:
        """Simple keyword-based fallback search when qmd is unavailable."""
        results = []
        keywords = question.lower().split()

        if not self.wiki_dir.exists():
            return results

        for md_file in self.wiki_dir.rglob("*.md"):
            try:
                original = md_file.read_text(encoding="utf-8")
                content_lower = original.lower()
                # Score by keyword frequency
                score = sum(content_lower.count(kw) for kw in keywords)
                if score > 0:
                    # Extract title from frontmatter or filename
                    title = self._extract_title(md_file)
                    results.append(WikiSearchResult(
                        title=title,
                        path=str(md_file.relative_to(self.wiki_dir)),
                        score=float(score),
                        snippet=original[:200],
                    ))
            except Exception:
                continue

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _extract_title(self, filepath: Path) -> str:
        """Extract title from YAML frontmatter or use filename."""
        try:
            content = filepath.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    data = yaml.safe_load(parts[1])
                    if data and "title" in data:
                        return data["title"]
        except Exception:
            pass
        return filepath.stem.replace("_", " ").title()
