"""Transcript generator using Gemini 3.1 Pro (Batch or Realtime)."""

import logging
import time
from pathlib import Path
from typing import List

from google import genai
from google.genai import types

from .interfaces import TranscriptGenerator
from .models import PaperContent, PaperReference

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


class GeminiTranscriptGenerator(TranscriptGenerator):
    """Generates podcast transcripts using Gemini 3.1 Pro."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.1-pro-preview",
        use_batch: bool = True,
        batch_poll_interval: int = 60,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.use_batch = use_batch
        self.batch_poll_interval = batch_poll_interval

    def generate(
        self,
        deep_dive_papers: List[PaperContent],
        summary_papers: List[PaperReference],
        date_str: str,
    ) -> str:
        """Generate a podcast transcript from tiered paper content.

        Args:
            deep_dive_papers: Papers with full text for detailed narration.
            summary_papers: Papers with title+abstract only for brief mention.
            date_str: Date string for the digest.

        Returns:
            Complete transcript text.

        Raises:
            Exception: If generation fails.
        """
        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(
            deep_dive_papers, summary_papers, date_str
        )

        if self.use_batch:
            return self._generate_batch(system_prompt, user_prompt)
        else:
            return self._generate_realtime(system_prompt, user_prompt)

    def _load_system_prompt(self) -> str:
        """Load the narrator system prompt."""
        prompt_path = PROMPTS_DIR / "narrator_system.txt"
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_prompt(
        self,
        deep_dive_papers: List[PaperContent],
        summary_papers: List[PaperReference],
        date_str: str,
    ) -> str:
        """Build the user prompt with paper content organized by tier."""
        sections = [f"Generate a research digest podcast transcript for {date_str}.\n"]

        # Deep-dive section
        if deep_dive_papers:
            sections.append("=== DEEP-DIVE PAPERS (provide detailed coverage) ===\n")
            for i, paper in enumerate(deep_dive_papers, 1):
                sections.append(f"--- Paper {i}: {paper.title} ---")
                sections.append(f"Source: {paper.source}")
                sections.append(f"URL: {paper.url}")
                sections.append(f"Abstract: {paper.abstract}")
                sections.append(f"Full Text:\n{paper.full_text}\n")

        # Summary section
        if summary_papers:
            sections.append(
                "=== QUICK HITS (brief mention, title + one-sentence summary) ===\n"
            )
            for i, paper in enumerate(summary_papers, 1):
                sections.append(f"--- Paper {i}: {paper.title} ---")
                sections.append(f"Source: {paper.source}")
                sections.append(f"Abstract: {paper.abstract}\n")

        return "\n".join(sections)

    def _generate_realtime(self, system_prompt: str, user_prompt: str) -> str:
        """Generate transcript using realtime API."""
        client = genai.Client(api_key=self.api_key)

        response = client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            ),
        )

        return response.text

    def _generate_batch(self, system_prompt: str, user_prompt: str) -> str:
        """Generate transcript using Batch API (50% cost savings).

        Creates a batch job, polls for completion, and returns the result.
        """
        client = genai.Client(api_key=self.api_key)

        # Create batch request
        batch_request = types.CreateBatchJobConfig(
            model=self.model_name,
            src=types.BatchJobSource(
                inline_data=types.InlineData(
                    requests=[
                        types.BatchRequest(
                            request=types.GenerateContentRequest(
                                model=self.model_name,
                                contents=[
                                    types.Content(
                                        parts=[types.Part(text=user_prompt)],
                                        role="user",
                                    )
                                ],
                                config=types.GenerateContentConfig(
                                    system_instruction=system_prompt,
                                    temperature=0.7,
                                ),
                            )
                        )
                    ]
                )
            ),
        )

        logger.info("Creating batch job for transcript generation...")
        batch_job = client.batches.create(config=batch_request)
        logger.info(f"Batch job created: {batch_job.name}")

        # Poll for completion
        while True:
            batch_job = client.batches.get(name=batch_job.name)
            status = batch_job.state

            if status == "JOB_STATE_SUCCEEDED":
                logger.info("Batch job completed successfully")
                break
            elif status in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED"):
                raise RuntimeError(f"Batch job failed with state: {status}")

            logger.info(f"Batch job status: {status}. Polling again in {self.batch_poll_interval}s...")
            time.sleep(self.batch_poll_interval)

        # Retrieve results
        result = client.batches.get(name=batch_job.name)
        if hasattr(result, "dest") and result.dest:
            responses = result.dest.inline_data.responses
            if responses:
                return responses[0].response.candidates[0].content.parts[0].text

        raise RuntimeError("No results in batch job response")
