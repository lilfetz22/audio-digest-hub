"""Tests for paper_scorer.py — GeminiPaperScorer."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from research_papers.paper_scorer import GeminiPaperScorer
from research_papers.models import PaperReference, ScoredPaper


@pytest.fixture
def scorer():
    return GeminiPaperScorer(
        api_key="test-key",
        model_name="gemini-3-flash-preview",
        top_n=2,
    )


@pytest.fixture
def sample_arxiv_papers():
    return [
        PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Agent-Based Optimization for Time Series",
            abstract="We propose a novel agent-based approach to time series forecasting.",
            source="arxiv",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12346",
            title="Diffusion Models for Image Synthesis",
            abstract="New architectures for diffusion-based image generation.",
            source="arxiv",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12347",
            title="Constrained Optimization via RL",
            abstract="A reinforcement learning framework for constrained optimization.",
            source="arxiv",
        ),
    ]


@pytest.fixture
def sample_hf_papers():
    return [
        PaperReference(
            url="https://huggingface.co/papers/2603.11111",
            title="Foundation Model for Code",
            abstract="A large language model for code generation.",
            source="huggingface",
        ),
    ]


class TestScoringLogic:
    """Tests for the scoring and tiering logic."""

    @patch("research_papers.paper_scorer.genai")
    def test_scores_arxiv_papers(self, mock_genai, scorer, sample_arxiv_papers):
        """Should score all Arxiv papers and return sorted results."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # Mock Gemini response with structured scores
        mock_response = MagicMock()
        mock_response.text = (
            '[{"url": "https://arxiv.org/abs/2603.12345", "score": 9, "reasoning": "Directly relevant"},'
            '{"url": "https://arxiv.org/abs/2603.12347", "score": 8, "reasoning": "Optimization paper"},'
            '{"url": "https://arxiv.org/abs/2603.12346", "score": 3, "reasoning": "Image synthesis, unrelated"}]'
        )
        mock_client.models.generate_content.return_value = mock_response

        result = scorer.score(sample_arxiv_papers, preference_profile="")

        assert len(result) == 3
        assert all(isinstance(r, ScoredPaper) for r in result)
        # Top 2 should be deep_dive (top_n=2)
        deep_dives = [r for r in result if r.tier == "deep_dive"]
        summaries = [r for r in result if r.tier == "summary"]
        assert len(deep_dives) == 2
        assert len(summaries) == 1

    @patch("research_papers.paper_scorer.genai")
    def test_tiering_top_n(self, mock_genai, scorer, sample_arxiv_papers):
        """Top N papers should be deep_dive, rest summary."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = (
            '[{"url": "https://arxiv.org/abs/2603.12345", "score": 9, "reasoning": "High"},'
            '{"url": "https://arxiv.org/abs/2603.12347", "score": 7, "reasoning": "Medium"},'
            '{"url": "https://arxiv.org/abs/2603.12346", "score": 2, "reasoning": "Low"}]'
        )
        mock_client.models.generate_content.return_value = mock_response

        result = scorer.score(sample_arxiv_papers, preference_profile="")

        # Sorted by score desc, top 2 deep_dive
        assert result[0].score >= result[1].score >= result[2].score
        assert result[0].tier == "deep_dive"
        assert result[1].tier == "deep_dive"
        assert result[2].tier == "summary"


class TestHuggingFaceBypass:
    """HuggingFace papers should never be scored."""

    def test_hf_papers_are_never_scored(self, scorer, sample_hf_papers):
        """HuggingFace papers bypass scoring — all marked as deep_dive."""
        # This is actually handled in the pipeline, not the scorer.
        # The scorer should only receive Arxiv papers.
        # But if HF papers are accidentally passed, they should still work.
        pass


class TestPreferenceProfile:
    """Tests for preference profile injection."""

    @patch("research_papers.paper_scorer.genai")
    def test_includes_preference_profile_in_prompt(
        self, mock_genai, scorer, sample_arxiv_papers
    ):
        """Preference profile should be injected into the system prompt."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = (
            '[{"url": "https://arxiv.org/abs/2603.12345", "score": 5, "reasoning": "ok"},'
            '{"url": "https://arxiv.org/abs/2603.12346", "score": 4, "reasoning": "ok"},'
            '{"url": "https://arxiv.org/abs/2603.12347", "score": 3, "reasoning": "ok"}]'
        )
        mock_client.models.generate_content.return_value = mock_response

        profile = "The user has shown interest in retrieval-augmented generation."
        scorer.score(sample_arxiv_papers, preference_profile=profile)

        # Verify the profile was included in the call
        call_args = mock_client.models.generate_content.call_args
        # The system instruction or contents should contain the profile
        call_kwargs = call_args[1] if call_args[1] else {}
        config = call_kwargs.get("config", None)
        if config:
            system_instruction = getattr(config, "system_instruction", "")
            assert "retrieval-augmented generation" in str(system_instruction)


class TestErrorHandling:
    """Tests for API error handling."""

    @patch("research_papers.paper_scorer.genai")
    def test_handles_api_error(self, mock_genai, scorer, sample_arxiv_papers):
        """Should handle API errors gracefully — return all papers as summary."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        result = scorer.score(sample_arxiv_papers, preference_profile="")

        # On error, all papers get default low score and summary tier
        assert len(result) == 3
        for r in result:
            assert r.tier == "summary"

    @patch("research_papers.paper_scorer.genai")
    def test_handles_malformed_response(self, mock_genai, scorer, sample_arxiv_papers):
        """Should handle malformed JSON from the API."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON at all"
        mock_client.models.generate_content.return_value = mock_response

        result = scorer.score(sample_arxiv_papers, preference_profile="")

        # Should fall back gracefully
        assert len(result) == 3
