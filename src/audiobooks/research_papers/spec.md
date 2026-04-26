# LLM Wiki — Specification

## Goals

Build a multi-stage pipeline that transforms daily research paper podcast transcripts into a searchable, versioned knowledge base ("LLM Wiki"), with automated concept extraction, query-result logging, and self-maintaining lint passes.

### Primary Goals

1. **Structured Knowledge Base** — Organize daily transcripts into `wiki/sources/`, synthesized ideas into `wiki/concepts/`, and saved Q&A exchanges into `wiki/queries/`.
2. **Automated Ingestion** — Classify transcripts, extract concepts via LLM, and upsert (not overwrite) concept pages using YAML frontmatter.
3. **Search & Query** — Integrate `qmd` for hybrid search (BM25 + semantic) and expose a query interface usable by LLM agents via MCP.
4. **Memory Persistence** — Save high-value Q&A results as wiki pages so insights don't disappear into ephemeral chat logs.
5. **Self-Maintenance** — Weekly lint pass finds contradictions, orphan pages, and implicit concepts that need their own pages.
6. **Version Control** — Every wiki mutation triggers a git commit for full audit trail.

---

## Architecture

```
research_papers/
├── wiki/                          # THE WIKI (git-tracked)
│   ├── index.md                   # Dynamic entry point
│   ├── sources/                   # Raw transcript source pages
│   ├── concepts/                  # Synthesized concept pages
│   └── queries/                   # Saved Q&A results
├── wiki_engine/                   # CODE for the wiki pipeline
│   ├── __init__.py
│   ├── classifier.py              # Transcript topic classifier
│   ├── ingestion.py               # LLM extraction & upsert logic
│   ├── search.py                  # qmd search integration
│   ├── query_saver.py             # Saves Q&A results as wiki pages
│   ├── linter.py                  # Weekly lint pass logic
│   ├── git_hooks.py               # Auto-commit on wiki changes
│   ├── index_builder.py           # Rebuilds wiki/index.md
│   ├── models.py                  # Data models for wiki pages
│   └── prompts/
│       ├── classify_system.txt
│       ├── extract_concepts_system.txt
│       ├── update_concept_system.txt
│       └── lint_system.txt
└── tests/
    ├── test_wiki_classifier.py
    ├── test_wiki_ingestion.py
    ├── test_wiki_search.py
    ├── test_wiki_query_saver.py
    ├── test_wiki_linter.py
    ├── test_wiki_git_hooks.py
    └── test_wiki_e2e.py
```

---

## Implementation Details

### Phase 1: Repository Structure & Tool Setup

| Component | Details |
|-----------|---------|
| `wiki/` directory | Three subfolders: `sources/`, `concepts/`, `queries/` |
| `wiki/index.md` | Dynamic index rebuilt on each ingestion run. Lists all pages grouped by type with wikilinks. |
| `qmd` installation | Script at `scripts/install_qmd.sh` (or npm script in package.json). Uses `npm install -g @tobilu/qmd`. |
| Git integration | `wiki_engine/git_hooks.py` — after any wiki file is written/updated, stage + commit with message describing the change. |

### Phase 2: Ingestion & Extraction Pipeline

| Component | Details |
|-----------|---------|
| **Input** | Transcripts from `raw_content/research_digest_*.txt` (output of existing pipeline) |
| **Classification** | LLM classifies each transcript section into categories (e.g., "AI Architecture", "Hardware", "Benchmarking", "Optimization") |
| **YAML Frontmatter** | Every wiki page starts with: `title`, `type` (concept/source/query-result), `sources` (list of URLs/papers), `created`, `updated`, `confidence` (0.0-1.0), `categories` |
| **Source Pages** | One per daily transcript in `wiki/sources/`, preserving the raw content with metadata |
| **Concept Extraction** | LLM extracts distinct concepts from transcript, checks existing `wiki/concepts/` for matches |
| **Upsert Logic** | If concept exists → LLM appends/edits with new findings (never overwrites). If new → creates page. |
| **Page Format** | Every concept page has: TLDR (1 sentence), Body (structured), Counterarguments/Data Gaps section |
| **Wikilinks** | Concept pages use `[[concept_name]]` linking syntax to cross-reference |

### Phase 3: Query & Memory Layer

| Component | Details |
|-----------|---------|
| **Search** | `wiki_engine/search.py` wraps `qmd query "..." --json` subprocess call. Returns ranked results. |
| **MCP Server** | `wiki_engine/mcp_server.py` — see Phase 5 below |
| **Query Saver** | `wiki_engine/query_saver.py` — takes a question + AI answer, formats into Markdown with `type: query-result` YAML, saves to `wiki/queries/` |
| **Naming** | Query files named: `wiki/queries/{date}_{slugified_question}.md` |

### Phase 4: Linting Pass

| Component | Details |
|-----------|---------|
| **Trigger** | Weekly script (can be cron or manual). Located at `wiki_engine/linter.py`. |
| **Contradiction Detection** | LLM reviews recently-updated pages for conflicting claims |
| **Orphan Detection** | Script scans all pages for `[[links]]` and finds pages with zero inbound links |
| **Implicit Concepts** | LLM identifies terms mentioned 3+ times across pages that lack their own concept page |
| **Output** | Lint report written to `wiki/lint_report.md` with actionable items |

---

## Configuration

Uses existing `config.ini` pattern. New section:

```ini
[wiki]
gemini_api_key = %(gemini_api_key)s
model_name = gemini-3.1-flash-lite-preview
wiki_dir = wiki
transcript_dir = raw_content
auto_commit = true
```

---

## Verification Plan

### Phase 1 Verification

| Test | How to verify |
|------|---------------|
| Wiki directory structure | `test_wiki_e2e.py::test_wiki_directories_created` — asserts `wiki/sources/`, `wiki/concepts/`, `wiki/queries/` exist after init |
| Index creation | `test_wiki_e2e.py::test_index_created` — asserts `wiki/index.md` exists and contains expected headers |
| Git hook | `test_wiki_git_hooks.py::test_auto_commit_on_write` — writes a file, verifies git log shows new commit |

### Phase 2 Verification

| Test | How to verify |
|------|---------------|
| Classification | `test_wiki_classifier.py::test_classify_transcript` — mock LLM, verify categories assigned |
| Source page creation | `test_wiki_ingestion.py::test_source_page_created` — ingest transcript, verify source page in `wiki/sources/` with YAML |
| Concept extraction | `test_wiki_ingestion.py::test_concepts_extracted` — ingest transcript, verify concept pages created |
| Upsert (no duplicate) | `test_wiki_ingestion.py::test_concept_upsert_appends` — ingest same concept twice, verify single file updated (not two files) |
| YAML frontmatter | `test_wiki_ingestion.py::test_yaml_frontmatter_valid` — all generated pages have valid YAML with required fields |
| Page format | `test_wiki_ingestion.py::test_page_has_required_sections` — TLDR, Body, Counterarguments sections present |

### Phase 3 Verification

| Test | How to verify |
|------|---------------|
| Search returns results | `test_wiki_search.py::test_search_returns_results` — populate wiki, run search, verify non-empty results |
| Query saver | `test_wiki_query_saver.py::test_save_query_result` — save Q&A, verify file in `wiki/queries/` with correct YAML |
| Query naming | `test_wiki_query_saver.py::test_query_file_naming` — verify slug format |

### Phase 4 Verification

| Test | How to verify |
|------|---------------|
| Orphan detection | `test_wiki_linter.py::test_find_orphan_pages` — create pages with no inlinks, verify linter finds them |
| Contradiction detection | `test_wiki_linter.py::test_find_contradictions` — mock LLM response, verify contradictions listed |
| Implicit concept detection | `test_wiki_linter.py::test_find_implicit_concepts` — pages mention term 3+ times without dedicated page, verify detection |
| Lint report output | `test_wiki_linter.py::test_lint_report_written` — run linter, verify `wiki/lint_report.md` exists |

---

## Dependencies

- `google-genai` (already in project for Gemini calls)
- `pyyaml` (YAML frontmatter parsing)
- `python-frontmatter` (convenient YAML+Markdown handling)
- `qmd` (npm package, installed globally)
- `gitpython` (programmatic git operations)
- `mcp` (PyPI: Model Context Protocol Python SDK — Phase 5)

---

## Phase 5: MCP Server

### Goals

Expose the wiki as a set of MCP tools so that LLM agents (GitHub Copilot, Claude Desktop, etc.) can search and update the wiki during a live conversation — without requiring the user to run scripts and paste results manually.

### Architecture

```
research_papers/
└── wiki_engine/
    └── mcp_server.py              # MCP server — exposes 4 tools over stdio
.vscode/
    └── mcp.json                   # VS Code MCP registration (points to mcp_server.py)
tests/
    └── test_wiki_mcp_server.py    # Unit tests for all tool handlers
```

The server uses **stdio transport** (stdin/stdout), which is the standard transport for locally-run MCP servers and is supported natively by VS Code Copilot and Claude Desktop.

### Tools Exposed

| Tool name | Description | Input schema | Output |
|-----------|-------------|--------------|--------|
| `wiki_search` | Hybrid BM25+semantic search over all wiki pages | `query: str`, `limit: int = 10` | JSON array of `{title, path, score, snippet}` |
| `wiki_get_page` | Read the full Markdown content of a wiki page | `path: str` (relative to wiki dir, e.g. `concepts/attention.md`) | Page content as plain text |
| `wiki_list_pages` | List all pages, optionally filtered by type | `page_type: str = ""` (`"concept"`, `"source"`, `"query-result"`, or empty for all) | JSON array of `{title, path, type, updated}` |
| `wiki_save_query` | Save a Q&A exchange as a persistent wiki page | `question: str`, `answer: str`, `sources: list[str] = []` | Path to the created file |

### Implementation Details

| Component | Details |
|-----------|---------|
| **Entry point** | `wiki_engine/mcp_server.py` — run via `python -m wiki_engine.mcp_server` from the `research_papers/` directory |
| **SDK** | `mcp` PyPI package (`from mcp.server import Server; from mcp.server.stdio import stdio_server`) |
| **Tool wiring** | `wiki_search` delegates to `WikiSearch(wiki_dir).query()`; `wiki_save_query` delegates to `QuerySaver(wiki_dir).save()` |
| **`wiki_get_page`** | Reads file at `wiki_dir / path`, returns raw text. Raises `McpError` (NOT_FOUND) if path does not exist or escapes the wiki dir. |
| **`wiki_list_pages`** | Walks `wiki/sources/`, `wiki/concepts/`, `wiki/queries/`. Parses YAML frontmatter for `title`, `type`, `updated`. Returns sorted list. |
| **Path safety** | All file paths are resolved and checked to be inside `wiki_dir` before reading. Never allow `..` traversal. |
| **Dependency injection** | `WikiSearch` and `QuerySaver` are passed in as constructor arguments to `WikiMcpServer` to keep all LLM/git calls mockable in tests. |
| **Error handling** | All tool handlers catch exceptions and return a structured error text response rather than crashing the server process. |

### VS Code Registration

Create `.vscode/mcp.json` at the project root to register the server with VS Code Copilot:

```json
{
  "servers": {
    "llm-wiki": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "wiki_engine.mcp_server"],
      "cwd": "${workspaceFolder}/src/audiobooks/research_papers",
      "env": {}
    }
  }
}
```

Once registered, agents can invoke `wiki_search`, `wiki_get_page`, `wiki_list_pages`, and `wiki_save_query` as tool calls mid-conversation.

### Phase 5 Verification

| Test | How to verify |
|------|---------------|
| Tool list | `test_wiki_mcp_server.py::test_list_tools` — instantiate server, call `list_tools()`, verify all 4 tool names returned with correct input schemas |
| `wiki_search` handler | `test_wiki_mcp_server.py::test_tool_wiki_search` — mock `WikiSearch.query()` returning 2 results, call tool handler, verify JSON output contains both results |
| `wiki_get_page` handler | `test_wiki_mcp_server.py::test_tool_wiki_get_page` — write a temp wiki page, call tool handler with its path, verify content returned |
| `wiki_get_page` path traversal | `test_wiki_mcp_server.py::test_tool_wiki_get_page_path_traversal` — pass `../../secrets.txt` as path, verify error response returned (not file read) |
| `wiki_get_page` missing file | `test_wiki_mcp_server.py::test_tool_wiki_get_page_not_found` — call with non-existent path, verify NOT_FOUND error |
| `wiki_list_pages` all types | `test_wiki_mcp_server.py::test_tool_wiki_list_pages_all` — create pages of each type, verify all returned |
| `wiki_list_pages` filtered | `test_wiki_mcp_server.py::test_tool_wiki_list_pages_filtered` — filter by `"concept"`, verify only concept pages returned |
| `wiki_save_query` handler | `test_wiki_mcp_server.py::test_tool_wiki_save_query` — mock `QuerySaver.save()`, call tool handler, verify returned path matches expected slug format |
| Error resilience | `test_wiki_mcp_server.py::test_tool_error_returns_text` — mock `WikiSearch.query()` to raise, verify handler returns error text response (not exception) |

---

## Constraints

- All LLM calls must be mockable in tests (never hit real APIs in CI)
- Wiki files are plain Markdown with YAML frontmatter — no proprietary formats
- The wiki pipeline is additive to the existing research paper pipeline; it consumes `raw_content/` output
- Follow existing project conventions: `config.ini` for secrets, dependency injection, abstract interfaces
