# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A monorepo with three loosely-coupled subsystems that together turn email newsletters and research-paper digests into a daily audiobook:

1. **Python pipeline** (`src/audiobooks/`) — runs headless (GitHub Actions / cron), reads Gmail, generates a transcript, synthesizes MP3 with Kokoro TTS, uploads to the backend.
2. **Supabase backend** (`supabase/`) — Postgres + storage + Deno edge functions that the Python pipeline POSTs to and the frontend reads from.
3. **React frontend** (`src/` outside `audiobooks/`) — Vite + TypeScript + shadcn/ui player and dashboard.

The Python side is the center of gravity; the frontend is mostly a consumer of what the pipeline produces.

## Commands

### Frontend

```bash
npm run dev          # Vite dev server
npm run build        # production build
npm run lint         # eslint (the only frontend check — there is no JS test suite)
```

### Python pipeline

Run from the repo root with the venv at `src/audiobooks/.venv` (or `audiogeneratorvenv`); `pipeline.py` locates the interpreter itself.

```bash
python pipeline.py                          # full daily run (research pipeline → audiobook)
python pipeline.py --skip-cleanup           # skip the Friday-only cleanup steps
python pipeline.py --reset-latest-research-day   # maintenance: drop the newest day from seen_papers.csv and exit
```

Individual stages:

```bash
python src/audiobooks/research_papers/run_research_pipeline.py --date 2026-03-19
python src/audiobooks/generate_audiobook.py --start-date 2026-03-15 --end-date 2026-03-19
python src/audiobooks/generate_audiobook.py --reauth   # force Google OAuth, rewrite token.json, exit
python src/audiobooks/generate_tts_audio.py path/to/digest.txt --voice af_heart
python src/audiobooks/upload_mp3.py "C:\path\to\file.mp3"   # manual upload, auto-splits >35 MB
```

With no date flags, `generate_audiobook.py` queries the audiobooks API for the last upload date and processes from the day after through yesterday. `run_research_pipeline.py` defaults to yesterday.

### Python tests

There is no pytest config file — rely on default discovery. Test files use both `test_*.py` (research_papers) and `*_test.py` (top-level audiobooks) naming.

```bash
cd src/audiobooks && python -m pytest                       # everything
cd src/audiobooks && python -m pytest generate_audiobook_test.py -v
cd src/audiobooks/research_papers && pytest tests/ -v
cd src/audiobooks/research_papers && pytest tests/test_pipeline.py -v
cd src/audiobooks/research_papers && pytest tests/test_pipeline.py::TestName::test_case -v
```

`research_papers/tests/conftest.py` inserts `research_papers/` and `src/audiobooks/` into `sys.path` and stubs `sentence_transformers` and `pymupdf` in `pytest_configure`, so tests run without those heavy deps installed. If you add a module that imports a heavy optional dep at import time, add a stub there or collection will break.

### Supabase

Schema is managed **remote-first** (see `workflow_for_new_features.md`): make changes in the Supabase dashboard, download them as a migration file into `supabase/migrations/`, then regenerate types:

```bash
npx supabase gen types typescript --project-id fpflgstvoztlbmowvpeo > src/integrations/supabase/types.ts
```

Do not author migrations locally and push them up.

## Architecture

### Daily data flow

```
Gmail ──┬─ arxiv/HF digest emails ─→ research_papers pipeline ─→ raw_content/research_digest_{date}.txt
        │                                     └─→ paper metadata POST → Supabase /research-papers
        └─ newsletter emails ────────────────────────┐
                                                     ▼
                              generate_audiobook.py: emails + raw_content/*.txt for the date
                                                     ▼
                              generate_tts_audio.py (Kokoro, CPU, 24 kHz) → archive_mp3/*.mp3
                                                     ▼
                              upload → Supabase /audiobooks edge function → storage + DB
                                                     ▼
                              React player (chapters = one text block per source)
```

The two Python stages communicate through the **filesystem**, not function calls: the research pipeline writes `src/audiobooks/raw_content/research_digest_{date}.txt`, and `generate_audiobook.py` picks up any `raw_content/` file whose filename carries that date and concatenates it with the day's newsletter emails. That directory is gitignored.

### research_papers subsystem

Strict SOLID/DI layout — `interfaces.py` defines abstract contracts, concrete classes are constructor-injected by `pipeline.py`, and `run_research_pipeline.py` is the only wiring/config/CLI layer. Every external call (Gmail, Gemini, HTTP) is mockable; the test suite never hits a real API. Read `src/audiobooks/research_papers/README.md` before changing anything here — it documents each component in depth.

Two things worth knowing before editing:

- **Arxiv and HuggingFace take different paths.** HF papers skip scoring entirely and are all `deep_dive`. Arxiv papers are Gemini-scored 1–10 and tiered *per category* (top N deep-dive, next M summary, rest discarded) so one high-volume category can't crowd out the others.
- **`dedup.py` maintains a 14-day rolling window** in `seen_papers.csv`, which is **committed to the repo** by the GitHub Actions workflow so dedup state survives between runs. That is why the commit log is full of `chore: update seen_papers.csv [skip ci]`.

All Gemini calls go through `gemini_client.GeminiClientWithFallback`, which walks primary key → backup key → paid key, each across a model chain, treating 429 as "skip to next key tier immediately" rather than burning retries. Add new LLM calls through this class, not a raw `genai.Client`.

### wiki_engine

`src/audiobooks/research_papers/wiki_engine/` ingests generated transcripts into a Markdown knowledge base and exposes it over MCP (`python -m wiki_engine.mcp_server`, 4 tools). The `wiki/` directory is a **git submodule** pointing at a separate private repo — treat it as external state, and expect it to be absent or empty in fresh clones that skipped `--recurse-submodules`.

Provenance relies on `<!-- WIKI_SOURCE_URL: ... -->` markers that `transcript_generator.py` embeds per deep-dive section and `ingestion.py` parses in Python. Do not remove those markers or ask the LLM to re-derive URLs from prose.

### Backend auth model

Edge functions (`supabase/functions/{audiobooks,sources,research-papers,cleanup}/index.ts`) authenticate the Python pipeline with a **bearer API key that is SHA-256 hashed and matched against the `api_keys` table** — not a Supabase JWT. The frontend, by contrast, uses Supabase Auth with RLS; every route except `/` is wrapped in `ProtectedRoute`. Keep those two paths separate when adding endpoints.

## Configuration and secrets

`src/audiobooks/config.ini` holds everything (`[WebApp]`, `[Gmail]`, `[Gemini]`, `[ResearchPapers]` sections) and is gitignored, along with `credentials.json` and `token.json`. There is no committed example file; the section/key layout is documented in `src/audiobooks/research_papers/README.md`.

In CI, `.github/workflows/daily-digest.yml` reconstructs all three files from the `CONFIG_INI`, `GOOGLE_CREDENTIALS_JSON`, and `GOOGLE_TOKEN_JSON` secrets, and writes the refreshed OAuth token back to `GOOGLE_TOKEN_JSON` via `GH_PAT` after every run. If you change what the pipeline reads from disk, update that workflow step too.

Frontend config comes from `.env.local` (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`).

## Conventions

- **Conventional Commits** for every commit message (from `.cursorrules`).
- Kokoro TTS requires `espeak-ng` on the host for phonemization; text is chunked to 250 characters before synthesis.
- The Friday-only cleanup (`scripts/cleanup-trigger.js` + `scripts/cleanup-local-files.js`) deletes audiobooks older than a Friday at least 7 days back — always a full week of retention. Test it with `node scripts/cleanup-trigger.js --force`.

## Known quirk

`generate_audiobook.py` defines `process_emails` **twice** (around lines 350 and 443). The second definition wins at import time; the first is dead code. Edit the later one, or the change silently does nothing.
