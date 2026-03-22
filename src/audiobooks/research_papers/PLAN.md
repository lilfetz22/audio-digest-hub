# Research Paper Podcast Pipeline — Implementation Plan

## TL;DR

Add a preprocessing pipeline that:

1. Fetches **HuggingFace** and **Arxiv** research paper emails via the existing Gmail API
2. **HuggingFace (~10 papers/day)**: All papers get full deep-dive treatment — download content, send to **Gemini 3.1 Pro** for detailed narration (no scoring/filtering needed, small enough to cover all)
3. **Arxiv (50+ papers/day)**: Uses **Gemini Flash** to AI-score papers by relevance to user interests (AI agents, time series, optimization). Top ~10 get full PDF download + deep narration; the rest use title+abstract already in the email for a brief summary
4. Generates a tiered single-narrator podcast transcript via **Gemini 3.1 Pro Batch API** (50% cost savings)
5. Outputs transcript to `raw_content/` where the existing TTS pipeline picks it up automatically
6. Pushes paper metadata to a Supabase edge function for a new **Research Review** frontend page with implicit click-tracking feedback that cumulatively refines the Arxiv scorer's preference profile

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Gmail (daily emails)                           │
│                                                                        │
│   HuggingFace (~10 papers)              Arxiv (50+ papers)            │
│         │                                      │                       │
│         ▼                                      ▼                       │
│   EmailParser                            EmailParser                   │
│   (extract URLs)                    (extract URLs + titles             │
│         │                            + abstracts from email)           │
│         │                                      │                       │
│         │                                      ▼                       │
│         │                              PaperScorer                     │
│         │                        (Gemini Flash — realtime)             │
│         │                        (uses preference profile)             │
│         │                                      │                       │
│         │                          ┌───────────┴──────────┐            │
│         │                          │                      │            │
│         ▼                          ▼                      ▼            │
│   PaperDownloader           PaperDownloader         (skip download)    │
│   (ALL HF papers)          (top ~10 Arxiv only)    (use email abstract)│
│         │                          │                      │            │
│         └──────────┬───────────────┘                      │            │
│                    │                                      │            │
│                    ▼                                      │            │
│         ┌─────────────────────┐                           │            │
│         │  Deep-dive papers   │     Summary papers ◄──────┘            │
│         │  (HF + top Arxiv)   │     (remaining Arxiv)                  │
│         └─────────┬───────────┘              │                         │
│                   └──────────┬───────────────┘                         │
│                              ▼                                         │
│                   TranscriptGenerator                                  │
│              (Gemini 3.1 Pro — Batch API)                             │
│                              │                                         │
│                    ┌─────────┴─────────┐                               │
│                    ▼                   ▼                                │
│     raw_content/research_         Supabase Edge Function               │
│     digest_{date}.txt             (paper metadata JSON)                │
│            │                           │                               │
│            ▼                           ▼                                │
│   [existing TTS pipeline]    Frontend: Research Review page            │
│                              (summary papers + click tracking)         │
│                                        │                               │
│                                        ▼                                │
│                              Clicked papers → cumulative               │
│                              preference profile → future               │
│                              Arxiv scoring improves                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### SOLID Principles

- **Single Responsibility**: Each class handles one concern (parsing, downloading, scoring, generation, feedback)
- **Open/Closed**: Abstract base classes for paper sources, extractors, scorers — extensible for new sources
- **Dependency Inversion**: All components depend on abstractions; dependencies injected via constructor
- **TDD**: Tests written first for every component with mocked external APIs

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **HuggingFace treatment** | All ~10 papers → full deep-dive (no scoring) | Small volume, all curated/interesting |
| **Arxiv treatment** | Gemini Flash scores → top ~10 deep-dive, rest summary | 50+ papers needs filtering; Flash is cheap ($0.50/M) |
| **Transcript model** | `gemini-3.1-pro-preview` via Batch API | Best quality, 50% cost savings, 24hr turnaround acceptable |
| **Scoring model** | `gemini-3-flash-preview` (realtime) | Fast, cheap, good enough for relevance scoring |
| **Narrative style** | Single narrator, tiered depth | Deep coverage on top papers, brief mention of rest |
| **Output format** | Daily digest (one combined audio) | Matches existing newsletter digest pattern |
| **Paper access (Arxiv summary)** | Title + abstract from email body (no PDF) | Arxiv daily digests include title+abstract inline |
| **Paper access (deep-dive)** | Pre-download PDFs, extract via pymupdf | Full content needed for detailed narration |
| **API key storage** | Existing `config.ini` | Matches current project pattern |
| **Feedback mechanism** | Implicit click tracking on Research Review page | Low friction; clicking = "I was interested enough to investigate" |
| **Feedback learning** | Cumulative preference profile | Evolves scorer system prompt over time with learned patterns |
| **Paper metadata storage** | Supabase Storage via edge function (no DB migration) | Simpler than new DB table; JSON files in storage bucket |

---

## Implementation Phases

### Phase 1: Project Setup & Abstractions

**Goal**: Establish the module structure, interfaces, and data models.

**Tasks**:

1. **Create module structure** — `src/audiobooks/research_papers/` package with `__init__.py`

2. **Define abstract interfaces** in `interfaces.py`:
   - `PaperSource` (ABC) — contract for extracting papers from any source
   - `ContentExtractor` (ABC) — contract for extracting text from a URL/file
   - `PaperScorer` (ABC) — contract for scoring/ranking papers
   - `TranscriptGenerator` (ABC) — contract for generating narrative
   - `FeedbackStore` (ABC) — contract for reading/writing preference feedback

3. **Define data models** in `models.py`:
   - `PaperReference(url, title, abstract, source)` — extracted from emails
   - `PaperContent(url, title, abstract, full_text, source)` — after PDF/HTML download
   - `ScoredPaper(paper, score, tier, reasoning)` — tier = `"deep_dive"` | `"summary"`

4. **Update `config.ini`** — Add sections:
   ```ini
   [Gemini]
   API_KEY = your-gemini-api-key
   SCORING_MODEL = gemini-3-flash-preview
   GENERATION_MODEL = gemini-3.1-pro-preview

   [ResearchPapers]
   ARXIV_SENDERS = no-reply@arxiv.org
   HUGGINGFACE_SENDERS = no-reply@huggingface.co
   TOP_N_THRESHOLD = 10
   ARXIV_DELAY_SECONDS = 3
   ```

5. **Update `requirements.txt`** — Add:
   ```
   google-genai
   pymupdf
   beautifulsoup4
   ```

---

### Phase 2: Email Parsing & URL Extraction *(parallel with Phase 3)*

**Goal**: Extract paper URLs, titles, and abstracts from Gmail.

**Tests first** — `test_email_parser.py`:
- Extract `arxiv.org/abs/XXXX` URLs from Arxiv daily digest email HTML
- Extract `huggingface.co/papers/XXXX` URLs from HuggingFace email
- Extract **title + abstract** directly from Arxiv email body (these daily digests include them inline)
- Deduplicate URLs across multiple emails
- Handle malformed emails (no links, broken HTML)

**Implementation** — `email_parser.py`:
- `ArxivHFEmailParser` (implements `PaperSource`)
- Reuses existing `authenticate_gmail()` from `generate_audiobook.py`
- Queries Gmail for HF and Arxiv sender emails by date
- **Arxiv**: Parses email HTML to extract title + abstract + URL for each paper (returns `PaperReference` with abstract pre-populated)
- **HuggingFace**: Extracts paper URLs (titles can be parsed from the link text or page later)
- Deduplicates, returns list of `PaperReference` dataclasses tagged with `source="arxiv"` or `source="huggingface"`

---

### Phase 3: Paper Content Download & Extraction *(parallel with Phase 2)*

**Goal**: Download full paper content for deep-dive papers only.

**Tests first** — `test_paper_downloader.py`:
- Download arxiv PDF and extract text via pymupdf
- Download HuggingFace paper page and extract text via BeautifulSoup
- Handle download failures (404, timeout, too large)
- Text cleaning (remove references section, excessive whitespace)
- Verify downloader is **only called for deep-dive tier papers** (all HF + top Arxiv)

**Implementation** — `paper_downloader.py`:
- `PaperContentDownloader` (implements `ContentExtractor`)
- `download_arxiv(url)` → fetch PDF from `arxiv.org/pdf/{id}.pdf`, extract text via pymupdf
- `download_huggingface(url)` → fetch HTML from `huggingface.co/papers/{id}`, parse with BeautifulSoup
- Polite **3-second delays** between Arxiv requests (respect rate limits)
- Timeout and size limits (skip papers > 34MB)
- Returns `PaperContent` dataclass with `full_text` populated

---

### Phase 4: AI-Powered Scoring & Filtering *(depends on Phase 1)*

**Goal**: Score Arxiv papers only. HuggingFace papers skip this entirely.

**Tests first** — `test_paper_scorer.py`:
- System prompt construction with base interests + cumulative preference profile
- Structured output parsing (scores + reasoning per paper)
- Tiering logic (top N = `deep_dive`, rest = `summary`)
- API error handling and retries
- Preference profile loading and prompt injection
- Verify HuggingFace papers are **never scored** (all auto-assigned `deep_dive`)

**Implementation** — `paper_scorer.py`:
- `GeminiPaperScorer` (implements `PaperScorer`)
- Uses `gemini-3-flash-preview` (realtime, $0.50/M input tokens)
- **Only scores Arxiv papers** — HuggingFace papers bypass scoring entirely, all marked as `deep_dive`
- Sends all Arxiv titles + abstracts in one request
- Uses Pydantic structured output for reliable parsing of scores (1-10) and reasoning
- Configurable `top_n_threshold` (default: 10) — top N Arxiv papers become `deep_dive`, rest become `summary`
- Returns papers sorted by score, split into tiers

**Scorer system prompt** (stored in `prompts/scorer_system.txt`):
```
You are an AI research paper relevance scorer. Your job is to evaluate research
papers for a data scientist who specializes in:

1. AI agents and agentic systems — tool use, planning, multi-agent collaboration,
   autonomous systems, function calling, agentic workflows
2. Time series analysis — forecasting, anomaly detection, temporal modeling,
   sequence prediction, change point detection
3. Optimization — mathematical optimization, hyperparameter tuning, neural
   architecture search, combinatorial optimization, constrained optimization

Score each paper from 1 to 10 based on relevance to these interests:
- 8-10: Directly advances one of the three core areas above
- 5-7: Tangentially related or introduces methods useful to these areas
        (e.g., new transformer architectures, reinforcement learning, foundation models)
- 1-4: Unrelated to the user's interests

For each paper, provide:
- score: integer 1-10
- reasoning: one sentence explaining the score

{preference_profile_section}
```

---

### Phase 5: Cumulative Feedback System *(parallel with Phase 4)*

**Goal**: Build a learning loop where user clicks on the Research Review page evolve future scoring.

**Tests first** — `test_feedback.py`:
- Load existing preference profile from JSON
- Update profile with new clicked papers
- Format profile for prompt injection
- Cumulative growth over time (append, don't replace)
- Cold start with empty profile
- Cap at 50 most recent example papers

**Implementation** — `feedback.py`:

**`PreferenceProfileManager`** (implements `FeedbackStore`):
- Local file: `preference_profile.json`
- Structure:
  ```json
  {
    "interests_learned": [
      "retrieval-augmented generation",
      "graph neural networks for optimization"
    ],
    "example_papers": [
      {"title": "...", "abstract": "...", "date": "2026-03-14"}
    ],
    "updated_at": "2026-03-14T10:00:00Z"
  }
  ```
- `load_profile()` → returns formatted string for scorer prompt injection:
  *"The user has previously shown interest in papers like: [examples]. Patterns noticed: [learned interests]. Prioritize papers similar to these."*
- `update_profile(clicked_papers)` → adds clicked papers to `example_papers`. Uses Gemini Flash to extract interest patterns from clicked titles/abstracts (e.g., *"user seems interested in retrieval-augmented generation"*). Appends new patterns to `interests_learned`.
- Caps `example_papers` at 50 most recent entries to keep prompt size reasonable

**`FeedbackClient`**:
- Calls the Supabase edge function (`GET /research-papers/feedback?days=30`) to fetch recent click data
- Pipes clicked papers into `PreferenceProfileManager.update_profile()`
- Called at the start of each pipeline run, before scoring

---

### Phase 6: Transcript Generation *(depends on Phases 2-4)*

**Goal**: Generate a single-narrator podcast transcript from tiered paper content.

**Tests first** — `test_transcript_generator.py`:
- Prompt construction with tiered papers (full text for deep-dive, title+abstract for summary)
- Batch API job creation with correct model and config
- Polling loop and result retrieval
- Output formatting (clean transcript text)
- Error handling (batch job failure, timeout, expired)

**Implementation** — `transcript_generator.py`:
- `GeminiTranscriptGenerator` (implements `TranscriptGenerator`)
- Uses `gemini-3.1-pro-preview` via **Batch API** (50% cost)
- Content construction:
  - **Deep-dive papers** (all HF + top Arxiv): full extracted text → detailed narration covering methodology, key findings, implications, why it matters
  - **Summary papers** (remaining Arxiv): title + abstract only → brief mention with one-sentence key takeaway
- Creates batch job with inline request
- Polls every 60 seconds for completion
- Returns clean transcript string

**Narrator system prompt** (stored in `prompts/narrator_system.txt`):
```
You are a knowledgeable AI researcher narrating a daily research digest podcast.
Your audience is a data scientist who works with AI agents, time series analysis,
and optimization.

Speak in a clear, engaging, conversational tone — as if explaining to a smart
colleague over coffee. You are a single narrator (not a dialogue).

Structure the digest as follows:
1. Brief intro: "Welcome to today's AI research digest for [date]."
2. Deep-dive section: For each featured paper, explain:
   - What problem it addresses and why it matters
   - The key methodology or approach
   - Main results and their significance
   - Practical implications or takeaways
3. Quick hits section: "And here are some other notable papers from today..."
   For each, give the title and a one-sentence summary of the key contribution.
4. Brief outro.

Keep the language accessible. Avoid excessive jargon. When using technical terms,
briefly explain them. Make transitions smooth between papers.
```

---

### Phase 7: Pipeline Orchestrator *(depends on Phases 5-6)*

**Goal**: Wire everything together into a single `run(date)` command.

**Tests first** — `test_pipeline.py`:
- Full flow with all mocked dependencies
- Output file naming: `research_digest_{date}.txt`
- File written to `raw_content/` directory
- Supabase push of paper metadata (both tiers)
- Idempotency (skip if output file already exists)
- Error handling (no papers found, scoring fails, generation fails)

**Implementation** — `pipeline.py`:

`ResearchPaperPipeline`:
- Constructor receives all dependencies (dependency injection)
- `run(date)` method orchestrates:
  1. **Load preference profile** — fetch click feedback from previous days, update profile
  2. **Parse emails** → list of `PaperReference` (with titles+abstracts from email body)
  3. **Split by source** — separate HuggingFace and Arxiv papers
  4. **Score Arxiv papers** using Gemini Flash (with preference profile) → tiered list
  5. **Mark all HuggingFace papers as `deep_dive`** (no scoring)
  6. **Download full content** for all `deep_dive` papers only (HF + top Arxiv)
  7. **Generate transcript** via Gemini 3.1 Pro Batch → podcast text
  8. **Save transcript** to `src/audiobooks/raw_content/research_digest_{date}.txt`
  9. **Push paper metadata** to Supabase edge function (for Research Review frontend)
- Logging throughout (same pattern as existing `audiobook_generator.log`)

**CLI entry point** — `run_research_pipeline.py`:
- Parses `--date`, `--start-date`, `--end-date` arguments (same pattern as existing pipeline)
- Wires up concrete implementations with config from `config.ini`
- Can run standalone or be chained from `run_audiobook_generator.bat`

**Update `run_audiobook_generator.bat`**:
- Add research pipeline step **before** existing audiobook generation:
  ```batch
  py research_papers/run_research_pipeline.py
  py generate_audiobook.py
  ```

---

### Phase 8: Supabase Edge Function *(parallel with Phase 7)*

**Goal**: Serve paper metadata to the frontend and receive click feedback.

**Create `supabase/functions/research-papers/index.ts`** (follows existing auth pattern):

| Method | Path | Description |
|--------|------|-------------|
| **POST** | `/research-papers` | Pipeline pushes daily paper list JSON → stored in Supabase Storage: `research-papers/{user_id}/{date}.json` |
| **GET** | `/research-papers?date=YYYY-MM-DD` | Frontend fetches papers for a given day |
| **PATCH** | `/research-papers` | Frontend sends click event `{date, paper_url}` → sets `clicked: true` in stored JSON |
| **GET** | `/research-papers/feedback?days=30` | Pipeline fetches last 30 days of clicked papers for preference profile building |

**Paper JSON structure** (stored per day):
```json
{
  "date": "2026-03-14",
  "papers": [
    {
      "url": "https://arxiv.org/abs/2603.12345",
      "title": "Agent-Based Optimization for Time Series Forecasting",
      "abstract": "We propose a novel agent-based approach...",
      "score": 9.2,
      "tier": "deep_dive",
      "source": "arxiv",
      "clicked": false
    },
    {
      "url": "https://arxiv.org/abs/2603.12346",
      "title": "Some Other Paper",
      "abstract": "This paper explores...",
      "score": 3.1,
      "tier": "summary",
      "source": "arxiv",
      "clicked": false
    }
  ]
}
```

**Auth**: Same API key SHA-256 hashing pattern as existing edge functions.

**Update `supabase/config.toml`**:
```toml
[functions.research-papers]
verify_jwt = false
```

---

### Phase 9: Frontend Research Review Page *(parallel with Phase 7)*

**Goal**: Give the user a way to browse summary-tier papers and provide implicit feedback.

**Create `src/pages/ResearchReview.tsx`**:
- Fetches today's papers from Supabase edge function (GET)
- Displays **summary-tier papers** as a list:
  - Title (clickable link → opens arxiv in new tab)
  - Abstract snippet (first 2-3 sentences)
  - Relevance score badge
  - Source indicator (Arxiv/HF)
- **Click tracking**: clicking a paper link:
  1. Opens the URL in a new tab
  2. Fires a PATCH request to the edge function marking `clicked: true`
  3. Visual indicator updates (checkmark/dimmed state)
- **Date picker** to browse previous days' papers
- Empty state: *"No research papers processed for today"*
- Uses existing card/layout components (same style as Dashboard)

**Update `src/App.tsx`**:
- Add `/research-review` route wrapped in `ProtectedRoute`

**Update `src/components/Layout.tsx`**:
- Add "Research Review" navigation item in sidebar (with a beaker/flask icon or similar)

---

## File Inventory

### Existing Files to Modify

| File | Change |
|------|--------|
| `src/audiobooks/config.ini` | Add `[Gemini]` and `[ResearchPapers]` sections |
| `src/audiobooks/generate_audiobook.py` | Reuse/import `authenticate_gmail()` pattern |
| `src/audiobooks/requirements.txt` | Add `google-genai`, `pymupdf`, `beautifulsoup4` |
| `src/audiobooks/run_audiobook_generator.bat` | Chain research pipeline before existing flow |
| `src/App.tsx` | Add `/research-review` protected route |
| `src/components/Layout.tsx` | Add "Research Review" nav link |
| `supabase/config.toml` | Register `research-papers` edge function |

### New Files to Create

**Python pipeline** (`src/audiobooks/research_papers/`):

| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `interfaces.py` | Abstract base classes (PaperSource, ContentExtractor, PaperScorer, TranscriptGenerator, FeedbackStore) |
| `models.py` | Dataclasses (PaperReference, PaperContent, ScoredPaper) |
| `email_parser.py` | ArxivHFEmailParser — Gmail fetching + URL/title/abstract extraction |
| `paper_downloader.py` | PaperContentDownloader — PDF/HTML download + text extraction |
| `paper_scorer.py` | GeminiPaperScorer — Arxiv-only scoring via Gemini Flash |
| `transcript_generator.py` | GeminiTranscriptGenerator — Batch API transcript generation |
| `feedback.py` | PreferenceProfileManager + FeedbackClient |
| `pipeline.py` | ResearchPaperPipeline — orchestrator |
| `run_research_pipeline.py` | CLI entry point |
| `prompts/scorer_system.txt` | Scorer system prompt template |
| `prompts/narrator_system.txt` | Narrator system prompt template |
| `preference_profile.json` | Cumulative preference profile (auto-created at runtime) |

**Tests** (`src/audiobooks/research_papers/tests/`):

| File | Covers |
|------|--------|
| `__init__.py` | Package init |
| `test_email_parser.py` | Email parsing, URL extraction, title+abstract extraction |
| `test_paper_downloader.py` | PDF/HTML download, text extraction, rate limiting |
| `test_paper_scorer.py` | Scoring, tiering, preference profile injection |
| `test_transcript_generator.py` | Batch API interaction, prompt construction |
| `test_feedback.py` | Profile loading, updating, formatting, growth capping |
| `test_pipeline.py` | Full orchestration flow, idempotency, error paths |

**Supabase**:

| File | Purpose |
|------|---------|
| `supabase/functions/research-papers/index.ts` | Edge function for paper metadata CRUD + click tracking |

**Frontend**:

| File | Purpose |
|------|---------|
| `src/pages/ResearchReview.tsx` | Research Review page with click-tracking feedback |

---

## Verification Checklist

1. [ ] `pytest src/audiobooks/research_papers/tests/` — all unit tests pass (mocked APIs)
2. [ ] **Email parsing**: Process a real Arxiv daily digest email → verify title+abstract+URL extracted for all papers
3. [ ] **Email parsing**: Process a real HuggingFace email → verify all ~10 paper URLs extracted
4. [ ] **Scorer**: Score 5 known papers (mix of relevant/irrelevant) → verify AI agents/time series papers rank highest
5. [ ] **Scorer**: Verify HuggingFace papers skip scoring entirely
6. [ ] **PDF download**: Download 1 known arxiv PDF → verify clean text extraction
7. [ ] **Batch API**: Submit 1-paper transcript generation → verify response format and quality
8. [ ] **End-to-end**: Research pipeline → `.txt` in `raw_content/` → existing `generate_audiobook.py` picks it up
9. [ ] **Edge function**: Deploy → test POST/GET/PATCH with curl
10. [ ] **Frontend**: Navigate to `/research-review` → verify paper list renders
11. [ ] **Click tracking**: Click a paper → verify PATCH fires → verify `clicked: true` in stored JSON
12. [ ] **Feedback loop**: Click papers day 1 → run pipeline day 2 → verify preference profile updated → verify scored papers reflect new preferences
13. [ ] **Cost check**: Monitor Gemini API dashboard after first full run

---

## Cost Estimate (daily, 50+ Arxiv + ~10 HuggingFace)

| Component | Model | API Mode | Estimated Daily Cost |
|-----------|-------|----------|---------------------|
| Arxiv scoring (50 abstracts) | `gemini-3-flash-preview` | Realtime | ~$0.01 |
| Transcript generation (~60 papers) | `gemini-3.1-pro-preview` | Batch (50% off) | ~$0.15–0.30 |
| Preference profile update | `gemini-3-flash-preview` | Realtime | ~$0.005 |
| **Total** | | | **~$0.20–0.30/day** |

---

## Scope Boundaries

**IN scope**:
- Email parsing (Arxiv + HuggingFace)
- AI-powered scoring (Arxiv only)
- PDF download (deep-dive papers only — all HF + top Arxiv)
- Transcript generation (Batch API)
- `raw_content/` output for existing TTS pipeline
- Supabase edge function (paper metadata + click tracking)
- Research Review frontend page
- Cumulative preference feedback loop

**OUT of scope**:
- Changes to existing TTS pipeline or Colab workflow
- Changes to existing Supabase DB tables (no migrations)
- Changes to Dashboard or Player pages
- Real-time/streaming transcript generation
- Mobile app or push notifications
