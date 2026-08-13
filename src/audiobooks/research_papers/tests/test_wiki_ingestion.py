"""Tests for the wiki ingestion engine."""

import json
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from wiki_engine.classifier import split_transcript_into_sections
from wiki_engine.ingestion import WikiIngestionEngine
from wiki_engine.models import WikiPageMeta, ExtractedConcept, ClassifiedSection


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


def _make_analysis_response_text():
    """JSON body for a combined classify+extract LLM response (single call)."""
    return json.dumps({
        "category": "AI Architecture",
        "title": "MoE and SSMs",
        "paper_urls": ["https://arxiv.org/abs/2024.99999"],
        "concepts": [
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
        ],
    })


@pytest.fixture
def multi_section_transcript(tmp_path):
    """Transcript that splits into exactly three sections.

    split_transcript_into_sections breaks on a blank line once the current
    section exceeds 1200 characters, so each paragraph is padded past that.
    """
    paragraph = (
        "This paragraph discusses a distinct research topic in detail. " * 25
    )
    transcript = tmp_path / "research_digest_2026-04-11.txt"
    transcript.write_text("\n\n".join([paragraph] * 3), encoding="utf-8")
    return transcript


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client returning a single combined analyze response."""
    client = MagicMock()
    analyze_response = MagicMock()
    analyze_response.text = _make_analysis_response_text()
    client.models.generate_content.return_value = analyze_response
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

        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])
        assert set(meta["sources"]) == {"https://old-paper.com", "https://new-paper.com"}

    def _make_existing_concept_page(self, tmp_wiki):
        """Helper: write a pre-existing 'Mixture of Experts' concept page."""
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
        return existing

    def test_default_llm_merge_updates_is_false(self, tmp_wiki):
        """Constructor defaults llm_merge_updates to False."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None)
        assert engine.llm_merge_updates is False

    def test_default_construction_skips_llm_on_concept_update(self, tmp_wiki):
        """With an LLM client but the default flag, updates use _simple_append, not the LLM."""
        self._make_existing_concept_page(tmp_wiki)
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=MagicMock())
        new_concept = ExtractedConcept(
            name="Mixture of Experts",
            tldr="New TLDR.",
            body="New body content.",
            counterarguments="New gaps.",
            confidence=0.9,
            sources=["https://new-paper.com"],
        )

        with patch.object(engine, "_llm_update_concept") as mock_llm_update, \
             patch.object(engine, "_simple_append", wraps=engine._simple_append) as mock_simple_append:
            engine._upsert_concept(new_concept, "2026-04-15")

        mock_llm_update.assert_not_called()
        mock_simple_append.assert_called_once()

    def test_llm_merge_updates_true_invokes_llm_update(self, tmp_wiki):
        """Opting in with llm_merge_updates=True routes updates through _llm_update_concept."""
        existing = self._make_existing_concept_page(tmp_wiki)
        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki), llm_client=MagicMock(), llm_merge_updates=True
        )
        new_concept = ExtractedConcept(
            name="Mixture of Experts",
            tldr="New TLDR.",
            body="New body content.",
            counterarguments="New gaps.",
            confidence=0.9,
            sources=["https://new-paper.com"],
        )

        with patch.object(
            engine, "_llm_update_concept", return_value=existing.read_text(encoding="utf-8")
        ) as mock_llm_update:
            engine._upsert_concept(new_concept, "2026-04-15")

        mock_llm_update.assert_called_once()

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

    def test_wiki_source_url_marker_preserved_in_concept(
        self, tmp_wiki, tmp_path, mock_llm_client
    ):
        """WIKI_SOURCE_URL markers written by the transcript generator are
        parsed by Python and injected into concept page sources — the LLM is
        not involved in URL extraction."""
        paper_url = "https://arxiv.org/abs/2501.99999"

        # Simulate a transcript that already has the URL marker embedded by
        # GeminiTranscriptGenerator.generate().
        transcript = tmp_path / "research_digest_2026-05-01.txt"
        transcript.write_text(
            f"<!-- WIKI_SOURCE_URL: {paper_url} -->\n"
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

        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki),
            llm_client=mock_llm_client,
        )
        engine.ingest_transcript(str(transcript), "2026-05-01")

        # At least one concept page should contain the original paper URL.
        concept_files = list((tmp_wiki / "concepts").glob("*.md"))
        assert concept_files, "No concept pages were created"

        all_sources: list[str] = []
        for f in concept_files:
            content = f.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            assert len(parts) > 1, f"Missing frontmatter in {f}"
            meta = yaml.safe_load(parts[1])
            all_sources.extend(meta.get("sources", []))

        assert paper_url in all_sources, (
            f"Expected '{paper_url}' in concept sources but got: {all_sources}"
        )


class TestCombinedSectionAnalysis:
    """Tests for the combined classify+extract-per-section call (Tasks 4 & 7)."""

    def test_defaults(self, tmp_wiki):
        """combined_analysis defaults True, max_workers defaults to 4."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None)
        assert engine.combined_analysis is True
        assert engine.max_workers == 4

    def test_combined_analysis_calls_llm_once_per_section(
        self, tmp_wiki, multi_section_transcript, mock_llm_client
    ):
        """The combined path makes exactly one LLM call per section, not two."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=mock_llm_client)
        sections = split_transcript_into_sections(
            multi_section_transcript.read_text(encoding="utf-8")
        )
        assert len(sections) == 3

        analyzed = engine._analyze_sections(sections)

        assert len(analyzed) == 3
        assert mock_llm_client.models.generate_content.call_count == 3

    def test_combined_analysis_extracts_classification_and_concepts(
        self, tmp_wiki, mock_llm_client
    ):
        """A single _analyze_section call yields both classification and concepts."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=mock_llm_client)
        section, concepts = engine._analyze_section("Some transcript section text.")

        assert section.category == "AI Architecture"
        assert section.title == "MoE and SSMs"
        assert "https://arxiv.org/abs/2024.99999" in section.paper_urls
        assert {c.name for c in concepts} == {"Mixture of Experts", "State Space Models"}
        assert mock_llm_client.models.generate_content.call_count == 1

    def test_source_url_injected_into_combined_analysis(self, tmp_wiki, mock_llm_client):
        """Python-parsed WIKI_SOURCE_URL markers still get merged into paper_urls."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=mock_llm_client)
        text = "<!-- WIKI_SOURCE_URL: https://arxiv.org/abs/2501.11111 -->\nSection body."
        section, concepts = engine._analyze_section(text)

        assert "https://arxiv.org/abs/2501.11111" in section.paper_urls
        assert all(
            "https://arxiv.org/abs/2501.11111" in c.sources for c in concepts
        )

    def test_legacy_two_call_path_still_selectable(self, tmp_wiki, sample_transcript):
        """combined_analysis=False keeps the old classify-then-extract path (2 LLM calls)."""
        client = MagicMock()
        classify_response = MagicMock()
        classify_response.text = json.dumps({
            "category": "AI Architecture",
            "title": "MoE and SSMs",
            "paper_urls": [],
        })
        extract_response = MagicMock()
        extract_response.text = json.dumps({
            "concepts": [
                {
                    "name": "Mixture of Experts",
                    "tldr": "TLDR",
                    "body": "Body",
                    "counterarguments": "None",
                    "confidence": 0.8,
                    "categories": [],
                    "related_concepts": [],
                    "sources": [],
                }
            ]
        })
        client.models.generate_content.side_effect = [classify_response, extract_response]

        engine = WikiIngestionEngine(
            wiki_dir=str(tmp_wiki), llm_client=client, combined_analysis=False
        )
        result = engine.ingest_transcript(str(sample_transcript), "2026-04-10")

        assert client.models.generate_content.call_count == 2
        assert "Mixture of Experts" in result["concepts_created"]

    def test_analyze_sections_sequential_when_max_workers_is_one(self, tmp_wiki):
        """max_workers=1 must not spin up an executor (fully sequential)."""
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None, max_workers=1)

        with patch("wiki_engine.ingestion.ThreadPoolExecutor") as mock_executor:
            engine._analyze_sections(["section one", "section two"])
            mock_executor.assert_not_called()

    def test_analyze_sections_ordering_deterministic_with_parallel_workers(self, tmp_wiki):
        """executor.map keeps results in input order, not completion order."""
        section_texts = [f"section-{i}" for i in range(4)]
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None, max_workers=4)
        # Every worker blocks until all have arrived, so completion order is
        # forced to interleave without depending on wall-clock timing.
        barrier = threading.Barrier(len(section_texts))

        def fake_analyze(text):
            idx = int(text.split("-")[1])
            barrier.wait(timeout=10)
            return ClassifiedSection(text=text, category="Other", title=f"Title-{idx}"), []

        with patch.object(engine, "_analyze_section", side_effect=fake_analyze):
            results = engine._analyze_sections(section_texts)

        assert [section.title for section, _ in results] == [
            f"Title-{i}" for i in range(4)
        ]

    def test_extra_classification_field_does_not_drop_concepts(self, tmp_wiki):
        """An unexpected classification key must not discard the parsed concepts."""
        payload = json.loads(_make_analysis_response_text())
        payload["summary"] = "an unexpected extra field"
        client = MagicMock()
        response = MagicMock()
        response.text = json.dumps(payload)
        client.models.generate_content.return_value = response

        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=client)
        section, concepts = engine._analyze_section("Some transcript section text.")

        assert section.category == "AI Architecture"
        assert len(concepts) == 2

    def test_missing_paper_urls_does_not_drop_concepts(self, tmp_wiki):
        """An omitted paper_urls key defaults to [] instead of failing the section."""
        payload = json.loads(_make_analysis_response_text())
        del payload["paper_urls"]
        client = MagicMock()
        response = MagicMock()
        response.text = json.dumps(payload)
        client.models.generate_content.return_value = response

        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=client)
        section, concepts = engine._analyze_section("Some transcript section text.")

        assert section.paper_urls == []
        assert len(concepts) == 2

    def test_analyze_sections_isolates_section_failure(self, tmp_wiki):
        """A section whose analysis raises contributes zero concepts; others unaffected."""
        section_texts = ["good section one", "boom section", "good section two"]
        engine = WikiIngestionEngine(wiki_dir=str(tmp_wiki), llm_client=None, max_workers=2)

        def fake_analyze(text):
            if "boom" in text:
                raise RuntimeError("simulated failure")
            section = ClassifiedSection(text=text, category="Other", title="ok")
            concept = ExtractedConcept(
                name=f"Concept for {text[:4]}", tldr="t", body="b", counterarguments="c"
            )
            return section, [concept]

        with patch.object(engine, "_analyze_section", side_effect=fake_analyze):
            results = engine._analyze_sections(section_texts)

        assert len(results) == 3
        assert results[1][1] == []
        assert len(results[0][1]) == 1
        assert len(results[2][1]) == 1
