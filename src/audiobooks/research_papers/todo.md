# LLM Wiki — TODO

## Phase 1: Repository Structure & Tool Setup

- [x] Create `wiki/` directory with `sources/`, `concepts/`, `queries/` subfolders
- [x] Create `wiki/index.md` dynamic entry point
- [x] Implement `wiki_engine/git_hooks.py` for auto-commit
- [x] Implement `wiki_engine/index_builder.py` for index regeneration
- [x] Add qmd install script

## Phase 2: Ingestion & Extraction Pipeline

- [x] Create `wiki_engine/models.py` — WikiPage dataclass, YAML frontmatter model
- [x] Create `wiki_engine/classifier.py` — classify transcript sections by topic
- [x] Create `wiki_engine/ingestion.py` — main ingestion logic:
  - [x] Parse transcript into sections
  - [x] Create source page in `wiki/sources/`
  - [x] Extract concepts via LLM
  - [x] Upsert concept pages (append if exists, create if new)
  - [x] Enforce page format: TLDR, Body, Counterarguments/Data Gaps
  - [x] Add `[[wikilinks]]` between related concepts
- [x] Create prompts: `classify_system.txt`, `extract_concepts_system.txt`, `update_concept_system.txt`
- [x] Rebuild index after ingestion

## Phase 3: Query & Memory Layer

- [x] Create `wiki_engine/search.py` — wrap qmd subprocess
- [x] Create `wiki_engine/query_saver.py` — save Q&A as wiki pages
- [ ] MCP server exposure — see Phase 5

## Phase 4: Linting Pass

- [x] Create `wiki_engine/linter.py`:
  - [x] Orphan page detection (no inbound `[[links]]`)
  - [x] Contradiction detection via LLM
  - [x] Implicit concept detection (frequent terms without own page)
  - [x] Write lint report to `wiki/lint_report.md`
- [x] Create `lint_system.txt` prompt

## Testing

- [x] `test_wiki_classifier.py` — classification works with mocked LLM
- [x] `test_wiki_ingestion.py` — source pages, concept pages, upsert logic, YAML, format
- [x] `test_wiki_search.py` — search integration
- [x] `test_wiki_query_saver.py` — query result saving
- [x] `test_wiki_linter.py` — orphans, contradictions, implicit concepts
- [x] `test_wiki_git_hooks.py` — auto-commit behavior
- [x] `test_wiki_e2e.py` — full end-to-end pipeline test
- [x] All tests pass

## Phase 5: MCP Server

- [x] Install `mcp` PyPI package (add to `requirements.txt`)
- [x] Create `wiki_engine/mcp_server.py`:
  - [x] Define `WikiMcpServer` class accepting injected `WikiSearch` and `QuerySaver`
  - [x] Implement `wiki_search` tool handler
  - [x] Implement `wiki_get_page` tool handler (with path traversal guard)
  - [x] Implement `wiki_list_pages` tool handler (supports optional `page_type` filter)
  - [x] Implement `wiki_save_query` tool handler
  - [x] `__main__` entry point: instantiate server with real `WikiSearch`/`QuerySaver` and run stdio server loop
- [x] Create `.vscode/mcp.json` to register server with VS Code Copilot
- [x] Add MCP server run/smoke test instructions to `README.md`

## Testing (Phase 5)

- [x] Create `tests/test_wiki_mcp_server.py`:
  - [x] `test_list_tools` — verify all 4 tools returned with correct schemas
  - [x] `test_tool_wiki_search` — mock `WikiSearch`, verify JSON result output
  - [x] `test_tool_wiki_get_page` — write temp page, verify content returned
  - [x] `test_tool_wiki_get_page_path_traversal` — verify `../` path rejected with error
  - [x] `test_tool_wiki_get_page_not_found` — verify NOT_FOUND error on missing file
  - [x] `test_tool_wiki_list_pages_all` — verify all page types returned
  - [x] `test_tool_wiki_list_pages_filtered` — verify `page_type` filter works
  - [x] `test_tool_wiki_save_query` — mock `QuerySaver`, verify returned path
  - [x] `test_tool_error_returns_text` — mock raises exception, verify error text response (not crash)
- [x] All Phase 5 tests pass
