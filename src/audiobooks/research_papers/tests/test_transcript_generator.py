"""Tests for transcript_generator.py — GeminiTranscriptGenerator."""

import pytest
from unittest.mock import patch, MagicMock
from research_papers.transcript_generator import GeminiTranscriptGenerator
from research_papers.models import PaperContent
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

    @patch("research_papers.transcript_generator.genai")
    def test_each_paper_gets_own_llm_call(
        self, mock_genai, generator, deep_dive_papers
    ):
        """Each deep-dive paper should trigger its own LLM call (realtime mode)."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Deep dive transcript for this paper."
        mock_client.models.generate_content.return_value = mock_response

        result = generator.generate(deep_dive_papers, "2026-03-14")

        # Should be called once per deep-dive paper (2 papers = 2 calls)
        assert mock_client.models.generate_content.call_count == len(deep_dive_papers)

    @patch("research_papers.transcript_generator.genai")
    def test_empty_deep_dive_returns_empty_string(
        self, mock_genai, generator
    ):
        """With no deep-dive papers, should return an empty string without LLM calls."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        result = generator.generate([], "2026-03-14")

        mock_client.models.generate_content.assert_not_called()
        assert result == ""

    @patch("research_papers.transcript_generator.genai")
    def test_output_concatenates_deep_dives(
        self, mock_genai, generator, deep_dive_papers
    ):
        """Final output should concatenate all deep-dive transcripts."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # Return different transcripts for each paper
        mock_client.models.generate_content.side_effect = [
            MagicMock(text="Deep dive on Agent-Based Optimization."),
            MagicMock(text="Deep dive on Foundation Model for Code."),
        ]

        result = generator.generate(deep_dive_papers, "2026-03-14")

        # Both deep dive transcripts should appear
        assert "Deep dive on Agent-Based Optimization" in result
        assert "Deep dive on Foundation Model for Code" in result

    @patch("research_papers.transcript_generator.genai")
    def test_handles_api_error(
        self, mock_genai, generator, deep_dive_papers
    ):
        """Should raise on API error (pipeline handles the exception)."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        with pytest.raises(Exception):
            generator.generate(deep_dive_papers, "2026-03-14")


class TestBatchMode:
    """Tests for batch API mode."""

    @patch("research_papers.transcript_generator.genai")
    def test_batch_creates_one_job_with_n_requests(self, mock_genai, deep_dive_papers):
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
            result = gen.generate(deep_dive_papers, "2026-03-14")

        # Batch should be created once (not per paper)
        assert mock_client.batches.create.call_count == 1

        # The batch should contain one InlinedRequest per deep-dive paper
        create_call = mock_client.batches.create.call_args
        src = create_call[1].get("src") or create_call[0][1] if len(create_call[0]) > 1 else create_call[1]["src"]
        assert len(src.inlined_requests) == len(deep_dive_papers)


class TestBatchErrorHandling:
    """Tests for batch mode error handling."""

    @patch("research_papers.transcript_generator.genai")
    def test_batch_handles_error_response(self, mock_genai, deep_dive_papers):
        """Should handle individual batch request errors gracefully."""
        gen = GeminiTranscriptGenerator(
            api_key="test-key",
            model_name="gemini-3.1-pro-preview",
            use_batch=True,
        )

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_batch_job = MagicMock()
        mock_batch_job.name = "batch-err"
        mock_batch_job.state = "JOB_STATE_SUCCEEDED"
        mock_client.batches.create.return_value = mock_batch_job

        mock_result = MagicMock()
        mock_result.state = "JOB_STATE_SUCCEEDED"

        # First response has error, second is OK
        resp1 = MagicMock()
        resp1.error = "Some error"
        resp2 = MagicMock()
        resp2.error = None
        resp2.response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(text="Transcript 2")]))
        ]
        mock_result.dest.inlined_responses = [resp1, resp2]
        mock_client.batches.get.return_value = mock_result

        with patch.object(types, "JOB_STATES_SUCCEEDED", {"JOB_STATE_SUCCEEDED"}), \
             patch.object(types, "JOB_STATES_ENDED", {"JOB_STATE_FAILED"}):
            result = gen.generate(deep_dive_papers, "2026-03-14")

        # First paper's transcript should be empty, second should work
        assert "Transcript 2" in result

    @patch("research_papers.transcript_generator.genai")
    def test_batch_handles_empty_response(self, mock_genai, deep_dive_papers):
        """Should handle batch response with no candidates."""
        gen = GeminiTranscriptGenerator(
            api_key="test-key",
            model_name="gemini-3.1-pro-preview",
            use_batch=True,
        )

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_batch_job = MagicMock()
        mock_batch_job.name = "batch-empty"
        mock_batch_job.state = "JOB_STATE_SUCCEEDED"
        mock_client.batches.create.return_value = mock_batch_job

        mock_result = MagicMock()
        mock_result.state = "JOB_STATE_SUCCEEDED"

        # Response with no candidates
        resp1 = MagicMock()
        resp1.error = None
        resp1.response = None
        resp2 = MagicMock()
        resp2.error = None
        resp2.response.candidates = []
        mock_result.dest.inlined_responses = [resp1, resp2]
        mock_client.batches.get.return_value = mock_result

        with patch.object(types, "JOB_STATES_SUCCEEDED", {"JOB_STATE_SUCCEEDED"}), \
             patch.object(types, "JOB_STATES_ENDED", {"JOB_STATE_FAILED"}):
            result = gen.generate(deep_dive_papers, "2026-03-14")

        assert isinstance(result, str)

    @patch("research_papers.transcript_generator.genai")
    def test_batch_no_results_raises(self, mock_genai, deep_dive_papers):
        """Should raise RuntimeError when batch returns no results at all."""
        gen = GeminiTranscriptGenerator(
            api_key="test-key",
            model_name="gemini-3.1-pro-preview",
            use_batch=True,
        )

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_batch_job = MagicMock()
        mock_batch_job.name = "batch-no-results"
        mock_batch_job.state = "JOB_STATE_SUCCEEDED"
        mock_client.batches.create.return_value = mock_batch_job

        mock_result = MagicMock()
        mock_result.state = "JOB_STATE_SUCCEEDED"
        mock_result.dest = None  # No dest at all
        mock_client.batches.get.return_value = mock_result

        with patch.object(types, "JOB_STATES_SUCCEEDED", {"JOB_STATE_SUCCEEDED"}), \
             patch.object(types, "JOB_STATES_ENDED", {"JOB_STATE_FAILED"}):
            with pytest.raises(RuntimeError, match="No results"):
                gen.generate(deep_dive_papers, "2026-03-14")

    @patch("research_papers.transcript_generator.genai")
    def test_batch_job_failure_raises(self, mock_genai, deep_dive_papers):
        """Should raise RuntimeError when batch job fails."""
        gen = GeminiTranscriptGenerator(
            api_key="test-key",
            model_name="gemini-3.1-pro-preview",
            use_batch=True,
        )

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_batch_job = MagicMock()
        mock_batch_job.name = "batch-fail"
        mock_batch_job.state = "JOB_STATE_FAILED"
        mock_client.batches.create.return_value = mock_batch_job
        mock_client.batches.get.return_value = mock_batch_job

        with patch.object(types, "JOB_STATES_SUCCEEDED", {"JOB_STATE_SUCCEEDED"}), \
             patch.object(types, "JOB_STATES_ENDED", {"JOB_STATE_FAILED"}):
            with pytest.raises(RuntimeError, match="Batch job failed"):
                gen.generate(deep_dive_papers, "2026-03-14")


class TestOutputFormatting:
    """Tests for output formatting."""

    @patch("research_papers.transcript_generator.genai")
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
