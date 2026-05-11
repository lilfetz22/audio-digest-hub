"""Tests for transcript_generator.py — GeminiTranscriptGenerator."""

import pytest
import time
from unittest.mock import patch, MagicMock
from research_papers.transcript_generator import GeminiTranscriptGenerator
from research_papers.models import PaperContent


@pytest.fixture
def generator():
    return GeminiTranscriptGenerator(
        api_key="test-key",
        model_name="gemini-3.1-flash-lite-preview",
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


class TestPromptConstruction:
    """Tests for prompt construction."""

    def test_single_paper_prompt_includes_full_text(self, generator, deep_dive_papers):
        """Each single-paper prompt should include the full text."""
        prompt = generator._build_single_paper_prompt(
            deep_dive_papers[0], "2026-03-14"
        )
        assert "Full paper text about agent-based optimization" in prompt
        assert "Agent-Based Optimization" in prompt
        assert "2026-03-14" in prompt

    def test_single_paper_prompt_includes_metadata(self, generator, deep_dive_papers):
        """Single-paper prompt should include source, URL, abstract."""
        prompt = generator._build_single_paper_prompt(
            deep_dive_papers[0], "2026-03-14"
        )
        assert "arxiv" in prompt
        assert "https://arxiv.org/abs/2603.12345" in prompt
        assert "Novel agent-based approach" in prompt


class TestPerPaperGeneration:
    """Tests for per-paper deep dive generation."""

    @patch("research_papers.gemini_client.genai")
    def test_each_paper_gets_own_llm_call(
        self, mock_genai, generator, deep_dive_papers
    ):
        """Each deep-dive paper should trigger its own sequential LLM call."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Deep dive transcript for this paper."
        mock_client.models.generate_content.return_value = mock_response

        result = generator.generate(deep_dive_papers, "2026-03-14")

        # Should be called once per deep-dive paper plus once for interrogator episode
        assert mock_client.models.generate_content.call_count == len(deep_dive_papers) + 1

    @patch("research_papers.gemini_client.genai")
    def test_empty_deep_dive_returns_empty_string(
        self, mock_genai, generator
    ):
        """With no deep-dive papers, should return an empty string without LLM calls."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        result = generator.generate([], "2026-03-14")

        mock_client.models.generate_content.assert_not_called()
        assert result == ""

    @patch("research_papers.gemini_client.genai")
    def test_output_concatenates_deep_dives(
        self, mock_genai, generator, deep_dive_papers
    ):
        """Final output should concatenate all deep-dive transcripts."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # Return different transcripts for each paper, plus one for the interrogator
        mock_client.models.generate_content.side_effect = [
            MagicMock(text="Deep dive on Agent-Based Optimization."),
            MagicMock(text="Deep dive on Foundation Model for Code."),
            MagicMock(text="Interrogator episode text."),
        ]

        result = generator.generate(deep_dive_papers, "2026-03-14")

        # Both deep dive transcripts should appear
        assert "Deep dive on Agent-Based Optimization" in result
        assert "Deep dive on Foundation Model for Code" in result

    @patch("research_papers.gemini_client.genai")
    def test_handles_api_error(
        self, mock_genai, generator, deep_dive_papers
    ):
        """Should raise on API error (pipeline handles the exception)."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        with pytest.raises(Exception):
            generator.generate(deep_dive_papers, "2026-03-14")


class TestRateLimiting:
    """Tests for rate limiting logic."""

    def test_rate_limiter_tracks_requests(self, generator):
        """Rate limiter should track request timestamps."""
        generator._request_timestamps = []
        generator._wait_for_rate_limit(estimated_tokens=100)
        assert len(generator._request_timestamps) == 1

    def test_rate_limiter_allows_requests_under_limit(self, generator):
        """Should allow requests when under the RPM limit."""
        generator._request_timestamps = [time.time()] * 10  # 10 recent requests
        generator._token_usage = []
        # Should not block — 10 < 15
        generator._wait_for_rate_limit(estimated_tokens=100)
        assert len(generator._request_timestamps) == 11

    def test_rate_limiter_prunes_old_timestamps(self, generator):
        """Should prune timestamps older than 60 seconds."""
        old_time = time.time() - 120  # 2 minutes ago
        generator._request_timestamps = [old_time] * 5
        generator._token_usage = [(old_time, 1000)] * 5
        generator._wait_for_rate_limit(estimated_tokens=100)
        # Old entries should be pruned, only the new request remains
        assert len(generator._request_timestamps) == 1
        assert len(generator._token_usage) == 0

    def test_record_usage_appends(self, generator):
        """_record_usage should append to token_usage list."""
        generator._token_usage = []
        generator._record_usage(5000)
        assert len(generator._token_usage) == 1
        assert generator._token_usage[0][1] == 5000


class TestOutputFormatting:
    """Tests for output formatting."""

    @patch("research_papers.gemini_client.genai")
    def test_output_is_clean_text(
        self, mock_genai, generator, deep_dive_papers
    ):
        """Output should be clean transcript text without JSON or code blocks."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "A clean transcript about this paper."
        mock_client.models.generate_content.return_value = mock_response

        result = generator.generate(deep_dive_papers, "2026-03-14")

        assert not result.startswith("{")
        assert not result.startswith("[")
        assert "```" not in result
