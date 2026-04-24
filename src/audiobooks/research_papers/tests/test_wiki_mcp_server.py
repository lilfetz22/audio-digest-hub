"""Tests for wiki_engine/mcp_server.py — WikiMcpServer tool handlers."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp import McpError

from wiki_engine.mcp_server import WikiMcpServer
from wiki_engine.search import WikiSearchResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def wiki_dir(tmp_path: Path) -> Path:
    """A temporary wiki directory with the standard subfolders."""
    for subdir in ("sources", "concepts", "queries"):
        (tmp_path / subdir).mkdir()
    return tmp_path


@pytest.fixture()
def mock_searcher() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_query_saver() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def server(wiki_dir: Path, mock_searcher: MagicMock, mock_query_saver: MagicMock) -> WikiMcpServer:
    return WikiMcpServer(
        wiki_dir=str(wiki_dir),
        searcher=mock_searcher,
        query_saver=mock_query_saver,
    )


# ---------------------------------------------------------------------------
# Phase 5: MCP Server Tests
# ---------------------------------------------------------------------------


class TestListTools:
    def test_list_tools_returns_four_tools(self, server: WikiMcpServer):
        names = [t["name"] for t in WikiMcpServer.TOOLS]
        assert names == ["wiki_search", "wiki_get_page", "wiki_list_pages", "wiki_save_query"]

    def test_all_tools_have_input_schema(self):
        for tool in WikiMcpServer.TOOLS:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_wiki_search_requires_query(self):
        tool = next(t for t in WikiMcpServer.TOOLS if t["name"] == "wiki_search")
        assert "query" in tool["inputSchema"]["required"]

    def test_wiki_get_page_requires_path(self):
        tool = next(t for t in WikiMcpServer.TOOLS if t["name"] == "wiki_get_page")
        assert "path" in tool["inputSchema"]["required"]

    def test_wiki_save_query_requires_question_and_answer(self):
        tool = next(t for t in WikiMcpServer.TOOLS if t["name"] == "wiki_save_query")
        assert "question" in tool["inputSchema"]["required"]
        assert "answer" in tool["inputSchema"]["required"]


class TestWikiSearch:
    def test_returns_json_array_of_results(
        self, server: WikiMcpServer, mock_searcher: MagicMock
    ):
        mock_searcher.query.return_value = [
            WikiSearchResult(title="Attention", path="concepts/attention.md", score=0.9, snippet="..."),
            WikiSearchResult(title="Transformers", path="concepts/transformers.md", score=0.7, snippet="..."),
        ]
        result = server.handle_wiki_search({"query": "attention mechanism"})
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["title"] == "Attention"
        assert data[1]["path"] == "concepts/transformers.md"

    def test_passes_limit_to_searcher(
        self, server: WikiMcpServer, mock_searcher: MagicMock
    ):
        mock_searcher.query.return_value = []
        server.handle_wiki_search({"query": "test", "limit": 5})
        mock_searcher.query.assert_called_once_with("test", limit=5)

    def test_empty_results_returns_empty_array(
        self, server: WikiMcpServer, mock_searcher: MagicMock
    ):
        mock_searcher.query.return_value = []
        result = server.handle_wiki_search({"query": "nothing"})
        assert json.loads(result) == []

    def test_result_fields_present(
        self, server: WikiMcpServer, mock_searcher: MagicMock
    ):
        mock_searcher.query.return_value = [
            WikiSearchResult(title="T", path="p", score=1.0, snippet="s")
        ]
        data = json.loads(server.handle_wiki_search({"query": "q"}))
        assert set(data[0].keys()) == {"title", "path", "score", "snippet"}


class TestWikiGetPage:
    def test_returns_file_content(self, server: WikiMcpServer, wiki_dir: Path):
        page = wiki_dir / "concepts" / "attention.md"
        page.write_text("# Attention\nsome content", encoding="utf-8")
        result = server.handle_wiki_get_page({"path": "concepts/attention.md"})
        assert result == "# Attention\nsome content"

    def test_not_found_raises_mcp_error(self, server: WikiMcpServer):
        with pytest.raises(McpError) as exc_info:
            server.handle_wiki_get_page({"path": "concepts/nonexistent.md"})
        assert "not found" in str(exc_info.value).lower()

    def test_path_traversal_rejected(self, server: WikiMcpServer, wiki_dir: Path):
        # Create a file outside wiki_dir to attempt to read
        secret = wiki_dir.parent / "secrets.txt"
        secret.write_text("top secret", encoding="utf-8")
        with pytest.raises(McpError) as exc_info:
            server.handle_wiki_get_page({"path": "../../secrets.txt"})
        # Most importantly — the secret content must NOT appear in the error
        assert "top secret" not in str(exc_info.value)

    def test_empty_path_returns_error(self, server: WikiMcpServer):
        result = server.handle_wiki_get_page({"path": ""})
        assert result.startswith("Error:")


class TestWikiListPages:
    def _write_page(self, folder: Path, filename: str, page_type: str, title: str) -> None:
        content = f"---\ntitle: {title}\ntype: {page_type}\nupdated: 2026-04-20\n---\n\nBody."
        (folder / filename).write_text(content, encoding="utf-8")

    def test_lists_all_pages_when_no_filter(
        self, server: WikiMcpServer, wiki_dir: Path
    ):
        self._write_page(wiki_dir / "concepts", "attention.md", "concept", "Attention")
        self._write_page(wiki_dir / "sources", "digest.md", "source", "Digest")
        self._write_page(wiki_dir / "queries", "q1.md", "query-result", "Q1")

        data = json.loads(server.handle_wiki_list_pages({}))
        types = {p["type"] for p in data}
        assert types == {"concept", "source", "query-result"}
        assert len(data) == 3

    def test_filters_by_concept_type(self, server: WikiMcpServer, wiki_dir: Path):
        self._write_page(wiki_dir / "concepts", "attention.md", "concept", "Attention")
        self._write_page(wiki_dir / "sources", "digest.md", "source", "Digest")

        data = json.loads(server.handle_wiki_list_pages({"page_type": "concept"}))
        assert len(data) == 1
        assert data[0]["type"] == "concept"
        assert data[0]["title"] == "Attention"

    def test_filters_by_source_type(self, server: WikiMcpServer, wiki_dir: Path):
        self._write_page(wiki_dir / "concepts", "attention.md", "concept", "Attention")
        self._write_page(wiki_dir / "sources", "digest.md", "source", "Digest")

        data = json.loads(server.handle_wiki_list_pages({"page_type": "source"}))
        assert len(data) == 1
        assert data[0]["type"] == "source"

    def test_empty_wiki_returns_empty_list(self, server: WikiMcpServer):
        data = json.loads(server.handle_wiki_list_pages({}))
        assert data == []

    def test_page_has_expected_fields(self, server: WikiMcpServer, wiki_dir: Path):
        self._write_page(wiki_dir / "concepts", "attention.md", "concept", "Attention")
        data = json.loads(server.handle_wiki_list_pages({}))
        assert set(data[0].keys()) == {"title", "path", "type", "updated"}

    def test_path_uses_forward_slashes(self, server: WikiMcpServer, wiki_dir: Path):
        self._write_page(wiki_dir / "concepts", "attention.md", "concept", "Attention")
        data = json.loads(server.handle_wiki_list_pages({}))
        assert "\\" not in data[0]["path"]


class TestWikiSaveQuery:
    def test_delegates_to_query_saver(
        self, server: WikiMcpServer, mock_query_saver: MagicMock, wiki_dir: Path
    ):
        mock_query_saver.save.return_value = wiki_dir / "queries" / "2026-04-21_my-question.md"
        result = server.handle_wiki_save_query(
            {"question": "My question?", "answer": "The answer.", "sources": ["http://example.com"]}
        )
        mock_query_saver.save.assert_called_once_with(
            question="My question?",
            answer="The answer.",
            sources=["http://example.com"],
        )
        assert "2026-04-21_my-question" in result

    def test_returns_path_string(
        self, server: WikiMcpServer, mock_query_saver: MagicMock, wiki_dir: Path
    ):
        expected = wiki_dir / "queries" / "2026-04-21_test.md"
        mock_query_saver.save.return_value = expected
        result = server.handle_wiki_save_query({"question": "Q?", "answer": "A."})
        assert isinstance(result, str)

    def test_sources_defaults_to_empty_list(
        self, server: WikiMcpServer, mock_query_saver: MagicMock, wiki_dir: Path
    ):
        mock_query_saver.save.return_value = wiki_dir / "queries" / "x.md"
        server.handle_wiki_save_query({"question": "Q?", "answer": "A."})
        _, kwargs = mock_query_saver.save.call_args
        assert kwargs.get("sources") == [] or mock_query_saver.save.call_args[1]["sources"] == []


class TestDispatchAndErrorResilience:
    def test_dispatch_routes_to_correct_handler(
        self, server: WikiMcpServer, mock_searcher: MagicMock
    ):
        mock_searcher.query.return_value = []
        result = server.dispatch("wiki_search", {"query": "test"})
        assert json.loads(result) == []

    def test_unknown_tool_returns_error(self, server: WikiMcpServer):
        result = server.dispatch("nonexistent_tool", {})
        assert "Error" in result
        assert "nonexistent_tool" in result

    def test_handler_exception_returns_error_text(
        self, server: WikiMcpServer, mock_searcher: MagicMock
    ):
        mock_searcher.query.side_effect = RuntimeError("search exploded")
        result = server.dispatch("wiki_search", {"query": "q"})
        assert result.startswith("Error:")
        assert "search exploded" in result

    def test_dispatch_does_not_raise_on_exception(
        self, server: WikiMcpServer, mock_searcher: MagicMock
    ):
        mock_searcher.query.side_effect = Exception("boom")
        # Must not raise — returns error string instead
        result = server.dispatch("wiki_search", {"query": "q"})
        assert isinstance(result, str)
