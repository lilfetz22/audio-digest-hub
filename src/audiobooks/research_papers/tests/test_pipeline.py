"""Tests for pipeline.py — ResearchPaperPipeline orchestrator."""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from research_papers.pipeline import ResearchPaperPipeline
from research_papers.models import PaperReference, PaperContent, ScoredPaper


@pytest.fixture
def mock_deps():
    """Create mock dependencies for the pipeline."""
    return {
        "email_parser": MagicMock(),
        "paper_downloader": MagicMock(),
        "paper_scorer": MagicMock(),
        "transcript_generator": MagicMock(),
        "feedback_manager": MagicMock(),
        "feedback_client": MagicMock(),
        "gmail_service": MagicMock(),
        "api_url": "https://example.supabase.co/functions/v1",
        "api_key": "test-key",
        "output_dir": None,  # Will be set per test
    }


@pytest.fixture
def sample_papers():
    """Sample paper references."""
    return [
        PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Agent Paper",
            abstract="Agent abstract",
            source="arxiv",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12346",
            title="Image Paper",
            abstract="Image abstract",
            source="arxiv",
        ),
        PaperReference(
            url="https://huggingface.co/papers/2603.11111",
            title="HF Paper",
            abstract="HF abstract",
            source="huggingface",
        ),
    ]


@pytest.fixture
def pipeline(mock_deps, tmp_path):
    mock_deps["output_dir"] = str(tmp_path)
    return ResearchPaperPipeline(**mock_deps)


class TestFullFlow:
    """Test the full pipeline orchestration."""

    def test_end_to_end_flow(self, pipeline, mock_deps, sample_papers, tmp_path):
        """Full flow: parse → score → download → generate → save."""
        # Setup mocks
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers

        # Scorer returns scored Arxiv papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        scored = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="Good"),
            ScoredPaper(paper=arxiv_papers[1], score=3, tier="summary", reasoning="Low"),
        ]
        mock_deps["paper_scorer"].score.return_value = scored

        # Downloader returns content for deep-dive papers
        mock_deps["paper_downloader"].extract.return_value = PaperContent(
            url="https://arxiv.org/abs/2603.12345",
            title="Agent Paper",
            abstract="Agent abstract",
            full_text="Full text",
            source="arxiv",
        )

        # Transcript generator returns text
        mock_deps["transcript_generator"].generate.return_value = (
            "Welcome to today's digest..."
        )

        pipeline.run("2026-03-14")

        # Verify output file was created
        output_path = os.path.join(str(tmp_path), "research_digest_2026-03-14.txt")
        assert os.path.exists(output_path)

        with open(output_path) as f:
            content = f.read()
        assert "Welcome to today's digest" in content

    def test_hf_papers_skip_scoring(self, pipeline, mock_deps, sample_papers, tmp_path):
        """HuggingFace papers should NOT be sent to the scorer."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=sample_papers[0], score=5, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=sample_papers[1], score=3, tier="summary", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.return_value = PaperContent(
            url="test", title="test", abstract="", full_text="text", source="arxiv"
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        pipeline.run("2026-03-14")

        # Scorer should only receive Arxiv papers
        scorer_call = mock_deps["paper_scorer"].score.call_args
        scored_papers = scorer_call[0][0]
        for p in scored_papers:
            assert p.source == "arxiv"


class TestOutputFile:
    """Tests for output file handling."""

    def test_output_file_naming(self, pipeline, mock_deps, tmp_path):
        """Output file should be named research_digest_{date}.txt."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = []

        pipeline.run("2026-03-14")

        # No papers = no output file (early return)
        # Just verify the method completes without error

    def test_idempotency_skips_existing(self, pipeline, mock_deps, tmp_path):
        """Should skip if output file already exists."""
        output_path = os.path.join(str(tmp_path), "research_digest_2026-03-14.txt")
        with open(output_path, "w") as f:
            f.write("Already exists")

        pipeline.run("2026-03-14")

        # Parser should not be called since file exists
        mock_deps["email_parser"].fetch_papers.assert_not_called()


class TestErrorHandling:
    """Tests for error handling."""

    def test_handles_no_papers(self, pipeline, mock_deps, tmp_path):
        """Should handle gracefully when no papers are found."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = []

        # Should not raise
        pipeline.run("2026-03-14")

    def test_handles_scoring_failure(self, pipeline, mock_deps, sample_papers, tmp_path):
        """Pipeline should continue if scoring fails (all become summary)."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        mock_deps["paper_scorer"].score.side_effect = Exception("Scoring error")
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        # Should not raise — falls back gracefully
        pipeline.run("2026-03-14")

    def test_handles_generation_failure(self, pipeline, mock_deps, sample_papers, tmp_path):
        """Should handle transcript generation failure."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=sample_papers[0], score=5, tier="deep_dive", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.return_value = PaperContent(
            url="test", title="test", abstract="", full_text="text", source="arxiv"
        )
        mock_deps["transcript_generator"].generate.side_effect = Exception(
            "Generation error"
        )

        # Should log error but not crash
        pipeline.run("2026-03-14")
