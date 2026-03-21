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


def _make_gmail_message(msg_id, sender, html_body, subject="Daily Digest"):
    """Helper to create a mock Gmail API message dict."""
    import base64

    encoded = base64.urlsafe_b64encode(html_body.encode("utf-8")).decode("utf-8")
    return {
        "id": msg_id,
        "payload": {
            "headers": [
                {"name": "From", "value": f"Papers <{sender}>"},
                {"name": "Subject", "value": subject},
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
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="[cs] daily digest")
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
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="[cs] daily digest")
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
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="[cs] daily digest")
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        assert len(arxiv_papers) == 3


class TestCategoryExtraction:
    """Tests for extracting category from Arxiv email subject line."""

    def test_extracts_cs_category(self, parser, mock_gmail_service):
        """Should extract 'cs' from subject '[cs] daily digest'."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="[cs] daily digest")
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        for p in arxiv_papers:
            assert p.category == "cs"

    def test_extracts_stat_category(self, parser, mock_gmail_service):
        """Should extract 'stat' from subject '[stat] daily listings'."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="[stat] daily listings")
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        for p in arxiv_papers:
            assert p.category == "stat"

    def test_extracts_math_category(self, parser, mock_gmail_service):
        """Should extract 'math' from subject '[math] daily digest'."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="[math] daily digest")
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        for p in arxiv_papers:
            assert p.category == "math"

    def test_fallback_category_on_missing_brackets(self, parser, mock_gmail_service):
        """Should default to 'arxiv' when subject has no [category] brackets."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="Daily paper digest")
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        for p in arxiv_papers:
            assert p.category == "arxiv"

    def test_hf_papers_have_empty_category(self, parser, mock_gmail_service):
        """HuggingFace papers should have empty category."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg2"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg2", "no-reply@huggingface.co", HUGGINGFACE_EMAIL_HTML)
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        hf_papers = [p for p in papers if p.source == "huggingface"]
        for p in hf_papers:
            assert p.category == ""


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
            _make_gmail_message("msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML, subject="[cs] daily digest")
        )

        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        for paper in papers:
            assert paper.source in ("arxiv", "huggingface")

    def test_requires_gmail_service(self, parser):
        """Should raise ValueError when gmail_service is None."""
        with pytest.raises(ValueError, match="gmail_service is required"):
            parser.fetch_papers("2026-03-14", gmail_service=None)

    def test_empty_senders_returns_empty(self, mock_gmail_service):
        """Should return empty list when no senders configured."""
        empty_parser = ArxivHFEmailParser(
            arxiv_senders=[], huggingface_senders=[]
        )
        papers = empty_parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        assert papers == []

    def test_skips_message_with_no_html_body(self, parser, mock_gmail_service):
        """Should skip messages where HTML body extraction returns None."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        # Message with no body data at all
        mock_gmail_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [{"name": "From", "value": "<no-reply@arxiv.org>"}],
            },
        }
        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        assert papers == []

    def test_skips_unknown_sender(self, parser, mock_gmail_service):
        """Should skip emails from senders not in arxiv or huggingface lists."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message("msg1", "unknown@example.com", ARXIV_EMAIL_HTML)
        )
        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        assert papers == []

    def test_query_gmail_exception(self, parser, mock_gmail_service):
        """Gmail query exception should return empty list."""
        mock_gmail_service.users().messages().list().execute.side_effect = Exception("API error")
        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        assert papers == []


class TestExtractSender:
    """Tests for _extract_sender helper."""

    def test_sender_without_angle_brackets(self, parser):
        """Should handle From header without angle brackets."""
        msg = {
            "payload": {
                "headers": [{"name": "From", "value": "no-reply@arxiv.org"}]
            }
        }
        result = parser._extract_sender(msg)
        assert result == "no-reply@arxiv.org"

    def test_sender_with_angle_brackets(self, parser):
        """Should extract email from angle brackets."""
        msg = {
            "payload": {
                "headers": [{"name": "From", "value": "Arxiv <no-reply@arxiv.org>"}]
            }
        }
        result = parser._extract_sender(msg)
        assert result == "no-reply@arxiv.org"

    def test_sender_missing_from_header(self, parser):
        """Should return empty string when From header is missing."""
        msg = {
            "payload": {
                "headers": [{"name": "Subject", "value": "Test"}]
            }
        }
        result = parser._extract_sender(msg)
        assert result == ""


class TestExtractHtmlBody:
    """Tests for _extract_html_body helper."""

    def test_extracts_body_from_direct_payload(self, parser):
        """Should extract body when data is in payload.body directly (no parts)."""
        import base64
        html = "<html><body>Hello</body></html>"
        encoded = base64.urlsafe_b64encode(html.encode()).decode()
        msg = {
            "payload": {
                "body": {"data": encoded}
            }
        }
        result = parser._extract_html_body(msg)
        assert result is not None
        assert "Hello" in result

    def test_returns_none_on_empty_payload(self, parser):
        """Should return None when payload has no parts and no body data."""
        msg = {"payload": {}}
        result = parser._extract_html_body(msg)
        assert result is None

    def test_handles_extraction_exception(self, parser):
        """Should return None on exception during body extraction."""
        msg = {
            "payload": {
                "parts": [{"mimeType": "text/html", "body": {"data": "!!!invalid-base64"}}]
            }
        }
        result = parser._extract_html_body(msg)
        # Should not crash; returns None or partial result
        assert result is None or isinstance(result, str)


class TestUnbracketedCategory:
    """Tests for the unbracketed category format (e.g. 'cs daily ...')."""

    def test_extracts_cs_from_unbracketed_subject(self, parser, mock_gmail_service):
        """Should extract 'cs' from 'cs daily Subj-class mailing...'."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message(
                "msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML,
                subject="cs daily Subj-class mailing for Fri, 21 Mar 2026"
            )
        )
        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        for p in arxiv_papers:
            assert p.category == "cs"

    def test_extracts_stat_from_unbracketed_subject(self, parser, mock_gmail_service):
        """Should extract 'stat' from 'stat daily Subj-class mailing...'."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message(
                "msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML,
                subject="stat daily Subj-class mailing for Fri, 21 Mar 2026"
            )
        )
        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        for p in arxiv_papers:
            assert p.category == "stat"

    def test_extracts_subcategory_from_unbracketed(self, parser, mock_gmail_service):
        """Should extract 'cs.AI' from 'cs.AI daily ...'."""
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            _make_gmail_message(
                "msg1", "no-reply@arxiv.org", ARXIV_EMAIL_HTML,
                subject="cs.AI daily Subj-class mailing for Fri, 21 Mar 2026"
            )
        )
        papers = parser.fetch_papers("2026-03-14", gmail_service=mock_gmail_service)
        arxiv_papers = [p for p in papers if p.source == "arxiv"]
        for p in arxiv_papers:
            assert p.category == "cs.ai"


class TestStrategy2LineParser:
    """Tests for the plain-text line-by-line Arxiv email parser (Strategy 2)."""

    def test_parses_plain_text_arxiv_format(self, parser):
        """Should parse plain-text Arxiv digest format with Title:/Abstract."""
        plain_text_html = (
            "<html><body><pre>\n"
            "\\\\\n"
            "arXiv:2603.55555\n"
            "Date: Fri, 21 Mar 2026\n"
            "\n"
            "Title: A Novel Approach to Reinforcement Learning\n"
            "  in Complex Environments\n"
            "Authors: Jane Doe, John Smith\n"
            "Categories: cs.AI cs.LG\n"
            "\\\\\n"
            "  We present a groundbreaking method for RL\n"
            "  that outperforms existing baselines.\n"
            "\\\\ ( https://arxiv.org/abs/2603.55555 , 42kb)\n"
            "------------------------------------------------------------------------------\n"
            "\\\\\n"
            "arXiv:2603.55556\n"
            "Date: Fri, 21 Mar 2026\n"
            "\n"
            "Title: Graph Neural Networks for Optimization\n"
            "Authors: Alice Bob\n"
            "Categories: cs.LG\n"
            "\\\\\n"
            "  A new GNN architecture for combinatorial problems.\n"
            "\\\\ ( https://arxiv.org/abs/2603.55556 , 38kb)\n"
            "------------------------------------------------------------------------------\n"
            "</pre></body></html>"
        )
        papers = parser._parse_arxiv_email(plain_text_html, category="cs")
        assert len(papers) >= 2

        urls = {p.url for p in papers}
        assert "https://arxiv.org/abs/2603.55555" in urls
        assert "https://arxiv.org/abs/2603.55556" in urls

        # Check title extraction for multi-line title
        paper1 = next(p for p in papers if "55555" in p.url)
        assert "Reinforcement Learning" in paper1.title


class TestHuggingFaceParsing2:
    """Additional tests for HuggingFace email parsing."""

    def test_hf_paper_without_abstract(self, parser):
        """HF paper link without a following <p> should still be extracted."""
        html = '<html><body><a href="https://huggingface.co/papers/2603.99999">Standalone Paper</a></body></html>'
        papers = parser._parse_huggingface_email(html)
        assert len(papers) == 1
        assert papers[0].title == "Standalone Paper"
        assert papers[0].source == "huggingface"

    def test_hf_paper_with_no_link_text(self, parser):
        """HF paper link with empty text should use fallback title."""
        html = '<html><body><a href="https://huggingface.co/papers/2603.88888"></a></body></html>'
        papers = parser._parse_huggingface_email(html)
        assert len(papers) == 1
        assert "2603.88888" in papers[0].title
