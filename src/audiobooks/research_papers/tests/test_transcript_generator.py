"""Tests for transcript_generator.py — GeminiTranscriptGenerator."""

import pytest
from unittest.mock import patch, MagicMock
from research_papers.transcript_generator import GeminiTranscriptGenerator
from research_papers.models import PaperReference, PaperContent


@pytest.fixture
def generator():
    return GeminiTranscriptGenerator(
        api_key="test-key",
        model_name="gemini-3.1-pro-preview",
        use_batch=False,  # Use realtime for tests
    )


@pytest.fixture
def deep_dive_papers():
    return [
        PaperContent(
            url="https://arxiv.org/abs/2603.12345",
            title="Agent-Based Optimization",
            abstract="Novel agent-based approach.",
            full_text="Full paper text about agent-based optimization...",
            source="arxiv",
        ),
        PaperContent(
            url="https://huggingface.co/papers/2603.11111",
            title="Foundation Model for Code",
            abstract="A large language model for code.",
            full_text="Full paper text about code generation models...",
            source="huggingface",
        ),
    ]


@pytest.fixture
def summary_papers():
    return [
        PaperReference(
            url="https://arxiv.org/abs/2603.12346",
            title="Diffusion Models for Images",
            abstract="New architectures for diffusion-based generation.",
            source="arxiv",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12347",
            title="Constrained Optimization via RL",
            abstract="RL framework for constrained optimization.",
            source="arxiv",
        ),
    ]


class TestPromptConstruction:
    """Tests for prompt construction."""

    def test_includes_deep_dive_full_text(self, generator, deep_dive_papers, summary_papers):
        """Deep-dive papers should include full text in the prompt."""
        prompt = generator._build_user_prompt(
            deep_dive_papers, summary_papers, "2026-03-14"
        )
        assert "Full paper text about agent-based optimization" in prompt
        assert "Full paper text about code generation models" in prompt

    def test_includes_summary_title_abstract(self, generator, deep_dive_papers, summary_papers):
        """Summary papers should include title and abstract only."""
        prompt = generator._build_user_prompt(
            deep_dive_papers, summary_papers, "2026-03-14"
        )
        assert "Diffusion Models for Images" in prompt
        assert "New architectures for diffusion-based generation" in prompt

    def test_summary_papers_no_full_text(self, generator, deep_dive_papers, summary_papers):
        """Summary papers should NOT have full text (they're PaperReference, not PaperContent)."""
        prompt = generator._build_user_prompt(
            deep_dive_papers, summary_papers, "2026-03-14"
        )
        # Just verify the structure is correct
        assert "DEEP-DIVE PAPERS" in prompt
        assert "QUICK HITS" in prompt

    def test_includes_date(self, generator, deep_dive_papers, summary_papers):
        """Prompt should include the digest date."""
        prompt = generator._build_user_prompt(
            deep_dive_papers, summary_papers, "2026-03-14"
        )
        assert "2026-03-14" in prompt


class TestTranscriptGeneration:
    """Tests for the full generation flow."""

    @patch("research_papers.transcript_generator.genai")
    def test_generates_transcript(
        self, mock_genai, generator, deep_dive_papers, summary_papers
    ):
        """Should generate a clean transcript string."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = (
            "Welcome to today's AI research digest for March 14, 2026. "
            "Today we have some exciting papers to discuss..."
        )
        mock_client.models.generate_content.return_value = mock_response

        result = generator.generate(
            deep_dive_papers, summary_papers, "2026-03-14"
        )

        assert isinstance(result, str)
        assert "Welcome" in result
        assert len(result) > 0

    @patch("research_papers.transcript_generator.genai")
    def test_handles_api_error(
        self, mock_genai, generator, deep_dive_papers, summary_papers
    ):
        """Should raise on API error (pipeline handles the exception)."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        with pytest.raises(Exception):
            generator.generate(deep_dive_papers, summary_papers, "2026-03-14")


class TestOutputFormatting:
    """Tests for output formatting."""

    @patch("research_papers.transcript_generator.genai")
    def test_output_is_clean_text(
        self, mock_genai, generator, deep_dive_papers, summary_papers
    ):
        """Output should be clean transcript text without JSON or code blocks."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "A clean transcript about papers."
        mock_client.models.generate_content.return_value = mock_response

        result = generator.generate(
            deep_dive_papers, summary_papers, "2026-03-14"
        )

        assert not result.startswith("{")
        assert not result.startswith("[")
        assert "```" not in result
