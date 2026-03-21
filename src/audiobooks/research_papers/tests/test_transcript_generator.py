"""Tests for transcript_generator.py — GeminiTranscriptGenerator."""

import pytest
from unittest.mock import patch, MagicMock
from research_papers.transcript_generator import GeminiTranscriptGenerator
from research_papers.models import PaperReference, PaperContent
from google.genai import types


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
            category="cs",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12347",
            title="Constrained Optimization via RL",
            abstract="RL framework for constrained optimization.",
            source="arxiv",
            category="stat",
        ),
        PaperReference(
            url="https://arxiv.org/abs/2603.12348",
            title="Matrix Theory Results",
            abstract="New results in random matrix theory.",
            source="arxiv",
            category="math",
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


class TestSummaryTextConstruction:
    """Tests for summary text (no LLM call)."""

    def test_summary_text_includes_titles_and_abstracts(self, generator, summary_papers):
        """Summary text should contain title and abstract for each paper."""
        text = generator._build_summary_text(summary_papers)
        assert "Diffusion Models for Images" in text
        assert "New architectures for diffusion-based generation" in text
        assert "Constrained Optimization via RL" in text
        assert "Matrix Theory Results" in text

    def test_summary_text_grouped_by_category(self, generator, summary_papers):
        """Summary papers should be grouped by category with TTS-friendly headings."""
        text = generator._build_summary_text(summary_papers)
        assert "Computer Science" in text
        assert "Statistics" in text
        assert "Mathematics" in text

    def test_summary_text_empty_for_no_papers(self, generator):
        """Should return empty string when no summary papers."""
        text = generator._build_summary_text([])
        assert text == ""

    def test_summary_text_has_intro_line(self, generator, summary_papers):
        """Summary section should start with a TTS-friendly intro line."""
        text = generator._build_summary_text(summary_papers)
        assert "additional notable papers" in text


class TestPerPaperGeneration:
    """Tests for per-paper deep dive generation."""

    @patch("research_papers.transcript_generator.genai")
    def test_each_paper_gets_own_llm_call(
        self, mock_genai, generator, deep_dive_papers, summary_papers
    ):
        """Each deep-dive paper should trigger its own LLM call (realtime mode)."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Deep dive transcript for this paper."
        mock_client.models.generate_content.return_value = mock_response

        result = generator.generate(
            deep_dive_papers, summary_papers, "2026-03-14"
        )

        # Should be called once per deep-dive paper (2 papers = 2 calls)
        assert mock_client.models.generate_content.call_count == len(deep_dive_papers)

    @patch("research_papers.transcript_generator.genai")
    def test_no_llm_call_for_summary_papers(
        self, mock_genai, generator, summary_papers
    ):
        """Summary papers should NOT trigger any LLM call."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # No deep-dive papers — only summary
        result = generator.generate([], summary_papers, "2026-03-14")

        # No LLM calls should be made
        mock_client.models.generate_content.assert_not_called()
        # But summary text should still be in the result
        assert "Diffusion Models for Images" in result

    @patch("research_papers.transcript_generator.genai")
    def test_output_concatenates_deep_dives_and_summaries(
        self, mock_genai, generator, deep_dive_papers, summary_papers
    ):
        """Final output should be deep-dive transcripts followed by summary text."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # Return different transcripts for each paper
        mock_client.models.generate_content.side_effect = [
            MagicMock(text="Deep dive on Agent-Based Optimization."),
            MagicMock(text="Deep dive on Foundation Model for Code."),
        ]

        result = generator.generate(
            deep_dive_papers, summary_papers, "2026-03-14"
        )

        # Both deep dive transcripts should appear
        assert "Deep dive on Agent-Based Optimization" in result
        assert "Deep dive on Foundation Model for Code" in result
        # Summary text should appear after deep dives
        assert "Diffusion Models for Images" in result
        # Deep dives should come before summaries
        dd_pos = result.index("Deep dive on Agent-Based Optimization")
        summary_pos = result.index("Diffusion Models for Images")
        assert dd_pos < summary_pos

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


class TestBatchMode:
    """Tests for batch API mode."""

    @patch("research_papers.transcript_generator.genai")
    def test_batch_creates_one_job_with_n_requests(self, mock_genai, deep_dive_papers, summary_papers):
        """Batch mode should create a single job with one InlinedRequest per paper."""
        gen = GeminiTranscriptGenerator(
            api_key="test-key",
            model_name="gemini-3.1-pro-preview",
            use_batch=True,
        )

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_genai.types = MagicMock()

        # Mock batch job lifecycle
        mock_batch_job = MagicMock()
        mock_batch_job.name = "batch-123"
        mock_batch_job.state = "JOB_STATE_SUCCEEDED"
        mock_client.batches.create.return_value = mock_batch_job

        # Mock successful state on get
        mock_result = MagicMock()
        mock_result.state = "JOB_STATE_SUCCEEDED"

        # Create mock responses for each paper
        mock_responses = []
        for i in range(len(deep_dive_papers)):
            resp = MagicMock()
            resp.error = None
            resp.response.candidates = [
                MagicMock(content=MagicMock(parts=[MagicMock(text=f"Transcript {i}")]))
            ]
            mock_responses.append(resp)

        mock_result.dest.inlined_responses = mock_responses
        mock_client.batches.get.return_value = mock_result

        # Patch JOB_STATES_SUCCEEDED
        with patch.object(types, "JOB_STATES_SUCCEEDED", {"JOB_STATE_SUCCEEDED"}), \
             patch.object(types, "JOB_STATES_ENDED", {"JOB_STATE_FAILED"}):
            result = gen.generate(deep_dive_papers, summary_papers, "2026-03-14")

        # Batch should be created once (not per paper)
        assert mock_client.batches.create.call_count == 1

        # The batch should contain one InlinedRequest per deep-dive paper
        create_call = mock_client.batches.create.call_args
        src = create_call[1].get("src") or create_call[0][1] if len(create_call[0]) > 1 else create_call[1]["src"]
        assert len(src.inlined_requests) == len(deep_dive_papers)


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
        mock_response.text = "A clean transcript about this paper."
        mock_client.models.generate_content.return_value = mock_response

        result = generator.generate(
            deep_dive_papers, summary_papers, "2026-03-14"
        )

        assert not result.startswith("{")
        assert not result.startswith("[")
        assert "```" not in result
