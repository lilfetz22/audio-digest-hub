"""Data models for the research papers pipeline."""

from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass
class PaperReference:
    """A paper reference extracted from an email — URL, title, abstract, source."""

    url: str
    title: str
    abstract: str
    source: Literal["arxiv", "huggingface"]


@dataclass
class PaperContent:
    """A paper with full text content downloaded from its source."""

    url: str
    title: str
    abstract: str
    full_text: str
    source: Literal["arxiv", "huggingface"]


@dataclass
class ScoredPaper:
    """A paper that has been scored and assigned a tier."""

    paper: PaperReference
    score: float
    tier: Literal["deep_dive", "summary"]
    reasoning: str = ""
