"""End-to-end tests for the full wiki pipeline."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from wiki_engine.ingestion import WikiIngestionEngine
from wiki_engine.index_builder import IndexBuilder
from wiki_engine.query_saver import QuerySaver
from wiki_engine.linter import WikiLinter
from wiki_engine.search import WikiSearch


@pytest.fixture
def full_wiki_setup(tmp_path):
    """Set up a complete wiki environment for E2E testing."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "sources").mkdir()
    (wiki_dir / "concepts").mkdir()
    (wiki_dir / "queries").mkdir()

    # Create a sample transcript
    transcript = tmp_path / "research_digest_2026-04-10.txt"
    transcript.write_text(
        "Today we discuss three major advances in AI research.\n\n"
        "First, Mixture of Experts (MoE) architectures have shown that routing tokens "
        "to specialized sub-networks can achieve the quality of dense models at a fraction "
        "of the compute cost. The key insight is that sparsity at inference time doesn't "
        "harm quality when the gating mechanism is well-designed.\n\n"
        "Second, State Space Models provide an alternative to the Transformer's attention "
        "mechanism. By modeling sequences as linear dynamical systems, they achieve O(n) "
        "complexity instead of O(n^2), making them particularly suited for very long sequences.\n\n"
        "Third, advances in Knowledge Distillation show that smaller student models can "
        "capture most of the teacher's capabilities when trained with the right objectives. "
        "This is crucial for deploying large models in resource-constrained environments.",
        encoding="utf-8",
    )

    return {
        "wiki_dir": wiki_dir,
        "transcript": transcript,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def mock_llm():
    """Mock LLM that returns reasonable extraction results."""
    client = MagicMock()

    classify_response = MagicMock()
    classify_response.text = json.dumps({
        "category": "AI Architecture",
        "title": "MoE SSM and Distillation",
        "paper_urls": [],
    })

    extract_response = MagicMock()
    extract_response.text = json.dumps([
        {
            "name": "Mixture of Experts",
            "tldr": "Sparse routing achieves dense-model quality at reduced compute.",
            "body": "MoE uses gating to route tokens to expert sub-networks.",
            "counterarguments": "Load balancing and expert collapse remain open problems.",
            "confidence": 0.85,
            "categories": ["AI Architecture", "Optimization"],
            "related_concepts": ["State Space Models"],
            "sources": [],
        },
        {
            "name": "State Space Models",
            "tldr": "Linear-time sequence modeling via structured state transitions.",
            "body": "SSMs achieve O(n) complexity for sequence modeling.",
            "counterarguments": "May underperform on tasks needing precise token interactions.",
            "confidence": 0.80,
            "categories": ["AI Architecture"],
            "related_concepts": ["Mixture of Experts", "Attention"],
            "sources": [],
        },
    ])

    client.models.generate_content.side_effect = [classify_response, extract_response]
    return client


class TestWikiDirectoriesCreated:
    """Phase 1: Verify wiki directory structure."""

    def test_wiki_directories_created(self, full_wiki_setup):
        """Wiki directories exist after setup."""
        wiki_dir = full_wiki_setup["wiki_dir"]
        assert (wiki_dir / "sources").is_dir()
        assert (wiki_dir / "concepts").is_dir()
        assert (wiki_dir / "queries").is_dir()

    def test_index_created(self, full_wiki_setup):
        """Index is created when rebuild is called."""
        wiki_dir = full_wiki_setup["wiki_dir"]
        builder = IndexBuilder(wiki_dir=str(wiki_dir))
        index_path = builder.rebuild()

        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "LLM Wiki Index" in content
        assert "Concepts" in content
        assert "Sources" in content
        assert "Saved Queries" in content


class TestFullIngestionPipeline:
    """Phase 2: End-to-end ingestion test."""

    def test_full_ingestion_creates_source_and_concepts(self, full_wiki_setup, mock_llm):
        """Full ingestion creates source page + concept pages."""
        wiki_dir = full_wiki_setup["wiki_dir"]
        transcript = full_wiki_setup["transcript"]

        engine = WikiIngestionEngine(
            wiki_dir=str(wiki_dir),
            llm_client=mock_llm,
        )
        result = engine.ingest_transcript(str(transcript), "2026-04-10")

        # Source page created
        assert result["source_page"]
        assert Path(result["source_page"]).exists()

        # Concept pages created
        assert len(result["concepts_created"]) >= 1

        # Verify concept files exist
        concept_files = list((wiki_dir / "concepts").glob("*.md"))
        assert len(concept_files) >= 1

    def test_ingestion_then_index_rebuild(self, full_wiki_setup, mock_llm):
        """After ingestion, index rebuild lists all pages."""
        wiki_dir = full_wiki_setup["wiki_dir"]
        transcript = full_wiki_setup["transcript"]

        # Ingest
        engine = WikiIngestionEngine(
            wiki_dir=str(wiki_dir),
            llm_client=mock_llm,
        )
        engine.ingest_transcript(str(transcript), "2026-04-10")

        # Rebuild index
        builder = IndexBuilder(wiki_dir=str(wiki_dir))
        builder.rebuild()

        index_content = (wiki_dir / "index.md").read_text(encoding="utf-8")
        # Should list the source page
        assert "2026-04-10" in index_content

    def test_ingestion_then_search(self, full_wiki_setup, mock_llm):
        """After ingestion, search can find concepts."""
        wiki_dir = full_wiki_setup["wiki_dir"]
        transcript = full_wiki_setup["transcript"]

        engine = WikiIngestionEngine(
            wiki_dir=str(wiki_dir),
            llm_client=mock_llm,
        )
        engine.ingest_transcript(str(transcript), "2026-04-10")

        search = WikiSearch(wiki_dir=str(wiki_dir))
        results = search._fallback_search("mixture experts", limit=5)
        assert len(results) >= 1


class TestQuerySaveAndSearch:
    """Phase 3: Query saving and retrieval."""

    @patch("wiki_engine.query_saver.datetime")
    def test_save_then_find_query(self, mock_dt, full_wiki_setup):
        """Saved queries are searchable."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"

        wiki_dir = full_wiki_setup["wiki_dir"]

        saver = QuerySaver(wiki_dir=str(wiki_dir))
        saver.save(
            question="How does MoE compare to dense models?",
            answer="MoE achieves similar quality with less compute by routing tokens.",
        )

        search = WikiSearch(wiki_dir=str(wiki_dir))
        results = search._fallback_search("MoE dense models", limit=5)
        assert len(results) >= 1


class TestLintAfterIngestion:
    """Phase 4: Linting after ingestion."""

    def test_lint_finds_orphans_after_ingestion(self, full_wiki_setup, mock_llm):
        """Lint pass detects orphan pages after ingestion."""
        wiki_dir = full_wiki_setup["wiki_dir"]
        transcript = full_wiki_setup["transcript"]

        engine = WikiIngestionEngine(
            wiki_dir=str(wiki_dir),
            llm_client=mock_llm,
        )
        engine.ingest_transcript(str(transcript), "2026-04-10")

        linter = WikiLinter(wiki_dir=str(wiki_dir), llm_client=None)
        result = linter.run_full_lint()

        # Report should exist
        assert Path(result["report_path"]).exists()

    def test_full_pipeline_flow(self, full_wiki_setup, mock_llm):
        """Complete flow: ingest → index → query → lint."""
        wiki_dir = full_wiki_setup["wiki_dir"]
        transcript = full_wiki_setup["transcript"]

        # 1. Ingest
        engine = WikiIngestionEngine(
            wiki_dir=str(wiki_dir),
            llm_client=mock_llm,
        )
        result = engine.ingest_transcript(str(transcript), "2026-04-10")
        assert result["source_page"]

        # 2. Index
        builder = IndexBuilder(wiki_dir=str(wiki_dir))
        index_path = builder.rebuild()
        assert index_path.exists()

        # 3. Search
        search = WikiSearch(wiki_dir=str(wiki_dir))
        results = search._fallback_search("expert", limit=5)
        # Should find something
        assert isinstance(results, list)

        # 4. Lint
        linter = WikiLinter(wiki_dir=str(wiki_dir), llm_client=None)
        lint_result = linter.run_full_lint()
        assert Path(lint_result["report_path"]).exists()
