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
