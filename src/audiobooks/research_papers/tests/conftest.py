"""Pytest configuration for research_papers tests.

Adds both `research_papers/` and `src/audiobooks/` to sys.path so that:
  - Wiki tests can do `from wiki_engine.xxx import ...` directly
  - Package-relative imports in wiki_engine (e.g. `from research_papers.gemini_client`)
    resolve correctly when modules are loaded without the full package context.
"""

import os
import sys

# research_papers/ — enables `from wiki_engine.xxx import ...`
_research_papers_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _research_papers_dir not in sys.path:
    sys.path.insert(0, _research_papers_dir)

# src/audiobooks/ — enables `from research_papers.gemini_client import ...`
_audiobooks_dir = os.path.dirname(_research_papers_dir)
if _audiobooks_dir not in sys.path:
    sys.path.insert(0, _audiobooks_dir)
