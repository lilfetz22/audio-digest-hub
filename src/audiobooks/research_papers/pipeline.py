"""Pipeline orchestrator — wires all components together."""

import json
import logging
import os
from typing import List, Optional

import requests

from .interfaces import (
    PaperSource,
    ContentExtractor,
    PaperScorer,
    TranscriptGenerator,
    FeedbackStore,
)
from .models import PaperReference, PaperContent, ScoredPaper
from .feedback import FeedbackClient

logger = logging.getLogger(__name__)


class ResearchPaperPipeline:
    """Orchestrates the full research paper digest pipeline."""

    def __init__(
        self,
        email_parser: PaperSource,
        paper_downloader: ContentExtractor,
        paper_scorer: PaperScorer,
        transcript_generator: TranscriptGenerator,
        feedback_manager: FeedbackStore,
        feedback_client: FeedbackClient,
        gmail_service,
        api_url: str,
        api_key: str,
        output_dir: str = "raw_content",
    ):
        self.email_parser = email_parser
        self.paper_downloader = paper_downloader
        self.paper_scorer = paper_scorer
        self.transcript_generator = transcript_generator
        self.feedback_manager = feedback_manager
        self.feedback_client = feedback_client
        self.gmail_service = gmail_service
        self.api_url = api_url
        self.api_key = api_key
        self.output_dir = output_dir

    def run(self, date_str: str) -> None:
        """Run the full pipeline for a given date.

        Steps:
            1. Check idempotency (skip if output exists)
            2. Load preference profile from feedback
            3. Parse emails for paper references
            4. Split by source (HuggingFace vs Arxiv)
            5. Score Arxiv papers
            6. Mark all HuggingFace papers as deep_dive
            7. Download full content for deep_dive papers
            8. Generate transcript
            9. Save transcript to output_dir
            10. Push paper metadata to Supabase
        """
        output_filename = f"research_digest_{date_str}.txt"
        output_path = os.path.join(self.output_dir, output_filename)

        # Step 1: Idempotency check
        if os.path.exists(output_path):
            logger.info(f"Output already exists: {output_path}. Skipping.")
            return

        logger.info(f"=== Starting research paper pipeline for {date_str} ===")

        # Step 2: Load preference profile
        self._update_feedback()
        preference_profile = self.feedback_manager.load_profile()
        if preference_profile:
            logger.info("Loaded preference profile for scoring")

        # Step 3: Parse emails
        papers = self.email_parser.fetch_papers(
            date_str, gmail_service=self.gmail_service
        )
        if not papers:
            logger.info(f"No papers found for {date_str}. Skipping.")
            return

        logger.info(f"Found {len(papers)} papers total")

        # Step 4: Split by source
        hf_papers = [p for p in papers if p.source == "huggingface"]
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        logger.info(
            f"Split: {len(hf_papers)} HuggingFace, {len(arxiv_papers)} Arxiv"
        )

        # Step 5: Score Arxiv papers only
        deep_dive_refs: List[PaperReference] = []
        summary_refs: List[PaperReference] = []

        if arxiv_papers:
            try:
                scored = self.paper_scorer.score(arxiv_papers, preference_profile)
                for sp in scored:
                    if sp.tier == "deep_dive":
                        deep_dive_refs.append(sp.paper)
                    else:
                        summary_refs.append(sp.paper)
                logger.info(
                    f"Arxiv scoring: {len(deep_dive_refs)} deep-dive, "
                    f"{len(summary_refs)} summary"
                )
            except Exception as e:
                logger.error(f"Scoring failed, all Arxiv papers become summary: {e}")
                summary_refs.extend(arxiv_papers)

        # Step 6: All HuggingFace papers are deep_dive
        deep_dive_refs.extend(hf_papers)
        logger.info(
            f"Total deep-dive papers: {len(deep_dive_refs)} "
            f"(including {len(hf_papers)} HuggingFace)"
        )

        # Step 7: Download full content for deep-dive papers
        deep_dive_content: List[PaperContent] = []
        for paper in deep_dive_refs:
            try:
                content = self.paper_downloader.extract(paper)
                if content:
                    deep_dive_content.append(content)
                else:
                    logger.warning(
                        f"Failed to download {paper.url}, moving to summary"
                    )
                    summary_refs.append(paper)
            except Exception as e:
                logger.error(f"Download error for {paper.url}: {e}")
                summary_refs.append(paper)

        logger.info(
            f"Downloaded {len(deep_dive_content)} deep-dive papers, "
            f"{len(summary_refs)} summary papers"
        )

        if not deep_dive_content and not summary_refs:
            logger.warning("No papers available for transcript generation")
            return

        # Step 8: Generate transcript
        try:
            transcript = self.transcript_generator.generate(
                deep_dive_content, summary_refs, date_str
            )
        except Exception as e:
            logger.error(f"Transcript generation failed: {e}", exc_info=True)
            return

        # Step 9: Save transcript
        os.makedirs(self.output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        logger.info(f"Saved transcript to {output_path}")

        # Step 10: Push metadata to Supabase
        self._push_metadata(date_str, deep_dive_content, summary_refs)

        logger.info(f"=== Pipeline completed for {date_str} ===")

    def _update_feedback(self) -> None:
        """Fetch recent click feedback and update preference profile."""
        try:
            clicked = self.feedback_client.fetch_clicked_papers(days=30)
            if clicked:
                self.feedback_manager.update_profile(clicked)
                logger.info(f"Updated profile with {len(clicked)} clicked papers")
        except Exception as e:
            logger.warning(f"Failed to update feedback: {e}")

    def _push_metadata(
        self,
        date_str: str,
        deep_dive: List[PaperContent],
        summary: List[PaperReference],
    ) -> None:
        """Push paper metadata to Supabase edge function."""
        papers_data = []

        for paper in deep_dive:
            papers_data.append(
                {
                    "url": paper.url,
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "score": 10,  # Deep-dive papers are top scored
                    "tier": "deep_dive",
                    "source": paper.source,
                    "clicked": False,
                }
            )

        for paper in summary:
            papers_data.append(
                {
                    "url": paper.url,
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "score": 0,
                    "tier": "summary",
                    "source": paper.source,
                    "clicked": False,
                }
            )

        payload = {"date": date_str, "papers": papers_data}

        try:
            url = f"{self.api_url}/research-papers"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            response = requests.post(
                url, json=payload, headers=headers, timeout=30
            )
            if response.status_code in (200, 201):
                logger.info(
                    f"Pushed {len(papers_data)} paper metadata to Supabase"
                )
            else:
                logger.warning(
                    f"Failed to push metadata: HTTP {response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Failed to push metadata to Supabase: {e}")
