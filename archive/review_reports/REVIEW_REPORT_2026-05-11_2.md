# Code Review Report — `llm-wiki` (2 commits)

**Date**: 2026-05-11
**Branch**: `llm-wiki`
**Commits reviewed**: 2
**Files reviewed**: 2
**Findings**: 0 CRITICAL, 2 WARNING, 2 SUGGESTION

---

## Findings

### src/audiobooks/research_papers/tests/conftest.py

**WARNING** Test correctness: the `sentence_transformers` stub registers a `MagicMock` for `SentenceTransformer`, so any test that fails to pre-assign `scorer._model` will silently receive a `MagicMock` model rather than the expected `ImportError` fallback or a real model error.
- Current:
```python
if "sentence_transformers" not in sys.modules:
    _st_util_stub = MagicMock(name="sentence_transformers.util")
    _st_stub = MagicMock(name="sentence_transformers")
    _st_stub.util = _st_util_stub
    sys.modules["sentence_transformers"] = _st_stub
    sys.modules["sentence_transformers.util"] = _st_util_stub
```
- Suggested:
```python
if "sentence_transformers" not in sys.modules:
    _st_util_stub = MagicMock(name="sentence_transformers.util")
    _st_stub = MagicMock(name="sentence_transformers")
    _st_stub.util = _st_util_stub
    # SentenceTransformer is loaded lazily in _get_model(); stub it explicitly
    # so any test that doesn't pre-set scorer._model gets a clearly unusable
    # object rather than a silently functional MagicMock.
    _st_stub.SentenceTransformer = MagicMock(
        name="SentenceTransformer",
        side_effect=ImportError("sentence-transformers not installed (stub)"),
    )
    sys.modules["sentence_transformers"] = _st_stub
    sys.modules["sentence_transformers.util"] = _st_util_stub
```
- Rationale: making `SentenceTransformer(...)` raise `ImportError` in the stub ensures that the production `_get_model()` code path immediately triggers the existing `score()` fallback (score=5.0) when a test forgets to set `scorer._model`. Without this, `_get_model()` would silently return a `MagicMock` whose `.encode()` returns another `MagicMock`, causing opaque failures downstream.

**WARNING** Code organization: module-level stub registration in conftest can be surprising to future contributors because conftest bodies normally only contain fixtures and hooks. The intent is also harder to discover.
- Current:
```python
# Module-level statements in conftest.py that mutate sys.modules
if "sentence_transformers" not in sys.modules:
    ...
    sys.modules["sentence_transformers"] = _st_stub
```
- Suggested:
```python
def pytest_configure(config):
    """Register stubs for optional heavy dependencies before collection begins."""
    if "sentence_transformers" not in sys.modules:
        ...
        sys.modules["sentence_transformers"] = _st_stub

    if "pymupdf" not in sys.modules:
        sys.modules["pymupdf"] = MagicMock(name="pymupdf")
```
- Rationale: `pytest_configure` is the canonical pytest hook for pre-collection setup. It runs before any test module is imported (same timing as module-level code) but makes the intent explicit and keeps the conftest body consistent with pytest conventions.

---

### src/audiobooks/research_papers/tests/test_paper_scorer.py

**SUGGESTION** Test robustness: the `_mock_embeddings` list-of-lists is compatible today because `cos_sim` is fully mocked, but the helper's docstring says "the production code only indexes/slices this value" — which is true as long as `_compute_scores` never calls any method on the embedding vectors themselves (e.g. `.to(device)`). Adding a `MagicMock` wrapper to the inner vectors would make that assumption explicit and catch future regressions.
- Current:
```python
return [[0.0] * 384 for _ in range(n_papers + 1)]
```
- Suggested:
```python
# A MagicMock supports any attribute/method call, so if the production code
# ever calls e.g. tensor methods the test will still run (and fail at the
# assertion, not silently pass with wrong data).
stub_embedding = MagicMock(name="embedding_vector")
return [stub_embedding] * (n_papers + 1)
```
- Rationale: using `MagicMock` for the embedding vectors makes it explicit that tests do not depend on any particular vector value or interface, and avoids the current implicit assumption that only indexing/slicing is performed.

**SUGGESTION** Readability: `mock_cos_sim.side_effect` uses a bare list of floats as a side effect. This works because `unittest.mock` iterates the list on each call, but it is not immediately obvious to a reader that `side_effect=[0.9, 0.5, 0.2]` means "return 0.9 on the first call, 0.5 on the second, ..." since `side_effect` can also accept a callable.
- Current:
```python
mock_cos_sim.side_effect = [0.9, 0.5, 0.2]
```
- Suggested:
```python
# side_effect iterates the list: first call → 0.9, second → 0.5, third → 0.2
mock_cos_sim.side_effect = [0.9, 0.5, 0.2]
```
- Rationale: a one-line comment clarifying iteration behaviour removes ambiguity for readers unfamiliar with mock's `side_effect` list semantics. Alternatively, use `return_value` with distinct `scorer._model.encode.return_value` shapes — but a comment is the lightest-weight fix.

---

## Files With No Findings

- `src/audiobooks/research_papers/tests/conftest.py` (stub registration logic) — the guard `if "sentence_transformers" not in sys.modules` correctly preserves real library behaviour when the package is installed.
- `src/audiobooks/research_papers/tests/test_paper_scorer.py` (torch removal) — removing `torch` dependency from test helpers is the right approach; all seven previously failing tests now pass cleanly.

---

## Top 3 Most Impactful Improvements

1. Make `SentenceTransformer` in the stub raise `ImportError` so tests that omit `scorer._model =` pre-assignment fail loudly instead of silently succeeding with a MagicMock model.
2. Move stub registration into the `pytest_configure` hook for explicitness and pytest convention alignment.
3. Add a brief comment on `side_effect` list iteration semantics for the tiering and sort tests.
