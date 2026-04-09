"""Abstract base classes for the research papers pipeline."""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import PaperReference, PaperContent, ScoredPaper


class PaperSource(ABC):
    """Contract for extracting paper references from any source (e.g., email)."""

    @abstractmethod
    def fetch_papers(self, date_str: str, **kwargs) -> List[PaperReference]:
        """Fetch paper references for a given date.

        Args:
            date_str: Date string in YYYY-MM-DD format.
            **kwargs: Additional arguments (e.g., gmail_service).

        Returns:
            List of PaperReference objects extracted from the source.
        """
        ...


class ContentExtractor(ABC):
    """Contract for downloading and extracting full text from a paper URL."""

    @abstractmethod
    def extract(self, paper: PaperReference) -> Optional[PaperContent]:
        """Download and extract full text content from a paper.

        Args:
            paper: A PaperReference with URL to download.

        Returns:
            PaperContent with full_text populated, or None on failure.
        """
        ...


class PaperScorer(ABC):
    """Contract for scoring and tiering papers by relevance."""

    @abstractmethod
    def score(
        self, papers: List[PaperReference], preference_profile: str
    ) -> List[ScoredPaper]:
        """Score papers and assign tiers.

        Args:
            papers: List of papers to score.
            preference_profile: Formatted preference profile string for prompt injection.

        Returns:
            List of ScoredPaper objects sorted by score descending.
        """
        ...


class TranscriptGenerator(ABC):
    """Contract for generating a podcast transcript from paper content."""

    @abstractmethod
    def generate(
        self,
        deep_dive_papers: List[PaperContent],
        date_str: str,
    ) -> str:
        """Generate a podcast transcript.

        Args:
            deep_dive_papers: Papers with full text for detailed narration.
            date_str: Date string for the digest.

        Returns:
            Complete transcript text.
        """
        ...


class FeedbackStore(ABC):
    """Contract for reading/writing preference feedback data."""

    @abstractmethod
    def load_profile(self) -> str:
        """Load the preference profile formatted for prompt injection.

        Returns:
            Formatted string describing user preferences, or empty string if none.
        """
        ...

    @abstractmethod
    def update_profile(self, clicked_papers: List[dict]) -> None:
        """Update the preference profile with newly clicked papers.

        Args:
            clicked_papers: List of dicts with 'title' and 'abstract' keys.
        """
        ...
