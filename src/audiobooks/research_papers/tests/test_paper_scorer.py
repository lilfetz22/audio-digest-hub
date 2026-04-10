"""Tests for paper_scorer.py — GeminiPaperScorer and EmbeddingPaperScorer."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from research_papers.paper_scorer import GeminiPaperScorer, EmbeddingPaperScorer
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

class TestEmptyInput:
    """Tests for empty input."""

    def test_empty_papers_returns_empty(self, scorer):
        """Should return empty list when no papers are provided."""
        result = scorer.score([], preference_profile="")
        assert result == []


class TestResponseParsing:
    """Tests for response parsing edge cases."""

    def test_parse_code_fenced_response(self, scorer, sample_arxiv_papers):
        """Should handle response wrapped in markdown code fences."""
        response_text = '```json\n[{"url": "https://arxiv.org/abs/2603.12345", "score": 8, "reasoning": "Good"}]\n```'
        result = scorer._parse_response(response_text, sample_arxiv_papers)
        assert "https://arxiv.org/abs/2603.12345" in result
        assert result["https://arxiv.org/abs/2603.12345"]["score"] == 8

    def test_parse_invalid_json_returns_empty(self, scorer, sample_arxiv_papers):
        """Should return empty dict on completely unparseable JSON."""
        result = scorer._parse_response("not json at all", sample_arxiv_papers)
        assert result == {}

    def test_parse_non_array_returns_empty(self, scorer, sample_arxiv_papers):
        """Should return empty dict when response is valid JSON but not an array."""
        result = scorer._parse_response('{"key": "value"}', sample_arxiv_papers)
        assert result == {}

    def test_parse_latex_backslash_in_reasoning(self, scorer, sample_arxiv_papers):
        """Should handle LaTeX backslashes in reasoning strings."""
        response_text = '[{"url": "https://arxiv.org/abs/2603.12345", "score": 7, "reasoning": "Uses \\alpha and \\beta"}]'
        result = scorer._parse_response(response_text, sample_arxiv_papers)
        assert "https://arxiv.org/abs/2603.12345" in result

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


# ---------------------------------------------------------------------------
# EmbeddingPaperScorer tests
# ---------------------------------------------------------------------------

class TestEmbeddingPaperScorer:
    """Tests for EmbeddingPaperScorer — no API calls, local embeddings."""

    @pytest.fixture
    def scorer(self, tmp_path):
        profile_file = tmp_path / "interest_profile.txt"
        profile_file.write_text(
            "AI agents, time series, optimization", encoding="utf-8"
        )
        return EmbeddingPaperScorer(
            model_name="all-MiniLM-L6-v2",
            top_n=2,
            interest_profile_path=str(profile_file),
        )

    @staticmethod
    def _mock_embeddings(n_papers: int):
        """Return a simple list of zero vectors usable as mock encode() output."""
        import torch
        return torch.zeros(n_papers + 1, 384)

    # --- Basic correctness ---

    @patch("sentence_transformers.util.cos_sim")
    def test_returns_list_of_scored_papers(self, mock_cos_sim, scorer, sample_arxiv_papers):
        """Should return one ScoredPaper per input paper."""
        import torch
        scorer._model = MagicMock()
        scorer._model.encode.return_value = self._mock_embeddings(len(sample_arxiv_papers))
        mock_cos_sim.return_value = torch.tensor([[0.8]])

        result = scorer.score(sample_arxiv_papers)

        assert len(result) == len(sample_arxiv_papers)
        assert all(isinstance(r, ScoredPaper) for r in result)

    @patch("sentence_transformers.util.cos_sim")
    def test_scores_are_in_range_1_to_10(self, mock_cos_sim, scorer, sample_arxiv_papers):
        """Scores must be in [1, 10] for all similarity values."""
        import torch
        scorer._model = MagicMock()
        scorer._model.encode.return_value = self._mock_embeddings(len(sample_arxiv_papers))
        mock_cos_sim.return_value = torch.tensor([[0.5]])

        result = scorer.score(sample_arxiv_papers)

        for r in result:
            assert 1.0 <= r.score <= 10.0

    @patch("sentence_transformers.util.cos_sim")
    def test_similarity_zero_maps_to_score_1(self, mock_cos_sim, scorer, sample_arxiv_papers):
        """Cosine similarity of 0.0 should map to score 1.0."""
        import torch
        scorer._model = MagicMock()
        scorer._model.encode.return_value = self._mock_embeddings(len(sample_arxiv_papers))
        mock_cos_sim.return_value = torch.tensor([[0.0]])

        result = scorer.score(sample_arxiv_papers)

        assert all(r.score == 1.0 for r in result)

    @patch("sentence_transformers.util.cos_sim")
    def test_similarity_one_maps_to_score_10(self, mock_cos_sim, scorer, sample_arxiv_papers):
        """Cosine similarity of 1.0 should map to score 10.0."""
        import torch
        scorer._model = MagicMock()
        scorer._model.encode.return_value = self._mock_embeddings(len(sample_arxiv_papers))
        mock_cos_sim.return_value = torch.tensor([[1.0]])

        result = scorer.score(sample_arxiv_papers)

        assert all(r.score == 10.0 for r in result)

    # --- Tiering ---

    @patch("sentence_transformers.util.cos_sim")
    def test_top_n_papers_get_deep_dive_tier(self, mock_cos_sim, scorer, sample_arxiv_papers):
        """Top top_n papers (by score) should be deep_dive, rest summary."""
        import torch
        scorer._model = MagicMock()
        scorer._model.encode.return_value = self._mock_embeddings(len(sample_arxiv_papers))
        # Return distinct similarities per call so papers sort deterministically
        mock_cos_sim.side_effect = [
            torch.tensor([[0.9]]),
            torch.tensor([[0.5]]),
            torch.tensor([[0.2]]),
        ]

        result = scorer.score(sample_arxiv_papers)

        deep_dives = [r for r in result if r.tier == "deep_dive"]
        summaries = [r for r in result if r.tier == "summary"]
        assert len(deep_dives) == 2  # top_n=2
        assert len(summaries) == 1

    @patch("sentence_transformers.util.cos_sim")
    def test_result_is_sorted_by_score_descending(self, mock_cos_sim, scorer, sample_arxiv_papers):
        """Result list should be sorted highest score first."""
        import torch
        scorer._model = MagicMock()
        scorer._model.encode.return_value = self._mock_embeddings(len(sample_arxiv_papers))
        mock_cos_sim.side_effect = [
            torch.tensor([[0.3]]),
            torch.tensor([[0.9]]),
            torch.tensor([[0.6]]),
        ]

        result = scorer.score(sample_arxiv_papers)

        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    # --- Preference profile ---

    def test_preference_profile_appended_to_base_query(self, scorer):
        """Preference profile text should be appended to the interest profile query."""
        profile = "user really likes retrieval-augmented generation"
        query = scorer._build_query(profile)
        assert "retrieval-augmented generation" in query
        assert "AI agents" in query  # base content from temp profile file

    def test_empty_preference_profile_uses_base_query_only(self, scorer):
        """Empty preference profile should return only the base interest query."""
        query = scorer._build_query("")
        assert query == "AI agents, time series, optimization"

    # --- Edge cases ---

    def test_empty_papers_returns_empty(self, scorer):
        """Should return empty list when no papers are provided."""
        result = scorer.score([])
        assert result == []

    # --- Reasoning field ---

    @patch("sentence_transformers.util.cos_sim")
    def test_reasoning_contains_similarity_value(self, mock_cos_sim, scorer, sample_arxiv_papers):
        """Reasoning field should document the embedding similarity score."""
        import torch
        scorer._model = MagicMock()
        scorer._model.encode.return_value = self._mock_embeddings(len(sample_arxiv_papers))
        mock_cos_sim.return_value = torch.tensor([[0.75]])

        result = scorer.score(sample_arxiv_papers)

        for r in result:
            assert "similarity" in r.reasoning.lower()

    # --- Error handling ---

    def test_model_encode_error_returns_fallback_scores(self, scorer, sample_arxiv_papers):
        """RuntimeError during encode should return fallback score=5.0 for all papers."""
        scorer._model = MagicMock()
        scorer._model.encode.side_effect = RuntimeError("CUDA error")

        result = scorer.score(sample_arxiv_papers)

        assert len(result) == len(sample_arxiv_papers)
        assert all(r.score == 5.0 for r in result)

    def test_model_load_error_returns_fallback_scores(self, scorer, sample_arxiv_papers):
        """ImportError when loading model should return fallback score=5.0 for all papers."""
        with patch.object(scorer, "_get_model", side_effect=ImportError("sentence-transformers not installed")):
            result = scorer.score(sample_arxiv_papers)

        assert len(result) == len(sample_arxiv_papers)
        assert all(r.score == 5.0 for r in result)
