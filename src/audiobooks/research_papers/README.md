# Research Papers Pipeline

An automated pipeline that fetches daily research papers from **Arxiv** and **HuggingFace** email digests, scores them by relevance using AI, downloads top papers, and generates a single-narrator podcast transcript — all feeding into the existing TTS audiobook generation system.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Components](#components)
  - [Email Parser](#email-parser)
  - [Paper Downloader](#paper-downloader)
  - [Paper Scorer](#paper-scorer)
  - [Transcript Generator](#transcript-generator)
  - [Feedback System](#feedback-system)
  - [Pipeline Orchestrator](#pipeline-orchestrator)
- [Data Models](#data-models)
- [Prompts](#prompts)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Single Date](#single-date)
  - [Date Range](#date-range)
  - [Default (Yesterday)](#default-yesterday)
- [Output](#output)
- [Feedback Loop](#feedback-loop)
- [Design Principles](#design-principles)
- [Testing](#testing)
- [Dependencies](#dependencies)
- [Project Structure](#project-structure)

---

## Overview

This pipeline solves the problem of staying current with AI research at scale. It processes two distinct paper sources with different strategies:

| Source | Volume | Strategy |
|--------|--------|----------|
| **HuggingFace** | ~10 papers/day | All papers get full deep-dive treatment (curated, high signal) |
| **Arxiv** | 50+ papers/day | AI-scored by relevance → top papers get deep-dives, rest get brief summaries |

The final output is a text transcript deposited into `raw_content/` where the existing TTS pipeline (`generate_audiobook.py`) picks it up automatically for audio conversion.

---

## Architecture

The system follows SOLID principles with dependency injection throughout:

- **Abstract interfaces** ([interfaces.py](interfaces.py)) define contracts for every component
- **Concrete implementations** are injected via constructor, making components testable and swappable
- **Single Responsibility**: each module handles exactly one concern
- **All external API calls are mockable** — the test suite never hits real APIs

```
┌─────────────────────────────────────────────────────────────────────┐
│                      run_research_pipeline.py                       │
│                     (CLI entry point + wiring)                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ResearchPaperPipeline                            │
│                   (pipeline.py — orchestrator)                      │
│                                                                     │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐     │
│  │ EmailParser  │  │ PaperDownloader│  │ PaperScorer          │     │
│  │ (Gmail→refs) │  │ (PDF/HTML→text)│  │ (Gemini Flash score) │     │
│  └──────────────┘  └────────────────┘  └──────────────────────┘     │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐     │
│  │ TranscriptGenerator  │  │ FeedbackManager + FeedbackClient │     │
│  │ Gemini Pro narration │  │ (preference learning loop)       │     │
│  └──────────────────────┘  └──────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
Gmail Inbox
    │
    ├── HuggingFace daily digest email
    │       │
    │       ▼
    │   EmailParser extracts paper URLs + titles
    │       │
    │       ▼
    │   ALL marked as "deep_dive" (no scoring — small curated set)
    │       │
    │       ▼
    │   PaperDownloader fetches HuggingFace page HTML → extract text
    │
    ├── Arxiv daily digest emails (one per category: cs, stat, math, ...)
    │       │
    │       ▼
    │   EmailParser extracts URLs + titles + abstracts from email body
    │       │
    │       ▼
    │   PaperScorer (Gemini Flash) scores each paper 1-10
    │       │
    │       ├── Top N per category → "deep_dive"
    │       │       │
    │       │       ▼
    │       │   PaperDownloader fetches Arxiv PDF → pymupdf text extraction
    │       │
    │       └── Next M per category → "summary" (title + abstract only, no download)
    │           (remaining papers are discarded)
    │
    ▼
TranscriptGenerator
    │
    ├── Deep-dive papers → individual Gemini 3.1 Pro calls (Batch API, 50% savings)
    │   Each paper gets a thorough, standalone narration segment
    │
    └── Summary papers → plain text assembly (no LLM call)
        Grouped by category with TTS-friendly headings
    │
    ▼
raw_content/research_digest_{date}.txt  →  existing TTS pipeline  →  audio
    │
    ▼
Supabase edge function (paper metadata JSON for Research Review frontend)
    │
    ▼
User clicks on papers → implicit feedback → preference profile evolves
    │
    ▼
Future Arxiv scoring improves based on learned preferences
```

---

## Components

### Email Parser

**File:** [email_parser.py](email_parser.py)
**Class:** `ArxivHFEmailParser` (implements `PaperSource`)

Connects to Gmail via the Google API and fetches daily digest emails from configured senders.

**Arxiv parsing** handles two email formats:
1. **HTML format** — looks for `<h3>` tags containing arxiv IDs, then extracts `Title:` and `Abstract:` from siblings
2. **Plain-text format** — line-by-line state machine parser that tracks `arXiv:XXXX.XXXXX` headers, `Title:` fields (with multi-line continuation), and abstract blocks delimited by `\\` markers

Both strategies extract structured `PaperReference` objects with title, abstract, URL, and category (parsed from the email subject line, e.g., `[cs]`, `[stat]`).

**HuggingFace parsing** extracts `huggingface.co/papers/XXXX.XXXXX` links from the email HTML, using the link text as the title and adjacent `<p>` elements for abstracts.

**Deduplication** is handled via a `seen_urls` set across all emails for the day.

### Paper Downloader

**File:** [paper_downloader.py](paper_downloader.py)
**Class:** `PaperContentDownloader` (implements `ContentExtractor`)

Downloads full paper content for deep-dive papers only:

| Source | Method |
|--------|--------|
| **Arxiv** | Converts `/abs/` URL to `/pdf/` URL, downloads PDF, extracts text with `pymupdf` |
| **HuggingFace** | Fetches the paper page HTML, strips `<script>`, `<style>`, `<nav>`, etc., extracts clean text |

**Safety features:**
- **Rate limiting**: configurable delay between Arxiv requests (default 3 seconds) to respect their API policies
- **Size limit**: skips PDFs larger than 34 MB (both via `Content-Length` header and actual content size)
- **Text cleaning**: strips `References` / `Bibliography` sections, normalizes excessive whitespace
- **Graceful failure**: returns `None` on download/parse errors; the pipeline demotes failed papers to summary tier

### Paper Scorer

**File:** [paper_scorer.py](paper_scorer.py)
**Class:** `GeminiPaperScorer` (implements `PaperScorer`)

Scores **Arxiv papers only** (HuggingFace papers bypass scoring entirely). Uses Gemini Flash for fast, cheap relevance scoring.

**Scoring criteria** (from [prompts/scorer_system.txt](prompts/scorer_system.txt)):
- **8-10**: Directly advances AI agents, time series analysis, or optimization
- **5-7**: Tangentially related (new architectures, RL, foundation models)
- **1-4**: Unrelated to user interests

**Key behaviors:**
- Papers are scored in **batches of 50** to avoid output token truncation
- Requests **structured JSON output** via `response_mime_type="application/json"`
- Temperature set to **0.1** for consistent scoring
- Handles **LaTeX in reasoning strings** by sanitizing invalid escape sequences before JSON parsing
- **Preference profile injection**: if a cumulative profile exists from user feedback, it's appended to the system prompt to improve scoring over time
- **Fallback on failure**: if the API call fails, all papers default to `"summary"` tier (no crash)

**Tiering**: after scoring, papers are sorted by score descending. The top N become `"deep_dive"`, the rest become `"summary"`.

### Transcript Generator

**File:** [transcript_generator.py](transcript_generator.py)
**Class:** `GeminiTranscriptGenerator` (implements `TranscriptGenerator`)

Generates the final podcast transcript using Gemini 3.1 Pro:

**Deep-dive papers** — each paper gets its **own individual LLM call** with the full paper text, producing a thorough standalone narration segment. All calls are submitted as separate `InlinedRequest` entries in a single **Batch API job** (50% cost savings, 24-hour turnaround acceptable for daily digests). A realtime fallback mode is available for testing.

**Summary papers** — formatted as **plain text without any LLM call**. Papers are grouped by Arxiv category with human-readable headings (e.g., "Computer Science", "Statistics") and listed with title + abstract. This section is appended after the deep-dive transcripts.

**Batch API workflow:**
1. Create a batch job with N `InlinedRequest` entries (one per deep-dive paper)
2. Poll for completion at a configurable interval (default 60 seconds)
3. Extract generated text from each response
4. Concatenate all segments into the final transcript

### Feedback System

**File:** [feedback.py](feedback.py)
**Classes:** `PreferenceProfileManager` (implements `FeedbackStore`), `FeedbackClient`

Implements a **cumulative learning loop** that improves Arxiv scoring over time based on implicit user behavior:

**`FeedbackClient`** — queries the Supabase edge function for papers the user clicked on in the Research Review frontend over the last 30 days. Clicking a paper signals "I was interested enough to investigate" — low friction, no explicit rating needed.

**`PreferenceProfileManager`** — manages a local JSON file (`preference_profile.json`) that evolves over time:
- Stores up to **50 example papers** (most recent kept when cap exceeded)
- Uses **Gemini Flash** to extract 1-3 broad interest patterns from newly clicked papers
- Deduplicates learned interests
- Formats the profile as a natural language string for injection into the scorer system prompt

**Profile format example:**
> The user has previously shown interest in papers like: "Paper A", "Paper B", "Paper C". Patterns noticed: multi-agent coordination, temporal graph networks. Prioritize papers similar to these.

### Pipeline Orchestrator

**File:** [pipeline.py](pipeline.py)
**Class:** `ResearchPaperPipeline`

Wires all components together and executes the 10-step pipeline:

1. **Idempotency check** — skips if output file already exists for the date
2. **Load preference profile** — fetches recent click feedback, updates profile
3. **Parse emails** — extracts paper references from Gmail
4. **Split by source** — separates HuggingFace and Arxiv papers
5. **Score Arxiv papers** — AI relevance scoring with per-category selection
6. **Mark HuggingFace as deep_dive** — all HF papers get full treatment
7. **Download content** — fetches PDFs/HTML for deep-dive papers; demotes failures to summary
8. **Generate transcript** — produces narration via Gemini Pro Batch API
9. **Save transcript** — writes to `raw_content/research_digest_{date}.txt`
10. **Push metadata** — sends paper metadata JSON to Supabase for the frontend

**Per-category selection**: Arxiv papers are grouped by their email category (cs, stat, math, etc.). Within each category, the top `deep_dive_per_category` papers (default 5) get full treatment, the next `summary_per_category` (default 10) get brief mentions, and the rest are discarded. This prevents a single high-volume category from crowding out others.

---

## Data Models

**File:** [models.py](models.py)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `PaperReference` | Extracted from email — lightweight metadata | `url`, `title`, `abstract`, `source` ("arxiv" \| "huggingface"), `category` |
| `PaperContent` | After downloading — includes full text | `url`, `title`, `abstract`, `full_text`, `source` |
| `ScoredPaper` | After scoring — includes tier assignment | `paper` (PaperReference), `score`, `tier` ("deep_dive" \| "summary"), `reasoning` |

All models are Python `dataclass` objects for clean, immutable data passing between pipeline stages.

---

## Prompts

Located in the [prompts/](prompts/) directory:

### `narrator_system.txt`
System prompt for Gemini 3.1 Pro when generating deep-dive segments. Instructs the model to act as a knowledgeable AI researcher narrating for a data scientist audience. Defines a 5-part structure: introduction → methodology → results → implications → transition.

### `scorer_system.txt`
System prompt for Gemini Flash when scoring Arxiv papers. Defines the three core interest areas (AI agents, time series, optimization) and the 1-10 scoring rubric. Contains a `{preference_profile_section}` placeholder that gets replaced with learned user preferences at runtime.

---

## Configuration

All configuration lives in `config.ini` (one directory up, in `src/audiobooks/`):

```ini
[WebApp]
API_URL = https://your-project.supabase.co/functions/v1
API_KEY = your-supabase-key

[Gmail]
CREDENTIALS_FILE = credentials.json   # OAuth client from Google Cloud Console
TOKEN_FILE = token.json                # Auto-created after first auth

[Gemini]
API_KEY = your-gemini-api-key
SCORING_MODEL = gemini-3-flash-preview
GENERATION_MODEL = gemini-3.1-pro-preview

[ResearchPapers]
ARXIV_SENDERS = no-reply@arxiv.org
HUGGINGFACE_SENDERS = daily_papers_digest@notifications.huggingface.co
TOP_N_THRESHOLD = 10
DEEP_DIVE_PER_CATEGORY = 5
SUMMARY_PER_CATEGORY = 10
ARXIV_DELAY_SECONDS = 3
```

### Gmail Setup

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API
3. Create OAuth 2.0 credentials (Desktop application type)
4. Download the credentials file as `credentials.json` and place it in `src/audiobooks/`
5. On first run, a browser window will open for authentication. The resulting `token.json` is saved automatically

**Required scope:** `https://www.googleapis.com/auth/gmail.modify`

---

## Usage

Run from the `src/audiobooks/` directory with the Python virtual environment activated:

### Single Date

```bash
python -m research_papers.run_research_pipeline --date 2026-03-19
```

### Date Range

```bash
python -m research_papers.run_research_pipeline --start-date 2026-03-15 --end-date 2026-03-19
```

### Default (Yesterday)

```bash
python -m research_papers.run_research_pipeline
```

Processes yesterday's papers. Designed for daily cron job / scheduled task usage.

---

## Output

### Transcript File

Written to `src/audiobooks/raw_content/research_digest_{YYYY-MM-DD}.txt`

The transcript contains:
1. **Deep-dive segments** — one per paper, each a thorough narration covering problem, methodology, results, and implications
2. **Summary section** — grouped by Arxiv category with TTS-friendly headings, listing remaining papers with title and abstract

### Supabase Metadata

A JSON payload is POSTed to the `/research-papers` edge function containing:
```json
{
  "date": "2026-03-19",
  "papers": [
    {
      "url": "https://arxiv.org/abs/2603.12345",
      "title": "Paper Title",
      "abstract": "Paper abstract...",
      "score": 10,
      "tier": "deep_dive",
      "source": "arxiv",
      "clicked": false
    }
  ]
}
```

This feeds the Research Review frontend page where users can browse papers and implicitly provide feedback via clicks.

### Logs

Detailed logs are written to both `research_pipeline.log` and stdout, covering every pipeline stage with paper counts, scoring results, batch job status, and error details.

---

## Feedback Loop

The system learns from user behavior over time:

```
Day 1: Score papers with base interests only
         ↓
Day 1: User clicks 3 papers on Research Review page
         ↓
Day 2: FeedbackClient fetches clicked papers from Supabase
         ↓
Day 2: PreferenceProfileManager uses Gemini Flash to extract interest patterns
         ↓
Day 2: Updated preference profile injected into scorer system prompt
         ↓
Day 2: Scoring now reflects both base interests AND learned preferences
         ↓
        ... cycle continues, profile grows cumulatively ...
```

The preference profile is stored locally at `preference_profile.json` and caps at 50 example papers to prevent unbounded growth.

---

## Design Principles

- **SOLID Architecture**: abstract interfaces → concrete implementations → dependency injection → testable components
- **TDD**: all components have comprehensive test suites with mocked external APIs
- **Idempotency**: re-running for the same date is a no-op if the output file exists
- **Graceful degradation**: API failures, download errors, and malformed emails are all handled — the pipeline continues with whatever papers it can process
- **Rate limit respect**: configurable delays between Arxiv requests (default 3s)
- **Cost optimization**: Gemini Flash for cheap scoring, Batch API for 50% savings on transcript generation
- **Per-category fairness**: top-N selection happens within each Arxiv category, preventing one category from dominating the digest

---

## Testing

The test suite lives in [tests/](tests/) and covers every component with unit tests using mocked external dependencies.

```bash
# Run all tests from the research_papers directory
pytest tests/ -v

# Run tests for a specific component
pytest tests/test_email_parser.py -v
pytest tests/test_paper_downloader.py -v
pytest tests/test_paper_scorer.py -v
pytest tests/test_transcript_generator.py -v
pytest tests/test_pipeline.py -v
pytest tests/test_feedback.py -v
```

| Test File | Coverage |
|-----------|----------|
| `test_email_parser.py` | Arxiv HTML + plain-text parsing, HuggingFace parsing, category extraction, deduplication, edge cases |
| `test_paper_downloader.py` | Arxiv PDF extraction, HuggingFace page extraction, text cleaning, rate limiting, size limits, error handling |
| `test_paper_scorer.py` | Scoring logic, tiering, batch processing, preference profile injection, HuggingFace bypass, JSON parsing, error fallback |
| `test_transcript_generator.py` | Prompt construction, per-paper generation, batch mode, summary text assembly, category grouping |
| `test_pipeline.py` | Full end-to-end orchestration, per-category selection, idempotency, Supabase metadata push, error scenarios |
| `test_feedback.py` | Profile loading/writing, interest extraction, growth capping, FeedbackClient API calls |

---

## Dependencies

Core Python packages (see `requirements.txt` in parent directory):

| Package | Purpose |
|---------|---------|
| `google-genai` | Gemini API client (scoring + transcript generation) |
| `pymupdf` | PDF text extraction for Arxiv papers |
| `beautifulsoup4` | HTML parsing for emails and HuggingFace pages |
| `requests` | HTTP calls for paper downloads and Supabase API |
| `google-api-python-client` | Gmail API access |
| `google-auth-oauthlib` | Gmail OAuth authentication |
| `pytest` | Test framework |

---

## Project Structure

```
research_papers/
├── __init__.py                  # Package marker
├── interfaces.py                # Abstract base classes (PaperSource, ContentExtractor, etc.)
├── models.py                    # Data classes (PaperReference, PaperContent, ScoredPaper)
├── email_parser.py              # Gmail → paper references (Arxiv + HuggingFace)
├── paper_downloader.py          # PDF/HTML → full text extraction
├── paper_scorer.py              # Gemini Flash relevance scoring (Arxiv only)
├── transcript_generator.py      # Gemini Pro podcast narration (Batch API)
├── feedback.py                  # Preference profile management + Supabase feedback client
├── pipeline.py                  # Pipeline orchestrator (wires everything together)
├── run_research_pipeline.py     # CLI entry point (config loading, Gmail auth, arg parsing)
├── PLAN.md                      # Original implementation plan and design decisions
├── README.md                    # This file
├── prompts/
│   ├── narrator_system.txt      # System prompt for deep-dive narration
│   └── scorer_system.txt        # System prompt for relevance scoring
└── tests/
    ├── __init__.py
    ├── test_email_parser.py
    ├── test_paper_downloader.py
    ├── test_paper_scorer.py
    ├── test_transcript_generator.py
    ├── test_pipeline.py
    └── test_feedback.py
```
