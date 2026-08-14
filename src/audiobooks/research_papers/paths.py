"""Shared filesystem paths for the research_papers subsystem.

run_research_pipeline.py (the writer) and run_wiki_ingestion.py (the reader)
each computed raw_content/'s location independently. Define it once here so
the two can't silently diverge — a mismatch there looks like "there were no
papers" rather than "the path is wrong".
"""

import os

RESEARCH_PAPERS_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CONTENT_DIR = os.path.join(os.path.dirname(RESEARCH_PAPERS_DIR), "raw_content")
