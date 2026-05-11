# Code Review Report `llm-wiki` (29 commits)

**Date**: 2026-04-21
**Branch**: `llm-wiki`
**Commits reviewed**: 29
**Files reviewed**: 9 Python files (`wiki_engine/` modules); 1 shell script (light review)
**Findings**: 0 CRITICAL, 7 WARNING, 4 SUGGESTION

---

## Findings

### `src/audiobooks/research_papers/wiki_engine/classifier.py`, `ingestion.py`, `linter.py`

**WARNING** Error Handling: `except (json.JSONDecodeError, Exception)` is redundant `json.JSONDecodeError` is a subclass of `ValueError` which is a subclass of `Exception`, so the first item in the tuple is never reached independently. More importantly, catching bare `Exception` silently swallows programming errors (e.g. `AttributeError`, `TypeError`) that should surface during development.

- Current (same pattern in all three files):
```python
except (json.JSONDecodeError, Exception) as e:
    logger.warning(f"Classification failed: {e}")
    return ClassifiedSection(text=text, category="Other", title="Unclassified")
```
- Suggested:
```python
except json.JSONDecodeError as e:
    logger.warning("LLM returned invalid JSON: %s", e)
    return ClassifiedSection(text=text, category="Other", title="Unclassified")
except Exception as e:
    logger.exception("Unexpected error during classification")
    return ClassifiedSection(text=text, category="Other", title="Unclassified")
```
- Rationale: Separating the two except clauses lets you handle expected JSON parse failures with a clean warning, while still surfacing unexpected errors via `logger.exception` (which prints the full traceback). This also removes the redundant tuple.

---

### `src/audiobooks/research_papers/wiki_engine/classifier.py` and `ingestion.py`

**WARNING** Code Quality: `_load_prompt` is defined identically in both `classifier.py` and `ingestion.py`. Similarly, `_slugify` is defined separately in `ingestion.py`, `query_saver.py`, and `linter.py`. `_format_page` is duplicated between `ingestion.py` and `query_saver.py`. This violates DRY and means any fix must be applied in multiple places.

- Current (`_load_prompt` defined verbatim in both files):
```python
def _load_prompt(filename: str, fallback: str) -> str:
    """Load a prompt template from disk with a safe fallback."""
    try:
        prompt_path = PROMPTS_DIR / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed loading prompt {filename}: {e}")
    return fallback
```
- Suggested: Create `wiki_engine/utils.py` with shared helpers:
```python
# wiki_engine/utils.py
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

def load_prompt(prompts_dir: Path, filename: str, fallback: str) -> str:
    try:
        path = prompts_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        logger.warning("Failed loading prompt %s", filename)
    return fallback

def slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s]+", "_", slug)
    return slug
```
- Rationale: Centralising shared utilities means a single source of truth, easier unit testing of the helpers themselves, and no risk of the three `_slugify` implementations diverging.

---

### `src/audiobooks/research_papers/wiki_engine/search.py`

**WARNING** Code Quality: `import yaml` appears inside the `_extract_title` method body rather than at the top of the module. Python imports inside functions are valid but unconventional; they hide the dependency and incur a lookup overhead on every call.

- Current:
```python
def _extract_title(self, filepath: Path) -> str:
    try:
        content = filepath.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                data = yaml.safe_load(parts[1])
```
- Suggested: Move `import yaml` to the top of `search.py` alongside the other imports.
- Rationale: Module-level imports are PEP 8 convention and make dependencies immediately visible to readers and linters.

---

### `src/audiobooks/research_papers/wiki_engine/search.py`

**WARNING** Performance: `_qmd_available()` spawns a `subprocess.run(["qmd", "--version"])` call on every invocation of `query()`. For any loop that processes many queries (e.g. during ingestion), this adds repeated subprocess overhead.

- Current:
```python
def query(self, question: str, limit: int = 10) -> List[WikiSearchResult]:
    if not self._qmd_available():
        ...
```
- Suggested: Cache the result at class level on first call:
```python
_qmd_available_cache: Optional[bool] = None

def _qmd_available(self) -> bool:
    if WikiSearch._qmd_available_cache is None:
        try:
            result = subprocess.run(
                ["qmd", "--version"], capture_output=True, text=True, timeout=5
            )
            WikiSearch._qmd_available_cache = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            WikiSearch._qmd_available_cache = False
    return WikiSearch._qmd_available_cache
```
- Rationale: `qmd` availability does not change during a process run, so checking once and caching the boolean eliminates repeated subprocess overhead.

---

### `src/audiobooks/research_papers/wiki_engine/query_saver.py`

**WARNING** Type Safety: `sources: list = None` is an incorrect type annotation `list` does not include `None`, so static type checkers will flag this. The parameter type should accurately reflect that `None` is a valid default.

- Current:
```python
def save(self, question: str, answer: str, sources: list = None) -> Path:
```
- Suggested:
```python
from typing import List, Optional

def save(self, question: str, answer: str, sources: Optional[List[str]] = None) -> Path:
```
- Rationale: `Optional[List[str]]` accurately expresses that the caller may pass `None`, and the type is self-documenting.

---

### `src/audiobooks/research_papers/wiki_engine/git_hooks.py`

**WARNING** Error Handling: `has_changes()` silently swallows all exceptions with a bare `except Exception:` and returns `False` with no log. If git is broken or the repo path is wrong, callers will skip auto-commit silently with no indication of why.

- Current:
```python
    except Exception:
        return False
```
- Suggested:
```python
    except Exception:
        logger.warning("has_changes() failed — assuming no changes", exc_info=True)
        return False
```
- Rationale: Adding `exc_info=True` preserves the full traceback in the log so problems are diagnosable without changing the method's return contract.

---

### `src/audiobooks/research_papers/wiki_engine/classifier.py` and `ingestion.py`

**WARNING** Code Quality: `CLASSIFY_SYSTEM_PROMPT` and `EXTRACT_CONCEPTS_PROMPT` are populated by `_load_prompt(...)` calls at module import time (top-level statements). This means file I/O runs on every `import wiki_engine.classifier`, which complicates testing and violates the principle of deferring side effects.

- Current:
```python
CLASSIFY_SYSTEM_PROMPT = _load_prompt("classify_system.txt", """...""")
```
- Suggested: Lazy-load inside `__init__`:
```python
class TranscriptClassifier:
    def __init__(self, llm_client=None, model_name: str = "gemini-3.1-flash-lite-preview"):
        self.llm_client = llm_client
        self.model_name = model_name
        self._classify_prompt = _load_prompt("classify_system.txt", _CLASSIFY_FALLBACK)
```
- Rationale: Scoping the file read to object construction means the I/O happens only when the object is used, and unit tests can import the module freely without needing prompt files present.

---

### `src/audiobooks/research_papers/wiki_engine/search.py`

**SUGGESTION** Code Quality: `WikiSearchResult` manually defines `__init__` and `__repr__`. A `@dataclass` removes the boilerplate and adds `__eq__` for free (useful in assertions).

- Current:
```python
class WikiSearchResult:
    def __init__(self, title: str, path: str, score: float = 0.0, snippet: str = ""):
        self.title = title
        self.path = path
        self.score = score
        self.snippet = snippet

    def __repr__(self):
        return f"WikiSearchResult(title={self.title!r}, score={self.score:.2f})"
```
- Suggested:
```python
from dataclasses import dataclass

@dataclass
class WikiSearchResult:
    title: str
    path: str
    score: float = 0.0
    snippet: str = ""
```
- Rationale: `@dataclass` is the idiomatic Python approach for data-holding classes and cuts 10 lines to 5 with more functionality.

---

### `src/audiobooks/research_papers/wiki_engine/mcp_server.py`

**SUGGESTION** Type Safety: `TOOLS` is a mutable class-level `list` with no type annotation. Any code that accidentally calls `WikiMcpServer.TOOLS.append(...)` would silently corrupt the tool registry. Annotating it with `ClassVar` signals its intent.

- Current:
```python
class WikiMcpServer:
    TOOLS = [
        {
            "name": "wiki_search",
            ...
```
- Suggested:
```python
from typing import ClassVar, List

class WikiMcpServer:
    TOOLS: ClassVar[List[dict]] = [
        ...
```
- Rationale: `ClassVar` tells type checkers this attribute belongs to the class, not instances, and prevents accidental instance-level shadowing.

---

### `src/audiobooks/research_papers/wiki_engine/linter.py`

**SUGGESTION** Readability: The technical terms regex alternation in `find_implicit_concepts` is embedded inline and will become difficult to maintain as the vocabulary grows. Pre-compiling it as a module-level constant also avoids recompiling it on every file scan.

- Current:
```python
tech_terms = re.findall(
    r"\b(?:transformer|attention|diffusion|reinforcement learning|"
    r"state space|mixture of experts|fine-tuning|"
    r"knowledge distillation|quantization|pruning)\b",
    content,
    re.IGNORECASE,
)
```
- Suggested:
```python
_TECH_TERM_PATTERN = re.compile(
    r"\b(?:transformer|attention|diffusion|reinforcement learning|"
    r"state space|mixture of experts|fine-tuning|"
    r"knowledge distillation|quantization|pruning)\b",
    re.IGNORECASE,
)

# inside find_implicit_concepts:
tech_terms = _TECH_TERM_PATTERN.findall(content)
```
- Rationale: Pre-compiling the regex to a module-level constant avoids recompiling on every file during a lint pass and makes the vocabulary list easy to find and extend.

---

### `src/audiobooks/research_papers/wiki_engine/index_builder.py`

**SUGGESTION** Robustness: `pages_by_type.setdefault(page_type, [])` will silently accept any unexpected `type` value from YAML (e.g. a typo like `"concpet"`), and those pages will be invisible in the generated index. A log warning would make this detectable.

- Current:
```python
pages_by_type.setdefault(page_type, []).append({...})
```
- Suggested:
```python
if page_type not in pages_by_type:
    logger.warning("Skipping page %s with unknown type %r", md_file.name, page_type)
else:
    pages_by_type[page_type].append({...})
```
- Rationale: A warning log surfaces YAML typos immediately rather than silently producing an incomplete index.

---

## Files With No Findings

- `wiki_engine/models.py` — Clean dataclass definitions with appropriate `__post_init__` guards and a well-formed `to_dict()`. Nothing to change.
- `wiki_engine/__init__.py` — Minimal package marker, appropriate.
- `scripts/install_qmd.sh` — Safe `set -eu`, idempotency check before install, correct `npm install -g` invocation.

---

## Top 3 Most Impactful Improvements

1. **Consolidate duplicated helpers into `wiki_engine/utils.py`** — `_load_prompt`, `_slugify`, and `_format_page` are scattered across 3–4 files. A single shared module eliminates drift risk and is the highest-leverage change in the batch.
2. **Fix the redundant `except (json.JSONDecodeError, Exception)` pattern** — Appears in at least three files. Splitting into two separate `except` clauses with `logger.exception` on the unexpected branch means real bugs will surface in logs instead of being silently swallowed.
3. **Cache `_qmd_available()`** — During an ingestion run processing many transcript sections, each `WikiSearch.query()` call currently forks a new `qmd --version` subprocess. A single cached boolean eliminates this overhead with a trivial change.
