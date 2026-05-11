"""Data models for the wiki engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional


@dataclass
class WikiPageMeta:
    """YAML frontmatter metadata for a wiki page."""

    title: str
    type: Literal["concept", "source", "query-result"]
    sources: List[str] = field(default_factory=list)
    created: str = ""
    updated: str = ""
    confidence: float = 0.5
    categories: List[str] = field(default_factory=list)

    def __post_init__(self):
        now = datetime.now().strftime("%Y-%m-%d")
        if not self.created:
            self.created = now
        if not self.updated:
            self.updated = now

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "type": self.type,
            "sources": self.sources,
            "created": self.created,
            "updated": self.updated,
            "confidence": self.confidence,
            "categories": self.categories,
        }


@dataclass
class ExtractedConcept:
    """A concept extracted from a transcript by the LLM."""

    name: str
    tldr: str
    body: str
    counterarguments: str
    confidence: float = 0.5
    categories: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


@dataclass
class ClassifiedSection:
    """A section of transcript that has been classified by topic."""

    text: str
    category: str
    title: str = ""
    paper_urls: List[str] = field(default_factory=list)
