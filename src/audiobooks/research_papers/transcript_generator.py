"""Transcript generator using Gemini 3.1 Pro (Batch or Realtime)."""

import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import List

from google import genai
from google.genai import types

from .interfaces import TranscriptGenerator
from .models import PaperContent, PaperReference

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# TTS-friendly display names for Arxiv category codes
CATEGORY_DISPLAY_NAMES = {
    "cs": "Computer Science",
    "stat": "Statistics",
    "math": "Mathematics",
    "eess": "Electrical Engineering and Systems Science",
    "q-bio": "Quantitative Biology",
    "q-fin": "Quantitative Finance",
    "physics": "Physics",
    "astro-ph": "Astrophysics",
    "cond-mat": "Condensed Matter",
    "hep": "High Energy Physics",
    "quant-ph": "Quantum Physics",
    "arxiv": "Arxiv",
}


class GeminiTranscriptGenerator(TranscriptGenerator):
    """Generates podcast transcripts using Gemini 3.1 Pro.

    Each deep-dive paper is sent individually to the LLM for a full deep dive.
    Summary papers are formatted as plain text (title + abstract) without any
    LLM call, grouped by category.
    """

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

        Each deep-dive paper gets its own LLM call for a thorough, individual
        deep dive. All deep-dive calls are submitted as separate InlinedRequests
        in a single Batch job (or as sequential realtime calls).

        Summary papers are NOT sent to the LLM. Their title + abstract are
        formatted directly as plain text, grouped by category with TTS-friendly
        headings, and appended after the deep-dive transcripts.

        Args:
            deep_dive_papers: Papers with full text for detailed narration.
            summary_papers: Papers with title+abstract only for brief mention.
            date_str: Date string for the digest.

        Returns:
            Complete transcript text.
        """
        system_prompt = self._load_system_prompt()

        # Generate per-paper deep dive transcripts
        deep_dive_transcripts: List[str] = []
        if deep_dive_papers:
            per_paper_prompts = [
                self._build_single_paper_prompt(paper, date_str)
                for paper in deep_dive_papers
            ]

            if self.use_batch:
                deep_dive_transcripts = self._generate_batch_multi(
                    system_prompt, per_paper_prompts
                )
            else:
                deep_dive_transcripts = [
                    self._generate_realtime(system_prompt, prompt)
                    for prompt in per_paper_prompts
                ]

        # Build summary text directly (no LLM call)
        summary_text = self._build_summary_text(summary_papers)

        # Assemble final transcript
        parts = []
        for transcript in deep_dive_transcripts:
            parts.append(transcript.strip())
        if summary_text:
            parts.append(summary_text)

        return "\n\n".join(parts)

    def _load_system_prompt(self) -> str:
        """Load the narrator system prompt."""
        prompt_path = PROMPTS_DIR / "narrator_system.txt"
        return prompt_path.read_text(encoding="utf-8")

    def _build_single_paper_prompt(
        self, paper: PaperContent, date_str: str
    ) -> str:
        """Build a user prompt for a deep dive into a single paper."""
        sections = [
            f"Generate a deep-dive research digest segment for {date_str}.\n",
            f"--- Paper: {paper.title} ---",
            f"Source: {paper.source}",
            f"URL: {paper.url}",
            f"Abstract: {paper.abstract}",
            f"Full Text:\n{paper.full_text}\n",
        ]
        return "\n".join(sections)

    def _build_summary_text(
        self, summary_papers: List[PaperReference]
    ) -> str:
        """Format summary papers as plain text grouped by category.

        This text is NOT sent to the LLM — it is assembled directly from the
        paper metadata and appended to the end of the transcript.
        """
        if not summary_papers:
            return ""

        # Group by category
        by_category: dict[str, List[PaperReference]] = defaultdict(list)
        for paper in summary_papers:
            cat = paper.category or paper.source
            by_category[cat].append(paper)

        sections = [
            "\nAnd now, here are some additional notable papers worth mentioning.\n"
        ]

        for cat, papers in sorted(by_category.items()):
            display_name = CATEGORY_DISPLAY_NAMES.get(cat, cat.title())
            sections.append(
                f"From the {display_name} category:\n"
            )
            for paper in papers:
                sections.append(f"  {paper.title}.")
                if paper.abstract:
                    sections.append(f"  {paper.abstract}\n")
                else:
                    sections.append("")

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

    def _generate_batch_multi(
        self, system_prompt: str, user_prompts: List[str]
    ) -> List[str]:
        """Generate transcripts for multiple papers in a single Batch job.

        Each paper gets its own InlinedRequest within one batch job. This avoids
        per-paper polling overhead while keeping each LLM call focused on a
        single paper for thorough deep-dive coverage.

        Args:
            system_prompt: The narrator system prompt.
            user_prompts: List of per-paper user prompts.

        Returns:
            List of transcript strings, one per paper, in the same order as
            user_prompts.
        """
        client = genai.Client(api_key=self.api_key)

        inlined_requests = [
            types.InlinedRequest(
                model=self.model_name,
                contents=[
                    types.Content(
                        parts=[types.Part(text=prompt)],
                        role="user",
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                ),
            )
            for prompt in user_prompts
        ]

        logger.info(
            f"Creating batch job with {len(inlined_requests)} "
            f"per-paper deep-dive requests..."
        )
        batch_job = client.batches.create(
            model=self.model_name,
            src=types.BatchJobSource(inlined_requests=inlined_requests),
        )
        logger.info(f"Batch job created: {batch_job.name}")

        # Poll for completion
        while True:
            batch_job = client.batches.get(name=batch_job.name)
            status = batch_job.state

            if status in types.JOB_STATES_SUCCEEDED:
                logger.info("Batch job completed successfully")
                break
            elif status in types.JOB_STATES_ENDED:
                raise RuntimeError(f"Batch job failed with state: {status}")

            logger.info(
                f"Batch job status: {status}. "
                f"Polling again in {self.batch_poll_interval}s..."
            )
            time.sleep(self.batch_poll_interval)

        # Retrieve results
        result = client.batches.get(name=batch_job.name)
        transcripts: List[str] = []

        if result.dest and result.dest.inlined_responses:
            for i, resp in enumerate(result.dest.inlined_responses):
                if resp.error:
                    logger.error(
                        f"Batch request {i} error: {resp.error}"
                    )
                    transcripts.append("")
                elif resp.response and resp.response.candidates:
                    text = resp.response.candidates[0].content.parts[0].text
                    transcripts.append(text)
                else:
                    logger.warning(f"Batch request {i}: no content in response")
                    transcripts.append("")
        else:
            raise RuntimeError("No results in batch job response")

        return transcripts
