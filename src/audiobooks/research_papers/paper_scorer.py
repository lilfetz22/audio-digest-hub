"""Paper scoring: LLM-based (GeminiPaperScorer) and embedding-based (EmbeddingPaperScorer)."""

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
    """Scores papers by relevance using Gemini Flash."""

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
        """Score papers and assign tiers.

        Args:
            papers: List of PaperReferences to score.
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


class EmbeddingPaperScorer(PaperScorer):
    """Scores papers by cosine similarity to a local interest profile using sentence-transformers.

    No API calls required. Model (~80 MB) is downloaded on first use and cached on disk.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        top_n: int = 10,
        interest_profile_path: str | None = None,
    ):
        self.model_name = model_name
        self.top_n = top_n
        self.interest_profile_path = (
            Path(interest_profile_path)
            if interest_profile_path
            else PROMPTS_DIR / "interest_profile.txt"
        )
        self._model = None  # Lazy-loaded on first score() call

    def _get_model(self):
        """Load the SentenceTransformer model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            logger.info(f"Loading embedding model '{self.model_name}' (downloads ~80 MB on first run)...")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded.")
        return self._model

    def _build_query(self, preference_profile: str) -> str:
        """Construct interest query from profile file + optional dynamic profile."""
        base_query = self.interest_profile_path.read_text(encoding="utf-8").strip()
        if preference_profile:
            return f"{base_query}. {preference_profile.strip()}"
        return base_query

    def _compute_scores(
        self, papers: List[PaperReference], preference_profile: str
    ) -> List[ScoredPaper]:
        """Embed query and all papers, compute cosine similarities, return ScoredPapers."""
        from sentence_transformers import util  # noqa: PLC0415

        model = self._get_model()
        query = self._build_query(preference_profile)

        # Encode query + all papers in one batch for efficiency
        paper_texts = [f"{p.title}. {p.abstract}" for p in papers]
        all_texts = [query] + paper_texts
        embeddings = model.encode(all_texts, convert_to_tensor=True, show_progress_bar=False)

        query_embedding = embeddings[0]
        paper_embeddings = embeddings[1:]

        scored = []
        for i, paper in enumerate(papers):
            similarity = float(util.cos_sim(query_embedding, paper_embeddings[i]))
            # Clamp to [0, 1] before scaling (cosine can be slightly negative)
            similarity = max(0.0, min(1.0, similarity))
            # Map to 1–10 scale for backward compatibility with Supabase schema and tier logic
            score = round(similarity * 9.0 + 1.0, 2)
            scored.append(
                ScoredPaper(
                    paper=paper,
                    score=score,
                    tier="summary",  # Temporary; tiering assigned after sort
                    reasoning=f"Embedding similarity: {similarity:.3f}",
                )
            )

        return scored

    def score(
        self, papers: List[PaperReference], preference_profile: str = ""
    ) -> List[ScoredPaper]:
        """Score papers and assign tiers.

        Args:
            papers: List of PaperReferences to score.
            preference_profile: Additional preference text appended to the base interest query.

        Returns:
            List of ScoredPaper sorted by score descending. Top N = deep_dive, rest = summary.
        """
        if not papers:
            return []

        try:
            scored = self._compute_scores(papers, preference_profile)
        except Exception as e:
            logger.error(f"Embedding scoring failed: {e}", exc_info=True)
            # Fallback: neutral score, tier logic still applied below
            scored = [
                ScoredPaper(paper=p, score=5.0, tier="summary", reasoning="Scoring failed")
                for p in papers
            ]

        # Sort by score descending
        scored.sort(key=lambda s: s.score, reverse=True)

        # Assign tiers: top N = deep_dive, rest = summary
        for i, sp in enumerate(scored):
            sp.tier = "deep_dive" if i < self.top_n else "summary"

        return scored
