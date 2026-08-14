"""Ingestion engine — extracts concepts from transcripts and upserts wiki pages."""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .models import WikiPageMeta, ExtractedConcept, ClassifiedSection
from .classifier import (
    TranscriptClassifier,
    split_transcript_into_sections,
    extract_source_urls_from_section,
    _SectionClassification,
)
from .git_hooks import WikiGitManager
from .index_builder import IndexBuilder
from .utils import (
    load_prompt,
    slugify,
    format_page,
    parse_json_response,
    coerce_json_list,
    build_response_format,
)

try:
    from ..gemini_client import GeminiClientWithFallback
except ImportError:
    # When wiki_engine is imported as a top-level package (e.g. in tests that
    # add research_papers/ directly to sys.path) the relative import fails.
    from research_papers.gemini_client import GeminiClientWithFallback

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


class _ExtractedConceptModel(BaseModel):
    """Structured-output contract for a single extracted concept."""

    model_config = ConfigDict(extra="forbid")

    name: str
    tldr: str
    body: str
    counterarguments: str
    confidence: float
    categories: list[str]
    related_concepts: list[str]
    sources: list[str]


class _ExtractedConceptList(BaseModel):
    """Object wrapper — json_schema requires an object root, not a bare array."""

    model_config = ConfigDict(extra="forbid")

    concepts: list[_ExtractedConceptModel]


# OpenRouter structured-output schema derived from the pydantic models above.
_EXTRACT_RESPONSE_FORMAT = build_response_format(
    "extracted_concepts", _ExtractedConceptList
)


class _SectionAnalysisModel(BaseModel):
    """Structured-output contract combining classification and concept extraction."""

    model_config = ConfigDict(extra="forbid")

    category: str
    title: str
    paper_urls: list[str]
    concepts: list[_ExtractedConceptModel]


# Combined schema — lets a single OpenRouter call return both the
# classification fields and the extracted concepts for a section.
_ANALYZE_RESPONSE_FORMAT = build_response_format(
    "section_analysis", _SectionAnalysisModel
)

_EXTRACT_CONCEPTS_FALLBACK = """You are a knowledge extraction engine. Given a research paper transcript section, extract the key concepts discussed.

Return a JSON object with a "concepts" array, where each element has:
- "name": The concept name (e.g., "Mixture of Experts", "State Space Models")
- "tldr": A single sentence summary
- "body": A structured explanation (2-4 paragraphs, use markdown)
- "counterarguments": Known limitations, data gaps, or counterarguments (1-2 paragraphs)
- "confidence": How confident you are in the extraction (0.0-1.0)
- "categories": List of topic categories this concept belongs to
- "related_concepts": Names of other concepts this relates to
- "sources": Any paper URLs or references mentioned

Respond ONLY with a valid JSON object of the form {"concepts": [...]}. No markdown formatting."""

_ANALYZE_SECTION_FALLBACK = """You are a research paper classifier and knowledge extraction engine. Given a transcript section, classify it and extract the key concepts discussed.

Return a JSON object with these fields:
- "category": The primary category (one of: "AI Architecture", "Hardware", "Benchmarking", "Optimization", "NLP", "Computer Vision", "Reinforcement Learning", "Robotics", "Time Series", "AI Agents", "Safety & Alignment", "Other")
- "title": A short descriptive title for this section (max 10 words)
- "paper_urls": Any URLs mentioned in the text (list of strings)
- "concepts": An array of extracted concepts, where each element has:
  - "name": The concept name (e.g., "Mixture of Experts", "State Space Models")
  - "tldr": A single sentence summary
  - "body": A structured explanation (2-4 paragraphs, use markdown)
  - "counterarguments": Known limitations, data gaps, or counterarguments (1-2 paragraphs)
  - "confidence": How confident you are in the extraction (0.0-1.0)
  - "categories": List of topic categories this concept belongs to
  - "related_concepts": Names of other concepts this relates to
  - "sources": Any paper URLs or references mentioned

Respond ONLY with a valid JSON object of the form {"category": ..., "title": ..., "paper_urls": [...], "concepts": [...]}. No markdown formatting."""

_UPDATE_CONCEPT_FALLBACK = """You are a knowledge base editor. You are updating an existing concept page with new information from a recent research paper.

EXISTING PAGE CONTENT:
{existing_content}

NEW INFORMATION TO INTEGRATE:
{new_info}

Rules:
1. APPEND new findings to the existing body — do NOT overwrite existing content
2. Update the TLDR only if the new info significantly changes the summary
3. Add new counterarguments/data gaps if the new paper reveals any
4. Preserve all existing sources and add new ones
5. Update confidence if warranted

Return a JSON object with:
- "tldr": Updated single-sentence TLDR
- "body": Updated full body (including existing content + new additions clearly marked)
- "counterarguments": Updated counterarguments section
- "confidence": Updated confidence score (0.0-1.0)
- "new_sources": List of new source URLs to add

Respond ONLY with valid JSON. No markdown formatting."""


class WikiIngestionEngine:
    """Ingests transcripts into the wiki, creating/updating concept and source pages."""

    def __init__(
        self,
        wiki_dir: str,
        api_key: str | None = None,
        llm_client=None,
        model_name: str = "gemini-3.1-flash-lite-preview",
        backup_api_key: str | None = None,
        openrouter_api_key: str | None = None,
        openrouter_model: str | None = None,
        classifier: Optional[TranscriptClassifier] = None,
        index_builder: Optional[IndexBuilder] = None,
        git_manager: Optional[WikiGitManager] = None,
        auto_commit: bool = False,
        rebuild_index: bool = True,
        repo_root: Optional[str] = None,
        parent_root: Optional[str] = None,
        branch: str = "main",
        auto_push: bool = False,
        push_parent: bool = False,
        llm_merge_updates: bool = False,
        combined_analysis: bool = True,
        max_workers: int = 4,
    ):
        self.wiki_dir = Path(wiki_dir)
        self.sources_dir = self.wiki_dir / "sources"
        self.concepts_dir = self.wiki_dir / "concepts"
        self.raw_summary_dir = self.wiki_dir / "raw_summary"
        self.model_name = model_name
        # The wiki portion uses OpenRouter exclusively when configured; fall
        # back to a Gemini fallback client, then a bare llm_client for tests.
        if openrouter_api_key and openrouter_model:
            self.llm_client = GeminiClientWithFallback(
                api_key=api_key or "",
                model_name=model_name,
                openrouter_api_key=openrouter_api_key,
                openrouter_model=openrouter_model,
                openrouter_only=True,
            )
        elif api_key:
            self.llm_client = GeminiClientWithFallback(
                api_key=api_key,
                model_name=model_name,
                backup_api_key=backup_api_key,
            )
        else:
            self.llm_client = llm_client
        self.llm_merge_updates = llm_merge_updates
        self.combined_analysis = combined_analysis
        self.max_workers = max_workers
        # Only the legacy combined_analysis=False path needs a classifier, so
        # it is built on demand to avoid loading its prompt on every engine.
        self.classifier = classifier
        self._failed_sections = 0
        self._failure_lock = threading.Lock()
        self.index_builder = index_builder or IndexBuilder(str(self.wiki_dir))
        self.auto_commit = auto_commit
        self.rebuild_index = rebuild_index
        repo_path = Path(repo_root) if repo_root else self.wiki_dir.parent
        self.git_manager = git_manager or WikiGitManager(
            repo_root=str(repo_path),
            wiki_dir=str(self.wiki_dir),
            parent_root=parent_root,
            branch=["main", "feat/kokoro-cpu-tts"],  # Updated to include the new branch
            auto_push=auto_push,
            push_parent=push_parent,
        )
        self._extract_prompt = load_prompt(
            PROMPTS_DIR, "extract_concepts_system.txt", _EXTRACT_CONCEPTS_FALLBACK
        )
        self._analyze_prompt = load_prompt(
            PROMPTS_DIR, "analyze_section_system.txt", _ANALYZE_SECTION_FALLBACK
        )
        self._update_prompt = load_prompt(
            PROMPTS_DIR, "update_concept_system.txt", _UPDATE_CONCEPT_FALLBACK
        )

    def _llm_generate(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        response_format: dict | None = None,
    ) -> str | None:
        """Call the LLM, routing through the fallback client when available."""
        if self.llm_client is None:
            return None
        # GeminiClientWithFallback exposes .generate(); legacy bare clients do not.
        try:
            from ..gemini_client import GeminiClientWithFallback
        except ImportError:
            from research_papers.gemini_client import GeminiClientWithFallback
        if isinstance(self.llm_client, GeminiClientWithFallback):
            return self.llm_client.generate(user_prompt, system_prompt, response_format)
        response = self.llm_client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config={"system_instruction": system_prompt} if system_prompt else {},
        )
        return response.text

    def ingest_transcript(self, transcript_path: str, date_str: str) -> dict:
        """Ingest a daily transcript into the wiki.

        Args:
            transcript_path: Path to the transcript file.
            date_str: Date string (YYYY-MM-DD).

        Returns:
            Dict with keys: source_page, concepts_created, concepts_updated
        """
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_text = f.read()

        result = {
            "source_page": "",
            "concepts_created": [],
            "concepts_updated": [],
            "index_page": "",
            "auto_committed": False,
        }

        # Step 1: Create source page
        source_page_path = self._create_source_page(transcript_text, date_str)
        result["source_page"] = str(source_page_path)

        # Step 2/3: Classify sections and extract their concepts. The
        # combined path makes one LLM call per section instead of two.
        sections = split_transcript_into_sections(transcript_text)
        self._failed_sections = 0
        if self.combined_analysis:
            analyzed = self._analyze_sections(sections)
        else:
            self.classifier = self.classifier or TranscriptClassifier(
                self.llm_client, self.model_name
            )
            classified = self.classifier.classify(sections)
            # Inject Python-extracted source URLs into each classified
            # section. This is intentionally done by Python code, not the
            # LLM, so that the original arXiv / Hugging Face URLs reliably
            # make it into wiki pages.
            for cs in classified:
                cs.paper_urls = self._merge_source_urls(
                    extract_source_urls_from_section(cs.text), cs.paper_urls
                )
            analyzed = [(cs, self._extract_concepts(cs)) for cs in classified]

        # Upserts touch concept .md files by slug and must stay sequential —
        # concurrent writes to the same slug would corrupt pages.
        for _section, concepts in analyzed:
            for concept in concepts:
                was_updated = self._upsert_concept(concept, date_str)
                if was_updated:
                    result["concepts_updated"].append(concept.name)
                else:
                    result["concepts_created"].append(concept.name)

        # Step 4: Rebuild index after any ingestion run
        if self.rebuild_index:
            index_path = self.index_builder.rebuild()
            result["index_page"] = str(index_path)

        result["sections_total"] = len(sections)
        result["sections_failed"] = self._failed_sections
        all_failed = bool(sections) and self._failed_sections == len(sections)
        if all_failed:
            logger.error(
                "All %d sections failed analysis; skipping auto-commit.",
                len(sections),
            )

        # Step 5: Optional auto-commit of wiki mutations
        if self.auto_commit and not all_failed:
            result["auto_committed"] = self.git_manager.auto_commit(
                message=f"wiki: ingest transcript {date_str}"
            )

        return result

    @staticmethod
    def _merge_source_urls(
        priority_urls: List[str], existing_urls: List[str]
    ) -> List[str]:
        """Merge two URL lists, priority_urls first, deduplicating while preserving order."""
        return list(dict.fromkeys(priority_urls + (existing_urls or [])))

    def _create_source_page(self, transcript_text: str, date_str: str) -> Path:
        """Create a source page for the daily transcript."""
        self.sources_dir.mkdir(parents=True, exist_ok=True)

        filename = f"digest_{date_str}.md"
        filepath = self.sources_dir / filename

        meta = WikiPageMeta(
            title=f"Research Digest {date_str}",
            type="source",
            sources=[],
            categories=["daily-digest"],
        )

        content = format_page(meta, transcript_text)
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Created source page: {filepath}")
        return filepath

    def archive_raw_summary(self, transcript_path: str, date_str: str) -> Path:
        """Archive a daily transcript verbatim into wiki/raw_summary/ — no LLM
        calls at all.

        This is the default, cheap alternative to `ingest_transcript` (which
        does one LLM classify+extract call per section and upserts concept
        pages). It exists so the daily pipeline can keep a durable record of
        each day's research digest without paying for or waiting on the
        LLM-wiki machinery, which is opt-in via `--llm-wiki` on
        run_wiki_ingestion.py.
        """
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_text = f.read()

        self.raw_summary_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.raw_summary_dir / f"digest_{date_str}.md"

        meta = WikiPageMeta(
            title=f"Research Digest {date_str}",
            type="raw-summary",
            sources=[],
            categories=["daily-digest"],
        )
        content = format_page(meta, transcript_text)
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Archived raw summary: {filepath}")

        if self.auto_commit:
            self.git_manager.auto_commit(
                message=f"wiki: archive raw summary {date_str}"
            )

        return filepath

    def _extract_concepts(self, section: ClassifiedSection) -> List[ExtractedConcept]:
        """Use LLM to extract concepts from a classified section."""
        if not self.llm_client:
            return []

        data = parse_json_response(
            lambda: self._llm_generate(
                section.text[:8000], self._extract_prompt, _EXTRACT_RESPONSE_FORMAT
            ),
            context="extract_concepts",
        )
        if data is None:
            return []

        return self._build_concepts(data, section)

    def _build_concepts(
        self, data: dict, section: ClassifiedSection
    ) -> List[ExtractedConcept]:
        """Turn a parsed ``concepts`` payload into ExtractedConcept objects."""
        concepts = []
        for item in coerce_json_list(data, "concepts"):
            if not isinstance(item, dict):
                continue
            try:
                parsed = _ExtractedConceptModel.model_validate(item)
            except ValidationError as e:
                logger.warning("Skipping concept failing schema validation: %s", e)
                continue
            concepts.append(
                ExtractedConcept(
                    name=parsed.name or "Unknown",
                    tldr=parsed.tldr,
                    body=parsed.body,
                    counterarguments=parsed.counterarguments,
                    confidence=parsed.confidence,
                    categories=parsed.categories or [section.category],
                    related_concepts=parsed.related_concepts,
                    # Always include Python-extracted paper URLs; supplement
                    # with any sources the LLM also identified.  dict.fromkeys
                    # preserves insertion order and removes duplicates.
                    sources=list(dict.fromkeys(section.paper_urls + parsed.sources)),
                )
            )
        return concepts

    def _analyze_sections(
        self, sections: List[str]
    ) -> List[Tuple[ClassifiedSection, List[ExtractedConcept]]]:
        """Classify and extract concepts for every section.

        Sequential when max_workers <= 1 (no executor is spun up at all);
        otherwise uses a thread pool. Results always come back in the
        original section order — executor.map preserves input order
        regardless of completion order.
        """
        if self.max_workers <= 1 or len(sections) <= 1:
            return [
                self._analyze_section_safe(i, text) for i, text in enumerate(sections)
            ]
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            return list(
                executor.map(
                    self._analyze_section_safe, range(len(sections)), sections
                )
            )

    def _analyze_section_safe(
        self, index: int, text: str
    ) -> Tuple[ClassifiedSection, List[ExtractedConcept]]:
        """Run _analyze_section, isolating a failure to just this section."""
        try:
            return self._analyze_section(text)
        except Exception as e:
            logger.warning("Section %d analysis raised; skipping: %s", index, e)
            with self._failure_lock:
                self._failed_sections += 1
            return (
                ClassifiedSection(text=text, category="Other", title="Unclassified"),
                [],
            )

    def _analyze_section(
        self, text: str
    ) -> Tuple[ClassifiedSection, List[ExtractedConcept]]:
        """Classify a section and extract its concepts in a single LLM call."""
        default_section = ClassifiedSection(
            text=text, category="Other", title="Unclassified"
        )
        if not self.llm_client:
            return default_section, []

        data = parse_json_response(
            lambda: self._llm_generate(
                text[:8000], self._analyze_prompt, _ANALYZE_RESPONSE_FORMAT
            ),
            context="analyze_section",
        )
        if not isinstance(data, dict):
            return default_section, []

        # Validate only the fields the classification contract owns — extra
        # keys the model volunteers must never destroy the parsed concepts.
        raw_classification = {k: data.get(k) for k in ("category", "title", "paper_urls")}
        raw_classification["paper_urls"] = raw_classification.get("paper_urls") or []
        try:
            classification = _SectionClassification.model_validate(raw_classification)
            section = ClassifiedSection(
                text=text,
                category=classification.category or "Other",
                title=classification.title,
                paper_urls=classification.paper_urls,
            )
        except ValidationError as e:
            logger.warning("Section classification invalid, defaulting: %s", e)
            section = default_section
        # Inject Python-extracted source URLs into the section. This is
        # intentionally done by Python code, not the LLM, so that the
        # original arXiv / Hugging Face URLs reliably make it into wiki pages.
        section.paper_urls = self._merge_source_urls(
            extract_source_urls_from_section(text), section.paper_urls
        )

        return section, self._build_concepts(data, section)

    def _upsert_concept(self, concept: ExtractedConcept, date_str: str) -> bool:
        """Create or update a concept page. Returns True if updated existing."""
        self.concepts_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(concept.name)
        filepath = self.concepts_dir / f"{slug}.md"

        if filepath.exists():
            self._update_existing_concept(filepath, concept, date_str)
            return True
        else:
            self._create_new_concept(filepath, concept, date_str)
            return False

    def _create_new_concept(
        self, filepath: Path, concept: ExtractedConcept, date_str: str
    ) -> None:
        """Create a new concept page."""
        meta = WikiPageMeta(
            title=concept.name,
            type="concept",
            sources=concept.sources,
            confidence=concept.confidence,
            categories=concept.categories,
        )

        # Build page body
        related_links = " ".join([f"[[{r}]]" for r in concept.related_concepts])
        body = f"""## TLDR

{concept.tldr}

## Body

{concept.body}

## Counterarguments / Data Gaps

{concept.counterarguments}

## Related Concepts

{related_links}
"""
        content = format_page(meta, body)
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Created concept page: {filepath}")

    def _update_existing_concept(
        self, filepath: Path, concept: ExtractedConcept, date_str: str
    ) -> None:
        """Update an existing concept page with new information."""
        existing_content = filepath.read_text(encoding="utf-8")

        if self.llm_client and self.llm_merge_updates:
            updated = self._llm_update_concept(existing_content, concept)
        else:
            updated = self._simple_append(existing_content, concept, date_str)

        filepath.write_text(updated, encoding="utf-8")
        logger.info(f"Updated concept page: {filepath}")

    def _llm_update_concept(
        self, existing_content: str, concept: ExtractedConcept
    ) -> str:
        """Use LLM to intelligently merge new info into existing page."""
        _, existing_body = self._parse_page(existing_content)
        new_info = f"Name: {concept.name}\nTLDR: {concept.tldr}\nBody: {concept.body}\nCounterarguments: {concept.counterarguments}"

        prompt = self._update_prompt.format(
            existing_content=existing_content,
            new_info=new_info,
        )

        try:
            result_text = self._llm_generate(prompt)
            if result_text is None:
                return self._simple_append(
                    existing_content, concept, datetime.now().strftime("%Y-%m-%d")
                )
            result_text = result_text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                result_text = result_text.rsplit("```", 1)[0]

            data = json.loads(result_text)

            # Parse existing frontmatter
            meta, _ = self._parse_page(existing_content)
            meta.updated = datetime.now().strftime("%Y-%m-%d")
            meta.confidence = data.get("confidence", meta.confidence)
            new_sources = data.get("new_sources", [])
            meta.sources = list(set(meta.sources + new_sources + concept.sources))

            merged_body = data.get("body", concept.body)
            # Guard against accidental overwrite: preserve prior context if model returns truncated content.
            if existing_body and (
                len(merged_body) < max(int(len(existing_body) * 0.6), 200)
                and existing_body[:80] not in merged_body
            ):
                logger.warning("LLM merge looked lossy; falling back to safe append")
                return self._simple_append(
                    existing_content,
                    concept,
                    datetime.now().strftime("%Y-%m-%d"),
                )

            related_links = " ".join([f"[[{r}]]" for r in concept.related_concepts])
            body = f"""## TLDR

{data.get('tldr', concept.tldr)}

## Body

{merged_body}

## Counterarguments / Data Gaps

{data.get('counterarguments', concept.counterarguments)}

## Related Concepts

{related_links}
"""
            return format_page(meta, body)

        except Exception as e:
            logger.warning(f"LLM update failed, using simple append: {e}")
            return self._simple_append(
                existing_content, concept, datetime.now().strftime("%Y-%m-%d")
            )

    def _simple_append(
        self, existing_content: str, concept: ExtractedConcept, date_str: str
    ) -> str:
        """Simple append of new info to existing page."""
        meta, body = self._parse_page(existing_content)
        meta.updated = date_str
        meta.sources = list(set(meta.sources + concept.sources))

        append_text = f"\n\n---\n\n### Update ({date_str})\n\n{concept.body}\n"
        if concept.counterarguments:
            append_text += f"\n**New counterarguments:** {concept.counterarguments}\n"

        new_body = body + append_text
        return format_page(meta, new_body)

    def _parse_page(self, content: str) -> Tuple[WikiPageMeta, str]:
        """Parse a wiki page into metadata and body."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1].strip()
                body = parts[2].strip()
                data = yaml.safe_load(frontmatter_str) or {}
                meta = WikiPageMeta(
                    title=data.get("title", ""),
                    type=data.get("type", "concept"),
                    sources=data.get("sources", []),
                    created=data.get("created", ""),
                    updated=data.get("updated", ""),
                    confidence=data.get("confidence", 0.5),
                    categories=data.get("categories", []),
                )
                return meta, body
        return WikiPageMeta(title="", type="concept"), content

    @staticmethod
    def _slugify(name: str) -> str:
        """Convert a concept name to a filesystem-safe slug."""
        return slugify(name)
