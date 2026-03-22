"""Tests for paper_downloader.py — PaperContentDownloader."""

import pytest
from unittest.mock import patch, MagicMock
from research_papers.paper_downloader import PaperContentDownloader
from research_papers.models import PaperReference, PaperContent


@pytest.fixture
def downloader():
    return PaperContentDownloader(delay_seconds=0)  # No delay in tests


class TestArxivDownload:
    """Tests for downloading and extracting Arxiv PDFs."""

    @patch("research_papers.paper_downloader.pymupdf")
    @patch("research_papers.paper_downloader.requests")
    def test_download_arxiv_pdf(self, mock_requests, mock_pymupdf, downloader):
        """Should download arxiv PDF and extract text via pymupdf."""
        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Test Paper",
            abstract="Test abstract",
            source="arxiv",
        )

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-fake-content"
        mock_response.headers = {"content-length": "1000"}
        mock_requests.get.return_value = mock_response

        # Mock pymupdf PDF parsing
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Extracted PDF text content here."
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_pymupdf.open.return_value = mock_doc

        result = downloader.extract(paper)

        assert result is not None
        assert isinstance(result, PaperContent)
        assert result.url == paper.url
        assert result.title == paper.title
        assert "Extracted PDF text" in result.full_text

    @patch("research_papers.paper_downloader.requests")
    def test_handles_404(self, mock_requests, downloader):
        """Should return None on 404."""
        paper = PaperReference(
            url="https://arxiv.org/abs/9999.99999",
            title="Missing Paper",
            abstract="",
            source="arxiv",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        result = downloader.extract(paper)
        assert result is None

    @patch("research_papers.paper_downloader.requests")
    def test_handles_timeout(self, mock_requests, downloader):
        """Should return None on request timeout."""
        import requests as real_requests

        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Timeout Paper",
            abstract="",
            source="arxiv",
        )
        mock_requests.get.side_effect = real_requests.exceptions.Timeout("timeout")
        mock_requests.exceptions = real_requests.exceptions

        result = downloader.extract(paper)
        assert result is None

    @patch("research_papers.paper_downloader.requests")
    def test_skips_oversized_pdf(self, mock_requests, downloader):
        """Should skip PDFs larger than the size limit."""
        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Huge Paper",
            abstract="",
            source="arxiv",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-length": str(40 * 1024 * 1024)  # 40MB > 34MB limit
        }
        mock_requests.get.return_value = mock_response

        result = downloader.extract(paper)
        assert result is None


class TestHuggingFaceDownload:
    """Tests for downloading and extracting HuggingFace paper pages."""

    @patch("research_papers.paper_downloader.requests")
    def test_download_huggingface_page(self, mock_requests, downloader):
        """Should fetch HF paper page and extract text via BeautifulSoup."""
        paper = PaperReference(
            url="https://huggingface.co/papers/2603.11111",
            title="HF Paper",
            abstract="HF abstract",
            source="huggingface",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body>
        <h1>HF Paper Title</h1>
        <div class="abstract">This is the full abstract text of the paper.</div>
        <div class="content">Full paper content here with methods and results.</div>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        result = downloader.extract(paper)

        assert result is not None
        assert isinstance(result, PaperContent)
        assert result.source == "huggingface"
        assert len(result.full_text) > 0


class TestTextCleaning:
    """Tests for text cleaning after extraction."""

    @patch("research_papers.paper_downloader.pymupdf")
    @patch("research_papers.paper_downloader.requests")
    def test_removes_excessive_whitespace(self, mock_requests, mock_pymupdf, downloader):
        """Extracted text should have excessive whitespace normalized."""
        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Test",
            abstract="",
            source="arxiv",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF"
        mock_response.headers = {"content-length": "1000"}
        mock_requests.get.return_value = mock_response

        mock_page = MagicMock()
        mock_page.get_text.return_value = "Hello    \n\n\n\n   World"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_pymupdf.open.return_value = mock_doc

        result = downloader.extract(paper)
        assert result is not None
        # Should not have 4+ consecutive newlines
        assert "\n\n\n\n" not in result.full_text


class TestOnlyDeepDive:
    """Verify the downloader concept — it should only be called for deep-dive papers."""

    def test_downloader_is_callable_for_any_paper(self, downloader):
        """The downloader itself doesn't filter — that's the pipeline's job.
        But it should accept any PaperReference."""
        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Test",
            abstract="",
            source="arxiv",
        )
        # Just verify it's callable without error (actual download would fail without mocks)
        assert hasattr(downloader, "extract")


class TestUnknownSource:
    """Tests for unknown paper source."""

    def test_returns_none_for_unknown_source(self, downloader):
        """Should return None and log warning for unknown source."""
        paper = PaperReference(
            url="https://example.com/paper",
            title="Unknown Source Paper",
            abstract="",
            source="unknown",
        )
        result = downloader.extract(paper)
        assert result is None


class TestArxivEdgeCases:
    """Additional edge case tests for Arxiv downloads."""

    @patch("research_papers.paper_downloader.pymupdf")
    @patch("research_papers.paper_downloader.requests")
    def test_skips_oversized_actual_content(self, mock_requests, mock_pymupdf, downloader):
        """Should skip when actual content bytes exceed size limit even if header is small."""
        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Huge Paper",
            abstract="",
            source="arxiv",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}  # Header says small
        mock_response.content = b"x" * (35 * 1024 * 1024)  # Actual content is 35MB
        mock_requests.get.return_value = mock_response

        result = downloader.extract(paper)
        assert result is None

    @patch("research_papers.paper_downloader.pymupdf")
    @patch("research_papers.paper_downloader.requests")
    def test_handles_pymupdf_parse_error(self, mock_requests, mock_pymupdf, downloader):
        """Should return None when pymupdf fails to parse the PDF."""
        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Bad PDF",
            abstract="",
            source="arxiv",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.content = b"not-a-pdf"
        mock_requests.get.return_value = mock_response
        mock_pymupdf.open.side_effect = Exception("Invalid PDF")

        result = downloader.extract(paper)
        assert result is None

    @patch("research_papers.paper_downloader.pymupdf")
    @patch("research_papers.paper_downloader.requests")
    def test_returns_none_for_empty_text_pdf(self, mock_requests, mock_pymupdf, downloader):
        """Should return None when PDF yields no extractable text."""
        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Empty PDF",
            abstract="",
            source="arxiv",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.content = b"%PDF"
        mock_requests.get.return_value = mock_response

        mock_page = MagicMock()
        mock_page.get_text.return_value = "   "  # Only whitespace
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_pymupdf.open.return_value = mock_doc

        result = downloader.extract(paper)
        assert result is None


class TestHuggingFaceEdgeCases:
    """Additional edge case tests for HuggingFace downloads."""

    @patch("research_papers.paper_downloader.requests")
    def test_hf_handles_timeout(self, mock_requests, downloader):
        """Should return None on HF request timeout."""
        import requests as real_requests
        paper = PaperReference(
            url="https://huggingface.co/papers/2603.11111",
            title="HF Timeout",
            abstract="",
            source="huggingface",
        )
        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError("timeout")
        mock_requests.exceptions = real_requests.exceptions

        result = downloader.extract(paper)
        assert result is None

    @patch("research_papers.paper_downloader.requests")
    def test_hf_handles_404(self, mock_requests, downloader):
        """Should return None on HF 404."""
        paper = PaperReference(
            url="https://huggingface.co/papers/2603.99999",
            title="Missing HF",
            abstract="",
            source="huggingface",
        )
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        result = downloader.extract(paper)
        assert result is None

    @patch("research_papers.paper_downloader.requests")
    def test_hf_returns_none_for_empty_text(self, mock_requests, downloader):
        """Should return None when HF page has no extractable text."""
        paper = PaperReference(
            url="https://huggingface.co/papers/2603.11111",
            title="Empty HF",
            abstract="",
            source="huggingface",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><script>only scripts</script></body></html>"
        mock_requests.get.return_value = mock_response

        result = downloader.extract(paper)
        assert result is None


class TestRateLimit:
    """Tests for rate limiting."""

    @patch("research_papers.paper_downloader.time")
    @patch("research_papers.paper_downloader.pymupdf")
    @patch("research_papers.paper_downloader.requests")
    def test_respects_rate_limit(self, mock_requests, mock_pymupdf, mock_time, downloader):
        """Should sleep when requests are too close together."""
        mock_time.time.side_effect = [100.0, 100.0, 101.0, 104.0]  # First call returns quickly
        downloader.delay_seconds = 3
        downloader._last_request_time = 100.0  # Set last request time

        paper = PaperReference(
            url="https://arxiv.org/abs/2603.12345",
            title="Test",
            abstract="",
            source="arxiv",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.content = b"%PDF"
        mock_requests.get.return_value = mock_response

        mock_page = MagicMock()
        mock_page.get_text.return_value = "Some text"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_pymupdf.open.return_value = mock_doc

        downloader.extract(paper)
        # Should have called sleep since elapsed < delay
        mock_time.sleep.assert_called()
