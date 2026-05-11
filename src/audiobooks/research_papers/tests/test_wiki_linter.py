"""Tests for the wiki linter."""

from pathlib import Path
from unittest.mock import MagicMock

import json
import pytest
import yaml

from wiki_engine.linter import WikiLinter


@pytest.fixture
def wiki_with_content(tmp_path):
    """Create a wiki with multiple concept pages for linting."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "concepts").mkdir()
    (wiki_dir / "sources").mkdir()

    # Page 1: references page 2, no reference to page 3
    meta1 = {
        "title": "Mixture of Experts",
        "type": "concept",
        "sources": [],
        "created": "2026-04-10",
        "updated": "2026-04-10",
        "confidence": 0.85,
        "categories": ["AI Architecture"],
    }
    (wiki_dir / "concepts" / "mixture_of_experts.md").write_text(
        f"---\n{yaml.dump(meta1)}---\n\n## TLDR\n\nMoE scales models.\n\n"
        f"## Body\n\nRelated to [[Attention Mechanism]].\n\n"
        f"## Counterarguments / Data Gaps\n\nLoad balancing is hard.\n",
        encoding="utf-8",
    )

    # Page 2: referenced by page 1
    meta2 = {
        "title": "Attention Mechanism",
        "type": "concept",
        "sources": [],
        "created": "2026-04-09",
        "updated": "2026-04-09",
        "confidence": 0.9,
        "categories": ["AI Architecture"],
    }
    (wiki_dir / "concepts" / "attention_mechanism.md").write_text(
        f"---\n{yaml.dump(meta2)}---\n\n## TLDR\n\nAttention computes weighted sums.\n\n"
        f"## Body\n\nUsed in Transformer architectures.\n\n"
        f"## Counterarguments / Data Gaps\n\nQuadratic complexity.\n",
        encoding="utf-8",
    )

    # Page 3: ORPHAN — no other page links to it
    meta3 = {
        "title": "Knowledge Distillation",
        "type": "concept",
        "sources": [],
        "created": "2026-04-08",
        "updated": "2026-04-08",
        "confidence": 0.7,
        "categories": ["Optimization"],
    }
    (wiki_dir / "concepts" / "knowledge_distillation.md").write_text(
        f"---\n{yaml.dump(meta3)}---\n\n## TLDR\n\nCompressing large models.\n\n"
        f"## Body\n\nTeacher-student framework. Transformer models use this approach. "
        f"Transformer architectures benefit from Transformer distillation.\n\n"
        f"## Counterarguments / Data Gaps\n\nQuality loss.\n",
        encoding="utf-8",
    )

    # Source page that mentions "Transformer" repeatedly
    meta_src = {
        "title": "Research Digest 2026-04-10",
        "type": "source",
        "sources": [],
        "created": "2026-04-10",
        "updated": "2026-04-10",
        "confidence": 0.5,
        "categories": ["daily-digest"],
    }
    (wiki_dir / "sources" / "digest_2026-04-10.md").write_text(
        f"---\n{yaml.dump(meta_src)}---\n\nToday we discuss Transformer improvements. "
        f"The Transformer architecture has evolved significantly. "
        f"New Transformer variants show promise.\n",
        encoding="utf-8",
    )

    return wiki_dir


class TestWikiLinter:
    """Tests for WikiLinter."""

    def test_find_orphan_pages(self, wiki_with_content):
        """Finds pages with no inbound [[wikilinks]]."""
        linter = WikiLinter(wiki_dir=str(wiki_with_content))
        orphans = linter.find_orphan_pages()

        # "knowledge_distillation" and "mixture_of_experts" are not linked to
        # "attention_mechanism" IS linked from mixture_of_experts
        assert "knowledge_distillation.md" in orphans
        assert "mixture_of_experts.md" in orphans
        assert "attention_mechanism.md" not in orphans

    def test_find_orphans_empty_wiki(self, tmp_path):
        """No orphans in empty wiki."""
        wiki_dir = tmp_path / "wiki"
        wiki_dir.mkdir()
        linter = WikiLinter(wiki_dir=str(wiki_dir))
        assert linter.find_orphan_pages() == []

    def test_find_contradictions_with_mock_llm(self, wiki_with_content):
        """LLM-based contradiction detection returns results."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {
                "type": "contradiction",
                "description": "MoE claims scaling is free but distillation page implies quality cost",
                "pages_involved": ["mixture_of_experts.md", "knowledge_distillation.md"],
                "severity": "medium",
            }
        ])
        mock_client.models.generate_content.return_value = mock_response

        linter = WikiLinter(wiki_dir=str(wiki_with_content), llm_client=mock_client)
        contradictions = linter.find_contradictions()

        assert len(contradictions) == 1
        assert contradictions[0]["type"] == "contradiction"
        assert "mixture_of_experts.md" in contradictions[0]["pages_involved"]

    def test_find_contradictions_without_llm(self, wiki_with_content):
        """Without LLM, contradiction detection returns empty list."""
        linter = WikiLinter(wiki_dir=str(wiki_with_content), llm_client=None)
        contradictions = linter.find_contradictions()
        assert contradictions == []

    def test_find_implicit_concepts(self, wiki_with_content):
        """Finds terms mentioned 3+ times without their own page."""
        linter = WikiLinter(wiki_dir=str(wiki_with_content))
        implicit = linter.find_implicit_concepts(min_mentions=3)

        # "transformer" is mentioned many times but has no concept page
        terms = [item["term"] for item in implicit]
        assert any("transformer" in t for t in terms)

    def test_find_implicit_concepts_excludes_existing(self, wiki_with_content):
        """Existing concept pages are not flagged as implicit."""
        linter = WikiLinter(wiki_dir=str(wiki_with_content))
        implicit = linter.find_implicit_concepts(min_mentions=1)

        terms = [item["term"] for item in implicit]
        # These have their own pages and should not appear
        assert "mixture of experts" not in terms
        assert "attention mechanism" not in terms

    def test_lint_report_written(self, wiki_with_content):
        """Full lint run writes a report to wiki/lint_report.md."""
        linter = WikiLinter(wiki_dir=str(wiki_with_content), llm_client=None)
        result = linter.run_full_lint()

        report_path = Path(result["report_path"])
        assert report_path.exists()
        assert report_path.name == "lint_report.md"

        content = report_path.read_text(encoding="utf-8")
        assert "Orphan Pages" in content
        assert "Contradictions" in content
        assert "Implicit Concepts" in content

    def test_full_lint_returns_all_sections(self, wiki_with_content):
        """run_full_lint returns dict with all expected keys."""
        linter = WikiLinter(wiki_dir=str(wiki_with_content), llm_client=None)
        result = linter.run_full_lint()

        assert "orphans" in result
        assert "contradictions" in result
        assert "implicit_concepts" in result
        assert "report_path" in result

    def test_find_contradictions_prefers_recently_updated_pages(self, tmp_path):
        """Contradiction scan sends recently updated pages first."""
        wiki_dir = tmp_path / "wiki"
        concepts_dir = wiki_dir / "concepts"
        concepts_dir.mkdir(parents=True)

        old_meta = {
            "title": "Old Concept",
            "type": "concept",
            "sources": [],
            "created": "2026-01-01",
            "updated": "2026-01-01",
            "confidence": 0.5,
            "categories": ["Other"],
        }
        new_meta = {
            "title": "New Concept",
            "type": "concept",
            "sources": [],
            "created": "2026-04-19",
            "updated": "2026-04-19",
            "confidence": 0.8,
            "categories": ["AI Architecture"],
        }
        (concepts_dir / "old_concept.md").write_text(
            f"---\n{yaml.dump(old_meta)}---\n\nOld content",
            encoding="utf-8",
        )
        (concepts_dir / "new_concept.md").write_text(
            f"---\n{yaml.dump(new_meta)}---\n\nNew content",
            encoding="utf-8",
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "[]"
        mock_client.models.generate_content.return_value = mock_response

        linter = WikiLinter(wiki_dir=str(wiki_dir), llm_client=mock_client)
        linter.find_contradictions()

        called_contents = mock_client.models.generate_content.call_args.kwargs["contents"]
        assert called_contents.find("=== new_concept.md ===") < called_contents.find("=== old_concept.md ===")

    def test_run_full_lint_calls_auto_commit_when_enabled(self, wiki_with_content):
        """Lint pass triggers auto-commit when enabled."""
        mock_git_manager = MagicMock()
        mock_git_manager.auto_commit.return_value = True

        linter = WikiLinter(
            wiki_dir=str(wiki_with_content),
            llm_client=None,
            git_manager=mock_git_manager,
            auto_commit=True,
        )
        result = linter.run_full_lint()

        assert result["auto_committed"] is True
        mock_git_manager.auto_commit.assert_called_once()
