"""Paper content downloader — downloads PDFs/HTML and extracts text."""

import io
import logging
import re
import time
from typing import Optional

import pymupdf
import requests
from bs4 import BeautifulSoup

from .interfaces import ContentExtractor
from .models import PaperReference, PaperContent

logger = logging.getLogger(__name__)

MAX_SIZE_BYTES = 34 * 1024 * 1024  # 34 MB


class PaperContentDownloader(ContentExtractor):
    """Downloads and extracts full text from Arxiv PDFs and HuggingFace pages."""

    def __init__(self, delay_seconds: int = 3):
        self.delay_seconds = delay_seconds
        self._last_request_time = 0.0

    def extract(self, paper: PaperReference) -> Optional[PaperContent]:
        """Download and extract full text from a paper.

        Args:
            paper: PaperReference to download.

        Returns:
            PaperContent with full_text, or None on failure.
        """
        if paper.source == "arxiv":
            return self._download_arxiv(paper)
        elif paper.source == "huggingface":
            return self._download_huggingface(paper)
        else:
            logger.warning(f"Unknown source: {paper.source}")
            return None

    def _respect_rate_limit(self):
        """Enforce polite delay between requests."""
        if self.delay_seconds > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay_seconds:
                time.sleep(self.delay_seconds - elapsed)
        self._last_request_time = time.time()

    def _download_arxiv(self, paper: PaperReference) -> Optional[PaperContent]:
        """Download an Arxiv paper PDF and extract text via pymupdf."""
        # Convert abs URL to pdf URL
        pdf_url = paper.url.replace("/abs/", "/pdf/") + ".pdf"
        logger.info(f"Downloading Arxiv PDF: {pdf_url}")

        self._respect_rate_limit()

        try:
            response = requests.get(pdf_url, timeout=60)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {pdf_url}: {e}")
            return None

        if response.status_code != 200:
            logger.warning(f"HTTP {response.status_code} for {pdf_url}")
            return None

        # Check size
        content_length = int(response.headers.get("content-length", 0))
        if content_length > MAX_SIZE_BYTES:
            logger.warning(
                f"Skipping oversized PDF ({content_length / 1024 / 1024:.1f}MB): {pdf_url}"
            )
            return None

        # Also check actual content size
        if len(response.content) > MAX_SIZE_BYTES:
            logger.warning(f"Skipping oversized PDF content: {pdf_url}")
            return None

        # Extract text with pymupdf
        try:
            doc = pymupdf.open(stream=io.BytesIO(response.content), filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            full_text = "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_url}: {e}")
            return None

        full_text = self._clean_text(full_text)

        if not full_text.strip():
            logger.warning(f"No text extracted from PDF: {pdf_url}")
            return None

        return PaperContent(
            url=paper.url,
            title=paper.title,
            abstract=paper.abstract,
            full_text=full_text,
            source=paper.source,
        )

    def _download_huggingface(self, paper: PaperReference) -> Optional[PaperContent]:
        """Download a HuggingFace paper page and extract text."""
        logger.info(f"Downloading HuggingFace page: {paper.url}")

        try:
            response = requests.get(paper.url, timeout=30)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {paper.url}: {e}")
            return None

        if response.status_code != 200:
            logger.warning(f"HTTP {response.status_code} for {paper.url}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script/style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        full_text = soup.get_text(separator="\n")
        full_text = self._clean_text(full_text)

        if not full_text.strip():
            logger.warning(f"No text extracted from HF page: {paper.url}")
            return None

        return PaperContent(
            url=paper.url,
            title=paper.title,
            abstract=paper.abstract,
            full_text=full_text,
            source=paper.source,
        )

    def _clean_text(self, text: str) -> str:
        """Clean extracted text: normalize whitespace, remove references section."""
        # Remove references section (common patterns)
        ref_patterns = [
            r"\nReferences\n.*",
            r"\nBibliography\n.*",
            r"\nREFERENCES\n.*",
        ]
        for pattern in ref_patterns:
            text = re.sub(pattern, "", text, flags=re.DOTALL)

        # Normalize excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()
