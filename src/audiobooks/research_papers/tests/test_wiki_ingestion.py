"""Tests for the wiki ingestion engine."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from wiki_engine.ingestion import WikiIngestionEngine
from wiki_engine.models import WikiPageMeta, ExtractedConcept


@pytest.fixture
def tmp_wiki(tmp_path):
    """Create a temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "sources").mkdir()
    (wiki_dir / "concepts").mkdir()
    (wiki_dir / "queries").mkdir()
    return wiki_dir


@pytest.fixture
def sample_transcript(tmp_path):
    """Create a sample transcript file."""
    transcript = tmp_path / "research_digest_2026-04-10.txt"
    transcript.write_text(
        "Today we explore Mixture of Experts architectures. "
        "The key idea is that not all parameters need to be active for every input. "
        "By routing tokens to specialized sub-networks, we can scale model capacity "
        "without proportionally increasing compute costs.\n\n"
        "In contrast, State Space Models offer an alternative to attention mechanisms. "
        "They provide linear-time sequence modeling through structured state transitions, "
        "which is particularly beneficial for very long sequences where quadratic "
        "attention becomes prohibitive.",
        encoding="utf-8",
    )
    return transcript


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client that returns concept extraction results."""
    client = MagicMock()

    classify_response = MagicMock()
    classify_response.text = json.dumps({
        "category": "AI Architecture",
        "title": "MoE and SSMs",
        "paper_urls": ["https://arxiv.org/abs/2024.99999"],
    })

    extract_response = MagicMock()
    extract_response.text = json.dumps([
        {
            "name": "Mixture of Experts",
            "tldr": "Routing tokens to specialized sub-networks scales capacity without proportional compute.",
            "body": "MoE architectures use a gating mechanism to route each token to a subset of expert networks.",
            "counterarguments": "Load balancing across experts remains challenging; some experts may be undertrained.",
            "confidence": 0.85,
            "categories": ["AI Architecture"],
            "related_concepts": ["State Space Models", "Attention"],
            "sources": ["https://arxiv.org/abs/2024.99999"],
        },
        {
            "name": "State Space Models",
            "tldr": "Linear-time sequence modeling through structured state transitions.",
            "body": "SSMs model sequences as linear dynamical systems, achieving O(n) complexity.",
            "counterarguments": "May not match transformer quality on tasks requiring precise token-to-token attention.",
            "confidence": 0.80,
            "categories": ["AI Architecture"],
            "related_concepts": ["Mixture of Experts", "Attention"],
            "sources": [],
        },
    ])

    # Return classify for first call, extract for second
    client.models.generate_content.side_effect = [classify_response, extract_response]
    return client


class TestWikiIngestionEngine:
    """Tests for WikiIngestionEngine."""

    def test_source_page_created(self, tmp_wiki, sample_transcript):
        """Ingesting a transcript creates a source page."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None)
        result = engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        assert result["source_page"]
        source_path = Path(result["source_page"])
        assert source_path.exists()
        assert source_path.parent.name == "sources"

    def test_source_page_has_yaml_frontmatter(self, tmp_wiki, sample_transcript):
        """Source page has valid YAML frontmatter with required fields."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None)
        result = engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        source_path = Path(result["source_page"])
        content = source_path.read_text(encoding="utf-8")

        assert content.startswith("---")
        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])

        assert "title" in meta
        assert meta["type"] == "source"
        assert "created" in meta
        assert "updated" in meta
        assert "confidence" in meta
        assert "sources" in meta
        assert "categories" in meta

    def test_concepts_extracted_with_llm(self, tmp_wiki, sample_transcript, mock_llm_client):
        """With LLM client, concepts are extracted from transcript."""
        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki),
            llm_client=mock_llm_client,
        )
        result = engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        assert "Mixture of Experts" in result["concepts_created"]
        assert "State Space Models" in result["concepts_created"]

    def test_concept_page_has_required_sections(self, tmp_wiki, sample_transcript, mock_llm_client):
        """Concept pages have TLDR, Body, and Counterarguments sections."""
        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki),
            llm_client=mock_llm_client,
        )
        engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        concept_files = list((tmp_wiki / "concepts").glob("*.md"))
        assert len(concept_files) >= 1

        for concept_file in concept_files:
            content = concept_file.read_text(encoding="utf-8")
            assert "## TLDR" in content
            assert "## Body" in content
            assert "## Counterarguments / Data Gaps" in content

    def test_concept_page_has_valid_yaml(self, tmp_wiki, sample_transcript, mock_llm_client):
        """Concept pages have valid YAML frontmatter."""
        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki),
            llm_client=mock_llm_client,
        )
        engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        for concept_file in (tmp_wiki / "concepts").glob("*.md"):
            content = concept_file.read_text(encoding="utf-8")
            assert content.startswith("---")
            parts = content.split("---", 2)
            meta = yaml.safe_load(parts[1])
            assert meta["type"] == "concept"
            assert "title" in meta
            assert "confidence" in meta

    def test_concept_upsert_appends(self, tmp_wiki, sample_transcript):
        """Ingesting the same concept twice updates (appends), doesn't duplicate."""
        # Pre-create a concept page
        concepts_dir = tmp_wiki / "concepts"
        existing = concepts_dir / "mixture_of_experts.md"
        existing_meta = WikiPageMeta(
            title="Mixture of Experts",
            type="concept",
            sources=["https://old-paper.com"],
            confidence=0.7,
            categories=["AI Architecture"],
        )
        existing_body = "## TLDR\n\nOld TLDR.\n\n## Body\n\nOld body content.\n\n## Counterarguments / Data Gaps\n\nOld gaps."
        frontmatter = yaml.dump(existing_meta.to_dict(), default_flow_style=False, sort_keys=False)
        existing.write_text(f"---\n{frontmatter}---\n\n{existing_body}\n", encoding="utf-8")

        # Now upsert with new info (no LLM — uses simple append)
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None)
        new_concept = ExtractedConcept(
            name="Mixture of Experts",
            tldr="New TLDR about MoE scaling.",
            body="New body content about recent advances.",
            counterarguments="New gaps identified.",
            confidence=0.9,
            sources=["https://new-paper.com"],
        )
        was_updated = engine._upsert_concept(new_concept, "2026-04-15")

        assert was_updated is True

        # Verify only one file exists
        moe_files = list(concepts_dir.glob("mixture_of_experts*"))
        assert len(moe_files) == 1

        # Verify content was appended
        content = existing.read_text(encoding="utf-8")
        assert "Old body content" in content
        assert "New body content" in content
        assert "2026-04-15" in content  # Update date present

    def test_concept_has_wikilinks(self, tmp_wiki, sample_transcript, mock_llm_client):
        """Concept pages include [[wikilinks]] to related concepts."""
        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki),
            llm_client=mock_llm_client,
        )
        engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        moe_file = tmp_wiki / "concepts" / "mixture_of_experts.md"
        if moe_file.exists():
            content = moe_file.read_text(encoding="utf-8")
            assert "[[" in content  # Has at least one wikilink

    def test_ingestion_without_llm_creates_source_only(self, tmp_wiki, sample_transcript):
        """Without LLM, only source page is created (no concepts)."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None)
        result = engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        assert result["source_page"]
        assert result["concepts_created"] == []
        assert result["concepts_updated"] == []

    def test_ingestion_rebuilds_index(self, tmp_wiki, sample_transcript):
        """Ingestion rebuilds wiki/index.md automatically."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None)
        result = engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        assert result["index_page"]
        index_path = Path(result["index_page"])
        assert index_path.exists()
        assert index_path.name == "index.md"

    def test_ingestion_calls_auto_commit_when_enabled(self, tmp_wiki, sample_transcript):
        """Ingestion triggers git auto-commit when enabled."""
        mock_git_manager = MagicMock()
        mock_git_manager.auto_commit.return_value = True

        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki),
            llm_client=None,
            git_manager=mock_git_manager,
            auto_commit=True,
        )
        result = engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        assert result["auto_committed"] is True
        mock_git_manager.auto_commit.assert_called_once()

    def test_slugify(self):
        """Slugify converts names to filesystem-safe slugs."""
        assert WikiIngestionEngine._slugify("Mixture of Experts") == "mixture_of_experts"
        assert WikiIngestionEngine._slugify("State Space Models") == "state_space_models"
        assert WikiIngestionEngine._slugify("GPT-4 Architecture") == "gpt-4_architecture"
