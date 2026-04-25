"""Ingestion engine — extracts concepts from transcripts and upserts wiki pages."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from .models import WikiPageMeta, ExtractedConcept, ClassifiedSection
from .classifier import TranscriptClassifier, split_transcript_into_sections
from .git_hooks import WikiGitManager
from .index_builder import IndexBuilder
from .utils import load_prompt, slugify, format_page
try:
    from ..gemini_client import GeminiClientWithFallback
except ImportError:
    # When wiki_engine is imported as a top-level package (e.g. in tests that
    # add research_papers/ directly to sys.path) the relative import fails.
    from research_papers.gemini_client import GeminiClientWithFallback

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

_EXTRACT_CONCEPTS_FALLBACK = """You are a knowledge extraction engine. Given a research paper transcript section, extract the key concepts discussed.

For EACH distinct concept, return a JSON array where each element has:
- "name": The concept name (e.g., "Mixture of Experts", "State Space Models")
- "tldr": A single sentence summary
- "body": A structured explanation (2-4 paragraphs, use markdown)
- "counterarguments": Known limitations, data gaps, or counterarguments (1-2 paragraphs)
- "confidence": How confident you are in the extraction (0.0-1.0)
- "categories": List of topic categories this concept belongs to
- "related_concepts": Names of other concepts this relates to
- "sources": Any paper URLs or references mentioned

Respond ONLY with a valid JSON array. No markdown formatting."""

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
        paid_api_key: str | None = None,
        paid_model_name: str | None = None,
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
    ):
        self.wiki_dir = Path(wiki_dir)
        self.sources_dir = self.wiki_dir / "sources"
        self.concepts_dir = self.wiki_dir / "concepts"
        self.model_name = model_name
        # Prefer api_key to build a fallback-capable client; fall back to bare
        # llm_client for backward compatibility (e.g. in tests).
        if api_key:
            self.llm_client = GeminiClientWithFallback(
                api_key=api_key,
                model_name=model_name,
                backup_api_key=backup_api_key,
                paid_api_key=paid_api_key,
                paid_model_name=paid_model_name,
            )
        else:
            self.llm_client = llm_client
        self.classifier = classifier or TranscriptClassifier(self.llm_client, model_name)
        self.index_builder = index_builder or IndexBuilder(str(self.wiki_dir))
        self.auto_commit = auto_commit
        self.rebuild_index = rebuild_index
        repo_path = Path(repo_root) if repo_root else self.wiki_dir.parent
        self.git_manager = git_manager or WikiGitManager(
            repo_root=str(repo_path),
            wiki_dir=str(self.wiki_dir),
            parent_root=parent_root,
            branch=branch,
            auto_push=auto_push,
            push_parent=push_parent,
        )
        self._extract_prompt = load_prompt(PROMPTS_DIR, "extract_concepts_system.txt", _EXTRACT_CONCEPTS_FALLBACK)
        self._update_prompt = load_prompt(PROMPTS_DIR, "update_concept_system.txt", _UPDATE_CONCEPT_FALLBACK)

    def _llm_generate(self, user_prompt: str, system_prompt: str | None = None) -> str | None:
        """Call the LLM, routing through the fallback client when available."""
        if self.llm_client is None:
            return None
        # GeminiClientWithFallback exposes .generate(); legacy bare clients do not.
        try:
            from ..gemini_client import GeminiClientWithFallback
        except ImportError:
            from research_papers.gemini_client import GeminiClientWithFallback
        if isinstance(self.llm_client, GeminiClientWithFallback):
            return self.llm_client.generate(user_prompt, system_prompt)
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

        # Step 2: Split and classify sections
        sections = split_transcript_into_sections(transcript_text)
        classified = self.classifier.classify(sections)

        # Step 3: Extract concepts from each section
        for section in classified:
            concepts = self._extract_concepts(section)
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

        # Step 5: Optional auto-commit of wiki mutations
        if self.auto_commit:
            result["auto_committed"] = self.git_manager.auto_commit(
                message=f"wiki: ingest transcript {date_str}"
            )

        return result

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

    def _extract_concepts(self, section: ClassifiedSection) -> List[ExtractedConcept]:
        """Use LLM to extract concepts from a classified section."""
        if not self.llm_client:
            return []

        try:
            result_text = self._llm_generate(section.text[:8000], self._extract_prompt)
            if result_text is None:
                return []
            result_text = result_text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                result_text = result_text.rsplit("```", 1)[0]

            data = json.loads(result_text)
            if not isinstance(data, list):
                data = [data]

            concepts = []
            for item in data:
                concept = ExtractedConcept(
                    name=item.get("name", "Unknown"),
                    tldr=item.get("tldr", ""),
                    body=item.get("body", ""),
                    counterarguments=item.get("counterarguments", ""),
                    confidence=item.get("confidence", 0.5),
                    categories=item.get("categories", [section.category]),
                    related_concepts=item.get("related_concepts", []),
                    sources=item.get("sources", section.paper_urls),
                )
                concepts.append(concept)
            return concepts

        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON: %s", e)
            return []
        except Exception:
            logger.exception("Unexpected error during concept extraction")
            return []

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
        related_links = " ".join(
            [f"[[{r}]]" for r in concept.related_concepts]
        )
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

        if self.llm_client:
            updated = self._llm_update_concept(existing_content, concept)
        else:
            # Fallback: simple append
            updated = self._simple_append(existing_content, concept, date_str)

        filepath.write_text(updated, encoding="utf-8")
        logger.info(f"Updated concept page: {filepath}")

    def _llm_update_concept(self, existing_content: str, concept: ExtractedConcept) -> str:
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
                return self._simple_append(existing_content, concept, datetime.now().strftime("%Y-%m-%d"))
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

            related_links = " ".join(
                [f"[[{r}]]" for r in concept.related_concepts]
            )
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
            return self._simple_append(existing_content, concept, datetime.now().strftime("%Y-%m-%d"))

    def _simple_append(self, existing_content: str, concept: ExtractedConcept, date_str: str) -> str:
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
