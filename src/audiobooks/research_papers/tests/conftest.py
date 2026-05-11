"""Pytest configuration for research_papers tests.

Adds both `research_papers/` and `src/audiobooks/` to sys.path so that:
  - Wiki tests can do `from wiki_engine.xxx import ...` directly
  - Package-relative imports in wiki_engine (e.g. `from research_papers.gemini_client`)
    resolve correctly when modules are loaded without the full package context.

Also stubs out optional heavy packages (sentence_transformers, pymupdf) so tests
can run without those libraries installed.  The stubs are inserted into sys.modules
before any test module is collected, ensuring:
  - `@patch("sentence_transformers.util.cos_sim")` can locate its target
  - Top-level `import pymupdf` in paper_downloader.py succeeds during collection
"""

import os
import sys
from unittest.mock import MagicMock

# research_papers/ — enables `from wiki_engine.xxx import ...`
_research_papers_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _research_papers_dir not in sys.path:
    sys.path.insert(0, _research_papers_dir)

# src/audiobooks/ — enables `from research_papers.gemini_client import ...`
_audiobooks_dir = os.path.dirname(_research_papers_dir)
if _audiobooks_dir not in sys.path:
    sys.path.insert(0, _audiobooks_dir)

def pytest_configure(config):
    """Register stubs for optional heavy dependencies before collection begins."""
    # sentence_transformers: imported lazily inside paper_scorer._compute_scores.
    # Tests patch `sentence_transformers.util.cos_sim`; that requires the module to
    # exist in sys.modules so unittest.mock can locate the patch target.
    # The .util attribute on the parent mock must be the *same* object registered as
    # sys.modules["sentence_transformers.util"] so the patch actually applies to the
    # object the production code receives when it does `from sentence_transformers import util`.
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

    # pymupdf: imported at module level in paper_downloader.py.
    # Without this stub the entire test module fails to collect.
    if "pymupdf" not in sys.modules:
        sys.modules["pymupdf"] = MagicMock(name="pymupdf")
