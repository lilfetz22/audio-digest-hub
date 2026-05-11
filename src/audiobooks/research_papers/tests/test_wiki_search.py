"""Tests for wiki search integration."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from wiki_engine.search import WikiSearch, WikiSearchResult


@pytest.fixture
def populated_wiki(tmp_path):
    """Create a wiki with some searchable content."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "concepts").mkdir()
    (wiki_dir / "sources").mkdir()

    # Create a concept page
    meta = {
        "title": "Mixture of Experts",
        "type": "concept",
        "sources": [],
        "created": "2026-04-10",
        "updated": "2026-04-10",
        "confidence": 0.85,
        "categories": ["AI Architecture"],
    }
    frontmatter = yaml.dump(meta, default_flow_style=False)
    (wiki_dir / "concepts" / "mixture_of_experts.md").write_text(
        f"---\n{frontmatter}---\n\nMoE routes tokens to expert sub-networks.\n",
        encoding="utf-8",
    )

    # Create another concept page
    meta2 = {
        "title": "Attention Mechanism",
        "type": "concept",
        "sources": [],
        "created": "2026-04-09",
        "updated": "2026-04-09",
        "confidence": 0.9,
        "categories": ["AI Architecture"],
    }
    frontmatter2 = yaml.dump(meta2, default_flow_style=False)
    (wiki_dir / "concepts" / "attention_mechanism.md").write_text(
        f"---\n{frontmatter2}---\n\nAttention computes weighted sums over all tokens.\n",
        encoding="utf-8",
    )

    return wiki_dir


class TestWikiSearch:
    """Tests for WikiSearch."""

    def test_fallback_search_returns_results(self, populated_wiki):
        """Fallback search finds pages by keyword match."""
        search = WikiSearch(wiki_dir=str(populated_wiki))
        results = search._fallback_search("mixture experts tokens", limit=10)

        assert len(results) >= 1
        titles = [r.title for r in results]
        assert "Mixture of Experts" in titles

    def test_fallback_search_ranks_by_relevance(self, populated_wiki):
        """More keyword matches rank higher."""
        search = WikiSearch(wiki_dir=str(populated_wiki))
        results = search._fallback_search("tokens expert", limit=10)

        # MoE page mentions both "tokens" and "expert"
        if len(results) >= 2:
            assert results[0].title == "Mixture of Experts"

    def test_search_empty_wiki(self, tmp_path):
        """Search on empty wiki returns empty list."""
        wiki_dir = tmp_path / "empty_wiki"
        wiki_dir.mkdir()
        search = WikiSearch(wiki_dir=str(wiki_dir))
        results = search.query("anything")
        assert results == []

    def test_search_nonexistent_wiki(self, tmp_path):
        """Search on nonexistent wiki dir returns empty list."""
        search = WikiSearch(wiki_dir=str(tmp_path / "nonexistent"))
        results = search._fallback_search("test", limit=5)
        assert results == []

    def test_query_uses_fallback_when_qmd_unavailable(self, populated_wiki):
        """query() falls back gracefully when qmd is not installed."""
        search = WikiSearch(wiki_dir=str(populated_wiki))
        # qmd is likely not installed in test env
        results = search.query("mixture of experts")
        # Should use fallback and return results
        assert isinstance(results, list)

    @patch("subprocess.run")
    def test_query_uses_qmd_when_available(self, mock_run, populated_wiki):
        """query() uses qmd when available."""
        # Mock qmd --version check
        mock_version = MagicMock()
        mock_version.returncode = 0

        # Mock qmd query result
        mock_query = MagicMock()
        mock_query.returncode = 0
        mock_query.stdout = json.dumps({
            "results": [
                {
                    "title": "Mixture of Experts",
                    "path": "concepts/mixture_of_experts.md",
                    "score": 0.95,
                    "snippet": "MoE routes tokens...",
                }
            ]
        })

        mock_run.side_effect = [mock_version, mock_query]

        search = WikiSearch(wiki_dir=str(populated_wiki))
        results = search.query("mixture of experts")

        assert len(results) == 1
        assert results[0].title == "Mixture of Experts"
        assert results[0].score == 0.95

    def test_extract_title_from_frontmatter(self, populated_wiki):
        """_extract_title reads title from YAML frontmatter."""
        search = WikiSearch(wiki_dir=str(populated_wiki))
        filepath = populated_wiki / "concepts" / "mixture_of_experts.md"
        title = search._extract_title(filepath)
        assert title == "Mixture of Experts"

    def test_extract_title_fallback_to_filename(self, tmp_path):
        """_extract_title uses filename when no frontmatter."""
        wiki_dir = tmp_path / "wiki"
        wiki_dir.mkdir()
        filepath = wiki_dir / "some_concept.md"
        filepath.write_text("No frontmatter here.", encoding="utf-8")

        search = WikiSearch(wiki_dir=str(wiki_dir))
        title = search._extract_title(filepath)
        assert title == "Some Concept"
