# Code Review Report — `llm-wiki` (5 commits)

**Date**: 2026-05-11
**Branch**: `llm-wiki`
**Commits reviewed**: 5
**Files reviewed**: 5
**Findings**: 0 CRITICAL, 2 WARNING, 3 SUGGESTION

---

## Findings

### src/audiobooks/research_papers/wiki_engine/ingestion.py

**WARNING** Error handling / robustness: `cs.paper_urls` is assumed to always be a list.
- Current:
```python
if python_urls:
    merged = list(dict.fromkeys(python_urls + cs.paper_urls))
    cs.paper_urls = merged
```
- Suggested:
```python
existing_urls = cs.paper_urls or []
merged = list(dict.fromkeys(python_urls + existing_urls))
cs.paper_urls = merged
```
- Rationale: if `ClassifiedSection` is ever instantiated with `paper_urls=None` or deserialized from a source that omits the field, the current merge would raise a `TypeError`.

**SUGGESTION** Code organization: extract the URL merge logic into a helper method.
- Current:
```python
for cs in classified:
    python_urls = extract_source_urls_from_section(cs.text)
    if python_urls:
        merged = list(dict.fromkeys(python_urls + cs.paper_urls))
        cs.paper_urls = merged
```
- Suggested:
```python
for cs in classified:
    cs.paper_urls = self._merge_source_urls(cs.paper_urls, extract_source_urls_from_section(cs.text))
```
- Rationale: encapsulating the merge behavior improves readability and makes the ingestion flow easier to test.

---

### src/audiobooks/research_papers/transcript_generator.py

**SUGGESTION** Robustness: `zip(deep_dive_papers, deep_dive_transcripts)` can silently drop entries if the lists differ in length.
- Current:
```python
for paper, transcript in zip(deep_dive_papers, deep_dive_transcripts):
    marker = f"<!-- WIKI_SOURCE_URL: {paper.url} -->"
    annotated_parts.append(f"{marker}\n{transcript.strip()}")
```
- Suggested:
```python
from itertools import zip_longest

for paper, transcript in zip_longest(deep_dive_papers, deep_dive_transcripts, fillvalue=None):
    if paper is None or transcript is None:
        raise ValueError("Expected equal counts of deep dive papers and transcripts")
    marker = f"<!-- WIKI_SOURCE_URL: {paper.url} -->"
    annotated_parts.append(f"{marker}\n{transcript.strip()}")
```
- Rationale: a mismatch in generated papers and transcripts should fail loudly rather than dropping data silently.

---

### src/audiobooks/research_papers/wiki_engine/classifier.py

**SUGGESTION** Minor readability improvement in `extract_source_urls_from_section`.
- Current:
```python
seen: dict[str, None] = {}
for url in _WIKI_SOURCE_URL_RE.findall(text):
    seen[url] = None
return list(seen.keys())
```
- Suggested:
```python
return list(dict.fromkeys(_WIKI_SOURCE_URL_RE.findall(text)))
```
- Rationale: the current implementation is correct, but the shorter form is still explicit and removes a small amount of boilerplate.

---

### src/audiobooks/research_papers/tests/test_wiki_ingestion.py

**SUGGESTION** Test resilience: make the YAML frontmatter extraction assertion safer.
- Current:
```python
for f in concept_files:
    content = f.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    meta = yaml.safe_load(parts[1])
```
- Suggested:
```python
for f in concept_files:
    content = f.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    assert len(parts) > 1, f"Missing frontmatter in {f}"
    meta = yaml.safe_load(parts[1])
```
- Rationale: the added assertion makes the test fail with a clearer message if the concept file format changes.

---

### src/audiobooks/research_papers/tests/test_wiki_classifier.py

**SUGGESTION** Positive note: the new tests provide good coverage for the URL marker extraction behavior.
- Current: new coverage includes single URL, multiple markers, duplicate markers, malformed markers, and empty sections.
- Rationale: this test suite gives strong confidence that `extract_source_urls_from_section` handles the expected marker formats.

---

## Files With No Findings

- `src/audiobooks/research_papers/tests/test_wiki_classifier.py` — tests are well-scoped and cover the new extraction functionality.

---

## Top 3 Most Impactful Improvements

1. Fail loudly when `deep_dive_papers` and `deep_dive_transcripts` counts differ in `transcript_generator.py`.
2. Guard against `None` in `cs.paper_urls` before merging extracted source URLs in `ingestion.py`.
3. Extract the URL merge logic into a helper method to improve readability and testability.
