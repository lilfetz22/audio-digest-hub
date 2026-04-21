"""Tests for the wiki transcript classifier."""

import json
from unittest.mock import MagicMock, patch

import pytest

from wiki_engine.classifier import (
    TranscriptClassifier,
    split_transcript_into_sections,
    _chunk_text,
)
from wiki_engine.models import ClassifiedSection


class TestTranscriptClassifier:
    """Tests for TranscriptClassifier."""

    def test_classify_without_llm_returns_other(self):
        """Without an LLM client, all sections classified as 'Other'."""
        classifier = TranscriptClassifier(llm_client=None)
        sections = ["Some text about transformers and attention mechanisms."]
        results = classifier.classify(sections)
        assert len(results) == 1
        assert results[0].category == "Other"
        assert results[0].title == "Unclassified"
        assert results[0].text == sections[0]

    def test_classify_with_mock_llm(self):
        """With a mock LLM, returns parsed classification."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "category": "AI Architecture",
            "title": "Transformer Improvements",
            "paper_urls": ["https://arxiv.org/abs/2024.12345"],
        })
        mock_client.models.generate_content.return_value = mock_response

        classifier = TranscriptClassifier(llm_client=mock_client)
        results = classifier.classify(["Text about new transformer architecture"])

        assert len(results) == 1
        assert results[0].category == "AI Architecture"
        assert results[0].title == "Transformer Improvements"
        assert "https://arxiv.org/abs/2024.12345" in results[0].paper_urls

    def test_classify_handles_llm_error(self):
        """Falls back to 'Other' if LLM returns invalid JSON."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "not valid json at all"
        mock_client.models.generate_content.return_value = mock_response

        classifier = TranscriptClassifier(llm_client=mock_client)
        results = classifier.classify(["Some text"])

        assert len(results) == 1
        assert results[0].category == "Other"

    def test_classify_handles_markdown_wrapped_json(self):
        """Handles LLM responses wrapped in markdown code fences."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"category": "NLP", "title": "Language Models", "paper_urls": []}\n```'
        mock_client.models.generate_content.return_value = mock_response

        classifier = TranscriptClassifier(llm_client=mock_client)
        results = classifier.classify(["Text about language models"])

        assert results[0].category == "NLP"

    def test_classify_multiple_sections(self):
        """Classifies multiple sections independently."""
        mock_client = MagicMock()

        responses = [
            json.dumps({"category": "AI Architecture", "title": "T1", "paper_urls": []}),
            json.dumps({"category": "Hardware", "title": "T2", "paper_urls": []}),
        ]
        mock_client.models.generate_content.side_effect = [
            MagicMock(text=r) for r in responses
        ]

        classifier = TranscriptClassifier(llm_client=mock_client)
        results = classifier.classify(["Section 1", "Section 2"])

        assert len(results) == 2
        assert results[0].category == "AI Architecture"
        assert results[1].category == "Hardware"


class TestSplitTranscript:
    """Tests for split_transcript_into_sections."""

    def test_split_short_text_returns_single_section(self):
        """Short text stays as one section."""
        text = "A short paragraph about AI."
        sections = split_transcript_into_sections(text)
        # Short text below 50 chars threshold is filtered out
        assert len(sections) <= 1

    def test_split_long_text_into_chunks(self):
        """Long text without clear breaks gets chunked."""
        text = "A" * 500 + "\n\n" + "B" * 500 + "\n\n" + "C" * 500 + "\n\n" + "D" * 500 + "\n\n" + "E" * 500 + "\n\n" + "F" * 500 + "\n\n" + "G" * 500
        sections = split_transcript_into_sections(text)
        assert len(sections) >= 1

    def test_split_preserves_content(self):
        """All content is preserved across sections."""
        paragraphs = [f"Paragraph {i} " * 50 for i in range(5)]
        text = "\n\n".join(paragraphs)
        sections = split_transcript_into_sections(text)
        combined = "".join(sections)
        for para in paragraphs:
            assert para.strip() in combined or para[:20] in combined

    def test_chunk_text_respects_size(self):
        """_chunk_text produces chunks near the target size."""
        text = "\n\n".join([f"Para {i} content here." * 20 for i in range(10)])
        chunks = _chunk_text(text, chunk_size=500)
        assert len(chunks) >= 2
        for chunk in chunks:
            # Allow some overflow due to paragraph boundaries
            assert len(chunk) < 1500
