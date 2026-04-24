"""Transcript classifier — categorizes transcript sections by topic."""

import json
import logging
from pathlib import Path
from typing import List

from .models import ClassifiedSection
from .utils import load_prompt

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

_CLASSIFY_SYSTEM_FALLBACK = """You are a research paper classifier. Given a transcript section, classify it into one or more categories.

Return a JSON object with these fields:
- "category": The primary category (one of: "AI Architecture", "Hardware", "Benchmarking", "Optimization", "NLP", "Computer Vision", "Reinforcement Learning", "Robotics", "Time Series", "AI Agents", "Safety & Alignment", "Other")
- "title": A short descriptive title for this section (max 10 words)
- "paper_urls": Any URLs mentioned in the text (list of strings)

Respond ONLY with valid JSON, no markdown formatting."""


class TranscriptClassifier:
    """Classifies transcript sections into topic categories using an LLM."""

    def __init__(self, llm_client=None, model_name: str = "gemini-3.1-flash-lite-preview"):
        self.llm_client = llm_client
        self.model_name = model_name
        self._classify_prompt = load_prompt(PROMPTS_DIR, "classify_system.txt", _CLASSIFY_SYSTEM_FALLBACK)

    def classify(self, sections: List[str]) -> List[ClassifiedSection]:
        """Classify a list of transcript sections.

        Args:
            sections: List of text sections from a transcript.

        Returns:
            List of ClassifiedSection objects with category assigned.
        """
        results = []
        for section in sections:
            classified = self._classify_single(section)
            results.append(classified)
        return results

    def _llm_generate(self, user_prompt: str, system_prompt: str) -> str | None:
        """Call the LLM, routing through the fallback client when available."""
        if self.llm_client is None:
            return None
        # GeminiClientWithFallback exposes .generate(); legacy bare clients do not.
        try:
            from ..gemini_client import GeminiClientWithFallback
        except ImportError:
            from research_papers.gemini_client import GeminiClientWithFallback
        if isinstance(self.llm_client, GeminiClientWithFallback):
            return self.llm_client.generate(user_prompt, system_prompt)
        response = self.llm_client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config={"system_instruction": system_prompt},
        )
        return response.text

    def _classify_single(self, text: str) -> ClassifiedSection:
        """Classify a single section of text."""
        if not self.llm_client:
            return ClassifiedSection(text=text, category="Other", title="Unclassified")

        try:
            result_text = self._llm_generate(text[:4000], self._classify_prompt)
            if result_text is None:
                return ClassifiedSection(text=text, category="Other", title="Unclassified")
            result_text = result_text.strip()
            # Strip markdown code fences if present
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                result_text = result_text.rsplit("```", 1)[0]

            data = json.loads(result_text)
            if isinstance(data, list):
                data = data[0] if data and isinstance(data[0], dict) else {}
            return ClassifiedSection(
                text=text,
                category=data.get("category", "Other"),
                title=data.get("title", ""),
                paper_urls=data.get("paper_urls", []),
            )
        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON: %s", e)
            return ClassifiedSection(text=text, category="Other", title="Unclassified")
        except Exception:
            logger.exception("Unexpected error during classification")
            return ClassifiedSection(text=text, category="Other", title="Unclassified")


def split_transcript_into_sections(transcript_text: str) -> List[str]:
    """Split a daily transcript into logical sections.

    Heuristic: split on double newlines that follow a pattern like
    paper titles or section markers. Falls back to splitting on
    large paragraph boundaries.
    """
    # Split on common section markers in transcripts
    sections = []
    current_section = []

    lines = transcript_text.split("\n")
    for line in lines:
        # Detect section boundaries: empty lines after substantial content
        if line.strip() == "" and len("\n".join(current_section)) > 1200:
            # Check if next content looks like a new topic
            if current_section:
                sections.append("\n".join(current_section))
                current_section = []
        else:
            current_section.append(line)

    if current_section:
        sections.append("\n".join(current_section))

    # If we got very few sections, the transcript might not have clear breaks
    # In that case, split into chunks of ~2000 chars
    if len(sections) <= 1 and len(transcript_text) > 3000:
        sections = _chunk_text(transcript_text, chunk_size=2000)

    return [s for s in sections if len(s.strip()) > 50]


def _chunk_text(text: str, chunk_size: int = 2000) -> List[str]:
    """Split text into roughly equal chunks at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_len = 0
        current_chunk.append(para)
        current_len += len(para)

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks
