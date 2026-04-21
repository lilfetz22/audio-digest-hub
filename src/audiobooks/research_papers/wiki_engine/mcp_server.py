"""MCP server — exposes the LLM Wiki as tools for LLM agents (GitHub Copilot, Claude, etc.).

Run via:
    python -m wiki_engine.mcp_server

from the research_papers/ directory. The server communicates over stdio using the
Model Context Protocol JSON-RPC protocol.

Tools exposed:
    wiki_search       — hybrid BM25+semantic search over all wiki pages
    wiki_get_page     — read full Markdown content of a specific page
    wiki_list_pages   — list all pages, optionally filtered by type
    wiki_save_query   — persist a Q&A exchange as a wiki/queries/ page
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import yaml

from .query_saver import QuerySaver
from .search import WikiSearch

logger = logging.getLogger(__name__)

_WIKI_DIR_DEFAULT = Path(__file__).parent.parent / "wiki"


class WikiMcpServer:
    """Core wiki tool logic — independent of the MCP transport layer.

    All handler methods are plain synchronous functions so they can be unit-tested
    without running an async server loop or importing the ``mcp`` package.
    """

    TOOLS = [
        {
            "name": "wiki_search",
            "description": (
                "Hybrid BM25+semantic search over all LLM Wiki pages. "
                "Returns ranked results with title, path, score, and a snippet."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "wiki_get_page",
            "description": (
                "Read the full Markdown content of a single wiki page. "
                "Use wiki_list_pages first if you need to discover available paths."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative path within the wiki directory, "
                            "e.g. 'concepts/attention.md' or 'sources/digest_2026-04-20.md'"
                        ),
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "wiki_list_pages",
            "description": (
                "List all wiki pages grouped by type. "
                "Optionally filter by page_type: 'concept', 'source', or 'query-result'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "page_type": {
                        "type": "string",
                        "description": (
                            "Filter by page type. One of: 'concept', 'source', 'query-result'. "
                            "Leave empty to list all pages."
                        ),
                        "default": "",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "wiki_save_query",
            "description": (
                "Save a Q&A exchange as a persistent wiki page in wiki/queries/. "
                "Use this to preserve high-value answers so they don't disappear from chat history."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question that was asked",
                    },
                    "answer": {
                        "type": "string",
                        "description": "The AI answer to persist",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of source URLs referenced in the answer",
                        "default": [],
                    },
                },
                "required": ["question", "answer"],
            },
        },
    ]

    def __init__(
        self,
        wiki_dir: str,
        searcher: Optional[WikiSearch] = None,
        query_saver: Optional[QuerySaver] = None,
    ) -> None:
        self.wiki_dir = Path(wiki_dir).resolve()
        self.searcher = searcher or WikiSearch(wiki_dir=str(self.wiki_dir))
        self.query_saver = query_saver or QuerySaver(wiki_dir=str(self.wiki_dir))

    # ------------------------------------------------------------------
    # Tool handlers — public so tests can call them directly
    # ------------------------------------------------------------------

    def handle_wiki_search(self, arguments: dict) -> str:
        """Search the wiki and return JSON array of results."""
        query = arguments.get("query", "")
        limit = int(arguments.get("limit", 10))
        results = self.searcher.query(query, limit=limit)
        data = [
            {
                "title": r.title,
                "path": r.path,
                "score": r.score,
                "snippet": r.snippet,
            }
            for r in results
        ]
        return json.dumps(data, indent=2)

    def handle_wiki_get_page(self, arguments: dict) -> str:
        """Return the raw Markdown content of a wiki page."""
        raw_path = arguments.get("path", "")
        if not raw_path:
            return "Error: 'path' argument is required"

        try:
            target = (self.wiki_dir / raw_path).resolve()
        except Exception as exc:
            return f"Error: invalid path — {exc}"

        # Security: reject any path that escapes wiki_dir (e.g. ../../secrets.txt)
        try:
            target.relative_to(self.wiki_dir)
        except ValueError:
            return "Error: path traversal not allowed"

        if not target.exists():
            return f"Error: page not found: {raw_path}"
        if not target.is_file():
            return f"Error: path is not a file: {raw_path}"

        return target.read_text(encoding="utf-8")

    def handle_wiki_list_pages(self, arguments: dict) -> str:
        """Return a JSON array of all wiki pages, optionally filtered by type."""
        page_type_filter = (arguments.get("page_type") or "").strip().lower()
        pages = []

        for subdir in ("sources", "concepts", "queries"):
            folder = self.wiki_dir / subdir
            if not folder.exists():
                continue
            for md_file in sorted(folder.glob("*.md")):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    meta = self._parse_frontmatter(content)
                    page_type = meta.get("type", "")
                    if page_type_filter and page_type != page_type_filter:
                        continue
                    pages.append(
                        {
                            "title": meta.get("title", md_file.stem),
                            "path": str(md_file.relative_to(self.wiki_dir)).replace("\\", "/"),
                            "type": page_type,
                            "updated": str(meta.get("updated", "")),
                        }
                    )
                except Exception:
                    continue

        return json.dumps(pages, indent=2)

    def handle_wiki_save_query(self, arguments: dict) -> str:
        """Save a Q&A exchange to wiki/queries/ and return the file path."""
        question = arguments.get("question", "")
        answer = arguments.get("answer", "")
        sources = arguments.get("sources") or []
        saved_path = self.query_saver.save(
            question=question, answer=answer, sources=list(sources)
        )
        return str(saved_path)

    def dispatch(self, tool_name: str, arguments: dict) -> str:
        """Route a tool call to the appropriate handler.

        All exceptions are caught and returned as error strings so the server
        process never crashes due to a bad tool call.
        """
        handlers = {
            "wiki_search": self.handle_wiki_search,
            "wiki_get_page": self.handle_wiki_get_page,
            "wiki_list_pages": self.handle_wiki_list_pages,
            "wiki_save_query": self.handle_wiki_save_query,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return f"Error: unknown tool '{tool_name}'"
        try:
            return handler(arguments)
        except Exception as exc:
            logger.exception("Tool '%s' raised an unhandled error", tool_name)
            return f"Error: {exc}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        """Extract YAML frontmatter from a Markdown string."""
        if not content.startswith("---"):
            return {}
        try:
            end = content.index("---", 3)
            return yaml.safe_load(content[3:end]) or {}
        except Exception:
            return {}


# ------------------------------------------------------------------
# MCP server wiring (only runs when the mcp package is installed)
# ------------------------------------------------------------------

def _build_mcp_server(wiki_mcp: WikiMcpServer):
    """Wire a WikiMcpServer into an mcp.server.Server instance.

    Separated from __main__ so integration tests can import it without
    triggering asyncio.run().
    """
    try:
        from mcp.server import Server
        from mcp import types as mcp_types
    except ImportError as exc:
        raise ImportError(
            "The 'mcp' package is required to run the MCP server. "
            "Install it with: pip install mcp"
        ) from exc

    server = Server("llm-wiki")

    @server.list_tools()
    async def list_tools() -> list:
        return [
            mcp_types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in WikiMcpServer.TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        result = wiki_mcp.dispatch(name, arguments or {})
        return [mcp_types.TextContent(type="text", text=result)]

    return server


async def _run_server(wiki_dir: str) -> None:
    """Start the stdio MCP server."""
    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError(
            "The 'mcp' package is required to run the MCP server. "
            "Install it with: pip install mcp"
        ) from exc

    wiki_mcp = WikiMcpServer(wiki_dir=wiki_dir)
    server = _build_mcp_server(wiki_mcp)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(_run_server(str(_WIKI_DIR_DEFAULT)))
