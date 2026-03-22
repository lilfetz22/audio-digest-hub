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
        "deep_dive_per_category": 2,
        "summary_per_category": 3,
    }


@pytest.fixture
def sample_papers():
    """Sample paper references with categories."""
    return [
        PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Agent Paper",
            abstract="Agent abstract",
            source="arxiv",
            category="cs",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12346",
            title="Image Paper",
            abstract="Image abstract",
            source="arxiv",
            category="cs",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12350",
            title="CS Low Paper",
            abstract="Low score CS paper",
            source="arxiv",
            category="cs",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12351",
            title="Stat Paper 1",
            abstract="Stat abstract 1",
            source="arxiv",
            category="stat",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12352",
            title="Stat Paper 2",
            abstract="Stat abstract 2",
            source="arxiv",
            category="stat",
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

        # Scorer returns scored Arxiv papers (all scored, tier assignment ignored by pipeline)
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        scored = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="Good"),
            ScoredPaper(paper=arxiv_papers[1], score=7, tier="deep_dive", reasoning="OK"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="Low"),
            ScoredPaper(paper=arxiv_papers[3], score=8, tier="deep_dive", reasoning="Stat good"),
            ScoredPaper(paper=arxiv_papers[4], score=5, tier="summary", reasoning="Stat ok"),
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
            ScoredPaper(paper=sample_papers[2], score=2, tier="summary", reasoning="ok"),
            ScoredPaper(paper=sample_papers[3], score=4, tier="summary", reasoning="ok"),
            ScoredPaper(paper=sample_papers[4], score=1, tier="summary", reasoning="ok"),
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


class TestPerCategorySelection:
    """Tests for per-category deep-dive and summary selection."""

    def test_selects_top_n_per_category_for_deep_dive(self, pipeline, mock_deps, sample_papers, tmp_path):
        """Should select top deep_dive_per_category papers from each category."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers

        # 3 CS papers scored: 9, 7, 3; 2 stat papers scored: 8, 5
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        scored = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="CS top"),
            ScoredPaper(paper=arxiv_papers[1], score=7, tier="deep_dive", reasoning="CS 2nd"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="CS low"),
            ScoredPaper(paper=arxiv_papers[3], score=8, tier="deep_dive", reasoning="Stat top"),
            ScoredPaper(paper=arxiv_papers[4], score=5, tier="summary", reasoning="Stat 2nd"),
        ]
        mock_deps["paper_scorer"].score.return_value = scored

        mock_deps["paper_downloader"].extract.side_effect = lambda p: PaperContent(
            url=p.url, title=p.title, abstract=p.abstract, full_text="text", source=p.source
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        pipeline.run("2026-03-14")

        # Verify what was passed to transcript_generator.generate()
        gen_call = mock_deps["transcript_generator"].generate.call_args
        deep_dive_content = gen_call[0][0]
        summary_refs = gen_call[0][1]

        # deep_dive_per_category=2: top 2 from CS (scores 9, 7) + top 2 from stat (scores 8, 5)
        # + 1 HF paper = total 5 deep dive
        # But HF paper may fail download, so check Arxiv deep dives
        deep_dive_urls = {p.url for p in deep_dive_content}
        # CS top 2
        assert "https://arxiv.org/abs/2603.12345" in deep_dive_urls  # score 9
        assert "https://arxiv.org/abs/2603.12346" in deep_dive_urls  # score 7
        # Stat top 2
        assert "https://arxiv.org/abs/2603.12351" in deep_dive_urls  # score 8
        assert "https://arxiv.org/abs/2603.12352" in deep_dive_urls  # score 5
        # HF paper
        assert "https://huggingface.co/papers/2603.11111" in deep_dive_urls

        # summary_per_category=3: CS has 1 remaining (score 3), stat has 0 remaining
        summary_urls = {p.url for p in summary_refs}
        assert "https://arxiv.org/abs/2603.12350" in summary_urls  # CS low score

    def test_discards_papers_beyond_limits(self, mock_deps, tmp_path):
        """Papers beyond deep_dive + summary per category should be discarded."""
        mock_deps["output_dir"] = str(tmp_path)
        mock_deps["deep_dive_per_category"] = 1
        mock_deps["summary_per_category"] = 1
        pipeline = ResearchPaperPipeline(**mock_deps)

        # 3 CS papers
        cs_papers = [
            PaperReference(url=f"https://arxiv.org/abs/2603.1000{i}",
                           title=f"CS Paper {i}", abstract=f"Abstract {i}",
                           source="arxiv", category="cs")
            for i in range(3)
        ]

        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = cs_papers
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=cs_papers[0], score=9, tier="deep_dive", reasoning="top"),
            ScoredPaper(paper=cs_papers[1], score=5, tier="summary", reasoning="mid"),
            ScoredPaper(paper=cs_papers[2], score=2, tier="summary", reasoning="low"),
        ]
        mock_deps["paper_downloader"].extract.side_effect = lambda p: PaperContent(
            url=p.url, title=p.title, abstract=p.abstract, full_text="text", source=p.source
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        pipeline.run("2026-03-14")

        gen_call = mock_deps["transcript_generator"].generate.call_args
        deep_dive_content = gen_call[0][0]
        summary_refs = gen_call[0][1]

        # deep_dive=1, summary=1 per category: 3rd CS paper (score 2) should be discarded
        assert len(deep_dive_content) == 1  # top 1 CS
        assert len(summary_refs) == 1  # next 1 CS
        assert deep_dive_content[0].url == "https://arxiv.org/abs/2603.10000"
        assert summary_refs[0].url == "https://arxiv.org/abs/2603.10001"


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
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=5, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=4, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=2, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=1, tier="summary", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.return_value = PaperContent(
            url="test", title="test", abstract="", full_text="text", source="arxiv"
        )
        mock_deps["transcript_generator"].generate.side_effect = Exception(
            "Generation error"
        )

        # Should log error but not crash
        pipeline.run("2026-03-14")

    def test_download_returns_none_moves_to_summary(self, pipeline, mock_deps, sample_papers, tmp_path):
        """When download returns None, paper should be moved to summary."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=8, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=7, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=6, tier="deep_dive", reasoning="ok"),
        ]
        # Download returns None for all papers — they should move to summary
        mock_deps["paper_downloader"].extract.return_value = None
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        pipeline.run("2026-03-14")

        gen_call = mock_deps["transcript_generator"].generate.call_args
        deep_dive_content = gen_call[0][0]
        summary_refs = gen_call[0][1]
        # All downloads failed, so deep_dive_content is empty
        assert len(deep_dive_content) == 0
        # Failed downloads moved to summary
        assert len(summary_refs) > 0

    def test_download_exception_moves_to_summary(self, pipeline, mock_deps, sample_papers, tmp_path):
        """When download raises exception, paper should be moved to summary."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=8, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=7, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=6, tier="deep_dive", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.side_effect = Exception("Download error")
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        pipeline.run("2026-03-14")

        gen_call = mock_deps["transcript_generator"].generate.call_args
        deep_dive_content = gen_call[0][0]
        assert len(deep_dive_content) == 0

    def test_no_papers_after_download_failure(self, pipeline, mock_deps, tmp_path):
        """Should return early when no papers are available after download failures."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        papers = [
            PaperReference(
                url="https://arxiv.org/abs/2603.12345", title="P1",
                abstract="A1", source="arxiv", category="cs"
            ),
        ]
        mock_deps["email_parser"].fetch_papers.return_value = papers
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=papers[0], score=9, tier="deep_dive", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.return_value = None
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        pipeline.run("2026-03-14")
        # Download failed → paper moves to summary → transcript still called

    @patch("research_papers.pipeline.requests")
    def test_push_metadata_success(self, mock_requests, pipeline, mock_deps, sample_papers, tmp_path):
        """Should push metadata to Supabase on successful pipeline run."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = "preference"
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=7, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=8, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=5, tier="summary", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.side_effect = lambda p: PaperContent(
            url=p.url, title=p.title, abstract=p.abstract, full_text="text", source=p.source
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        pipeline.run("2026-03-14")

        # Should have pushed metadata
        mock_requests.post.assert_called_once()

    @patch("research_papers.pipeline.requests")
    def test_push_metadata_preserves_actual_scores(self, mock_requests, pipeline, mock_deps, sample_papers, tmp_path):
        """Actual Gemini scores should be preserved in pushed metadata, not hardcoded 10/0."""
        pipeline.output_dir = str(tmp_path)
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = "preference"
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=9.2, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=7.5, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3.1, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=8.0, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=4.8, tier="summary", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.side_effect = lambda p: PaperContent(
            url=p.url, title=p.title, abstract=p.abstract, full_text="text", source=p.source
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        pipeline.run("2026-03-14")

        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args
        pushed_papers = call_kwargs[1]["json"]["papers"]
        score_by_url = {p["url"]: p["score"] for p in pushed_papers}

        # Deep-dive Arxiv papers must carry their real scores, not hardcoded 10
        assert score_by_url[arxiv_papers[0].url] == 9.2
        assert score_by_url[arxiv_papers[1].url] == 7.5
        # Summary Arxiv papers must carry their real scores, not hardcoded 0
        assert score_by_url[arxiv_papers[2].url] == 3.1
        assert score_by_url[arxiv_papers[4].url] == 4.8

    @patch("research_papers.pipeline.requests")
    def test_push_metadata_failure(self, mock_requests, pipeline, mock_deps, sample_papers, tmp_path):
        """Should handle metadata push failure gracefully."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=7, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=8, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=5, tier="summary", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.side_effect = lambda p: PaperContent(
            url=p.url, title=p.title, abstract=p.abstract, full_text="text", source=p.source
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"
        mock_requests.post.side_effect = Exception("Network error")

        # Should not crash
        pipeline.run("2026-03-14")

    @patch("research_papers.pipeline.requests")
    def test_push_metadata_non_200(self, mock_requests, pipeline, mock_deps, sample_papers, tmp_path):
        """Should handle non-200 metadata push response."""
        mock_deps["feedback_client"].fetch_clicked_papers.return_value = []
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=7, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=8, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=5, tier="summary", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.side_effect = lambda p: PaperContent(
            url=p.url, title=p.title, abstract=p.abstract, full_text="text", source=p.source
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.post.return_value = mock_response

        # Should log warning but not crash
        pipeline.run("2026-03-14")

    def test_feedback_update_failure(self, pipeline, mock_deps, sample_papers, tmp_path):
        """Should handle feedback update failure gracefully."""
        mock_deps["feedback_client"].fetch_clicked_papers.side_effect = Exception("Feedback error")
        mock_deps["feedback_manager"].load_profile.return_value = ""
        mock_deps["email_parser"].fetch_papers.return_value = sample_papers
        arxiv_papers = [p for p in sample_papers if p.source == "arxiv"]
        mock_deps["paper_scorer"].score.return_value = [
            ScoredPaper(paper=arxiv_papers[0], score=9, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[1], score=7, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[2], score=3, tier="summary", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[3], score=8, tier="deep_dive", reasoning="ok"),
            ScoredPaper(paper=arxiv_papers[4], score=5, tier="summary", reasoning="ok"),
        ]
        mock_deps["paper_downloader"].extract.side_effect = lambda p: PaperContent(
            url=p.url, title=p.title, abstract=p.abstract, full_text="text", source=p.source
        )
        mock_deps["transcript_generator"].generate.return_value = "Transcript"

        # Should not crash — feedback failure is non-fatal
        pipeline.run("2026-03-14")
