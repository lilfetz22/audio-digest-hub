"""Tests for email_parser.py — ArxivHFEmailParser."""

import pytest
from unittest.mock import MagicMock, patch
from research_papers.email_parser import ArxivHFEmailParser
from research_papers.models import PaperReference


# --- Sample email HTML fixtures ---

ARXIV_EMAIL_HTML = """
<html><body>
<h3>arXiv:2603.12345</h3>
<b>Title:</b> Agent-Based Optimization for Time Series Forecasting<br/>
<b>Authors:</b> Jane Doe, John Smith<br/>
<b>Abstract:</b> We propose a novel agent-based approach to time series forecasting
that leverages multi-agent collaboration for improved accuracy on long-horizon predictions.
Our method outperforms existing baselines on 7 benchmark datasets.<br/>
<a href="https://arxiv.org/abs/2603.12345">https://arxiv.org/abs/2603.12345</a>

<h3>arXiv:2603.12346</h3>
<b>Title:</b> Diffusion Models for Image Synthesis<br/>
<b>Authors:</b> Alice Bob<br/>
<b>Abstract:</b> This paper explores new architectures for diffusion-based image generation
with improved sampling efficiency and visual quality.<br/>
<a href="https://arxiv.org/abs/2603.12346">https://arxiv.org/abs/2603.12346</a>

<h3>arXiv:2603.12347</h3>
<b>Title:</b> Constrained Optimization via Reinforcement Learning<br/>
<b>Authors:</b> Charlie Delta<br/>
<b>Abstract:</b> A reinforcement learning framework for solving constrained optimization problems
in continuous action spaces with convergence guarantees.<br/>
<a href="https://arxiv.org/abs/2603.12347">https://arxiv.org/abs/2603.12347</a>
</body></html>
"""

HUGGINGFACE_EMAIL_HTML = """
<html><body>
<div>
<a href="https://huggingface.co/papers/2603.11111">New Foundation Model for Code Generation</a>
<p>A large language model specifically trained on code...</p>
</div>
<div>
<a href="https://huggingface.co/papers/2603.11112">Efficient Attention Mechanisms</a>
<p>Novel attention pattern that reduces complexity...</p>
</div>
</body></html>
"""

EMPTY_EMAIL_HTML = "<html><body><p>No papers today.</p></body></html>"

MALFORMED_EMAIL_HTML = "<html><body><div>Broken"


def _make_gmail_message(msg_id, sender, html_body):
    """Helper to create a mock Gmail API message dict."""
    import base64

    encoded = base64.urlsafe_b64encode(html_body.encode("utf-8")).decode("utf-8")
    return {
        "id": msg_id,
        "payload": {
            "headers": [
                {"name": "From", "value": f"Papers <{sender}>"},
                {"name": "Subject", "value": "Daily Digest"},
            ],
            "parts": [{"mimeType": "text/html", "body": {"data": encoded}}],
        },
        "labelIds": [],
    }


@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail API service."""
    service = MagicMock()
    return service


@pytest.fixture
def parser():
    """Create an ArxivHFEmailParser with default config."""
    return ArxivHFEmailParser(
        arxiv_senders=["no-reply@arxiv.org"],
        huggingface_senders=["no-reply@huggingface.co"],
    )


class TestArxivParsing:
    """Tests for extracting papers from Arxiv emails."""

    def test_extracts_arxiv_urls(self, parser, mock_gmail_service):
        """Should extract arxiv.org/abs/XXXX URLs from Arxiv email HTML."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML)
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)

        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        urls = {p.url for p in arxiv_papers}
        assert "https://arxiv.org/abs/2603.12345" in urls
        assert "https://arxiv.org/abs/2603.12346" in urls
        assert "https://arxiv.org/abs/2603.12347" in urls

    def test_extracts_title_and_abstract_from_email(self, parser, mock_gmail_service):
        """Arxiv daily digests include title+abstract inline — should extract them."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML)
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)

        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        agent_paper = next(
            (p for p in arxiv_papers if "2603.12345" in p.url), None
        )
        assert agent_paper is not None
        assert "Agent-Based Optimization" in agent_paper.title
        assert "multi-agent collaboration" in agent_paper.abstract

    def test_extracts_all_arxiv_papers(self, parser, mock_gmail_service):
        """Should extract all 3 papers from the fixture."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML)
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        assert len(arxiv_papers) == 3


class TestHuggingFaceParsing:
    """Tests for extracting papers from HuggingFace emails."""

    def test_extracts_huggingface_urls(self, parser, mock_gmail_service):
        """Should extract huggingface.co/papers URLs."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg2"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message(
                "msg2", "no-reply@huggingface.co", HUGGINGFACE_EMAIL_HTML
            )
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)

        hf_papers = [p for p in papers if p.source == "huggingface"]
        urls = {p.url for p in hf_papers}
        assert "https://huggingface.co/papers/2603.11111" in urls
        assert "https://huggingface.co/papers/2603.11112" in urls

    def test_extracts_huggingface_titles(self, parser, mock_gmail_service):
        """Should extract title from HF link text."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg2"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message(
                "msg2", "no-reply@huggingface.co", HUGGINGFACE_EMAIL_HTML
            )
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        hf_papers = [p for p in papers if p.source == "huggingface"]
        titles = {p.title for p in hf_papers}
        assert "New Foundation Model for Code Generation" in titles


class TestDeduplication:
    """Tests for URL deduplication across emails."""

    def test_deduplicates_urls(self, parser, mock_gmail_service):
        """Same URL in multiple emails should only appear once."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }

        def get_side_effect(*args, **kwargs):
            mock = MagicMock()
            # Both messages return the same Arxiv email
            mock.execute.return_value = _make_gmail_message(
                "msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML
            )
            return mock

        mock_gmail_service.users().messages().get.return_value = MagicMock(
            execute=MagicMock(
                return_value=_make_gmail_message(
                    "msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML
                )
            )
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        urls = [p.url for p in papers]
        assert len(urls) == len(set(urls)), "Duplicate URLs found"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_no_messages(self, parser, mock_gmail_service):
        """No emails found should return empty list."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": []
        }

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        assert papers == []

    def test_handles_empty_email(self, parser, mock_gmail_service):
        """Email with no paper links should return empty list."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", EMPTY_EMAIL_HTML)
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        assert papers == []

    def test_handles_malformed_html(self, parser, mock_gmail_service):
        """Malformed HTML should not crash, just return empty."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", MALFORMED_EMAIL_HTML)
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        # Should not raise — just return whatever it can parse (possibly empty)
        assert isinstance(papers, list)

    def test_all_papers_have_source_tag(self, parser, mock_gmail_service):
        """Every returned paper should have a valid source tag."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML)
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        for paper in papers:
            assert paper.source in ("arxiv", "huggingface")
