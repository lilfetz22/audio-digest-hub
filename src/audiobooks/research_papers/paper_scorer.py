"""AI-powered paper scorer using Gemini Flash — Arxiv papers only."""

import json
import logging
import os
import re
from pathlib import Path
from typing import List

from google import genai
from google.genai import types

from .interfaces import PaperScorer
from .models import PaperReference, ScoredPaper

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


class GeminiPaperScorer(PaperScorer):
    """Scores Arxiv papers by relevance using Gemini Flash."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3-flash-preview",
        top_n: int = 10,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.top_n = top_n

    def score(
        self, papers: List[PaperReference], preference_profile: str = ""
    ) -> List[ScoredPaper]:
        """Score Arxiv papers and assign tiers.

        Args:
            papers: List of Arxiv PaperReferences to score.
            preference_profile: Formatted preference string for prompt injection.

        Returns:
            List of ScoredPaper sorted by score descending. Top N = deep_dive, rest = summary.
        """
        if not papers:
            return []

        try:
            scores_map = self._call_gemini(papers, preference_profile)
        except Exception as e:
            logger.error(f"Scoring failed: {e}", exc_info=True)
            # Fallback: all papers get summary tier
            return [
                ScoredPaper(paper=p, score=0, tier="summary", reasoning="Scoring failed")
                for p in papers
            ]

        # Build ScoredPaper list
        scored = []
        for paper in papers:
            if paper.url in scores_map:
                entry = scores_map[paper.url]
                scored.append(
                    ScoredPaper(
                        paper=paper,
                        score=entry.get("score", 0),
                        tier="deep_dive",  # Temporary, will assign after sorting
                        reasoning=entry.get("reasoning", ""),
                    )
                )
            else:
                scored.append(
                    ScoredPaper(
                        paper=paper, score=0, tier="summary", reasoning="Not scored"
                    )
                )

        # Sort by score descending
        scored.sort(key=lambda s: s.score, reverse=True)

        # Assign tiers: top N = deep_dive, rest = summary
        for i, sp in enumerate(scored):
            sp.tier = "deep_dive" if i < self.top_n else "summary"

        return scored

    def _call_gemini(
        self, papers: List[PaperReference], preference_profile: str
    ) -> dict:
        """Call Gemini Flash to score papers in batches to avoid output truncation.

        Returns:
            Dict mapping paper URL to {"score": int, "reasoning": str}.
        """
        system_prompt = self._build_system_prompt(preference_profile)
        client = genai.Client(api_key=self.api_key)

        # Score in batches of 50 to avoid hitting output token limits
        BATCH_SIZE = 50
        scores_map: dict = {}
        for batch_start in range(0, len(papers), BATCH_SIZE):
            batch = papers[batch_start : batch_start + BATCH_SIZE]
            user_prompt = self._build_user_prompt(batch)
            response = client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            batch_scores = self._parse_response(response.text or "", batch)
            scores_map.update(batch_scores)
            logger.info(
                f"Scored batch {batch_start // BATCH_SIZE + 1}"
                f"/{(len(papers) + BATCH_SIZE - 1) // BATCH_SIZE}"
                f" ({len(batch_scores)}/{len(batch)} scored)"
            )

        return scores_map


    def _build_system_prompt(self, preference_profile: str) -> str:
        """Load scorer system prompt and inject preference profile."""
        prompt_path = PROMPTS_DIR / "scorer_system.txt"
        template = prompt_path.read_text(encoding="utf-8")

        if preference_profile:
            profile_section = (
                f"\n\nAdditional context from user behavior:\n{preference_profile}"
            )
        else:
            profile_section = ""

        return template.replace("{preference_profile_section}", profile_section)

    def _build_user_prompt(self, papers: List[PaperReference]) -> str:
        """Build the user prompt with all papers to score."""
        lines = ["Score the following papers:\n"]
        for i, paper in enumerate(papers, 1):
            lines.append(f"Paper {i}:")
            lines.append(f"  URL: {paper.url}")
            lines.append(f"  Title: {paper.title}")
            lines.append(f"  Abstract: {paper.abstract}")
            lines.append("")

        lines.append(
            'Return a JSON array with objects containing "url", "score" (1-10), '
            'and "reasoning" (one sentence) for each paper.'
        )
        return "\n".join(lines)

    def _parse_response(self, response_text: str, papers: List[PaperReference]) -> dict:
        """Parse the Gemini response JSON into a URL-keyed dict."""
        try:
            # Strip markdown code fences if present
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            # Try to parse; if backslash escape errors occur (e.g. LaTeX in
            # reasoning strings), sanitize invalid \X sequences and retry.
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Replace \X where X is not a valid JSON escape character
                sanitized = re.sub(r'\\(?!["\\/bfnrtu0-9])', r'\\\\', text)
                data = json.loads(sanitized)

            if not isinstance(data, list):
                raise ValueError("Expected a JSON array")

            result = {}
            for entry in data:
                url = entry.get("url", "")
                score = int(entry.get("score", 0))
                reasoning = entry.get("reasoning", "")
                result[url] = {"score": score, "reasoning": reasoning}

            return result

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse scorer response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            # Return empty — caller will assign default scores
            return {}
