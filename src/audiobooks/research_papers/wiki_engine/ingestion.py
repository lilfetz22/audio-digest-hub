"""Ingestion engine — extracts concepts from transcripts and upserts wiki pages."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from .models import WikiPageMeta, ExtractedConcept, ClassifiedSection
from .classifier import TranscriptClassifier, split_transcript_into_sections
from .git_hooks import WikiGitManager
from .index_builder import IndexBuilder

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str, fallback: str) -> str:
    """Load a prompt template from disk with a safe fallback."""
    try:
        prompt_path = PROMPTS_DIR / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed loading prompt {filename}: {e}")
    return fallback


EXTRACT_CONCEPTS_PROMPT = _load_prompt("extract_concepts_system.txt", """You are a knowledge extraction engine. Given a research paper transcript section, extract the key concepts discussed.

For EACH distinct concept, return a JSON array where each element has:
- "name": The concept name (e.g., "Mixture of Experts", "State Space Models")
- "tldr": A single sentence summary
- "body": A structured explanation (2-4 paragraphs, use markdown)
- "counterarguments": Known limitations, data gaps, or counterarguments (1-2 paragraphs)
- "confidence": How confident you are in the extraction (0.0-1.0)
- "categories": List of topic categories this concept belongs to
- "related_concepts": Names of other concepts this relates to
- "sources": Any paper URLs or references mentioned

Respond ONLY with a valid JSON array. No markdown formatting.""")

UPDATE_CONCEPT_PROMPT = _load_prompt("update_concept_system.txt", """You are a knowledge base editor. You are updating an existing concept page with new information from a recent research paper.

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

Respond ONLY with valid JSON. No markdown formatting.""")


class WikiIngestionEngine:
    """Ingests transcripts into the wiki, creating/updating concept and source pages."""

    def __init__(
        self,
        wiki_dir: str,
        llm_client=None,
        model_name: str = "gemini-3.1-flash-lite-preview",
        classifier: Optional[TranscriptClassifier] = None,
        index_builder: Optional[IndexBuilder] = None,
        git_manager: Optional[WikiGitManager] = None,
        auto_commit: bool = False,
        rebuild_index: bool = True,
        repo_root: Optional[str] = None,
    ):
        self.wiki_dir = Path(wiki_dir)
        self.sources_dir = self.wiki_dir / "sources"
        self.concepts_dir = self.wiki_dir / "concepts"
        self.llm_client = llm_client
        self.model_name = model_name
        self.classifier = classifier or TranscriptClassifier(llm_client, model_name)
        self.index_builder = index_builder or IndexBuilder(str(self.wiki_dir))
        self.auto_commit = auto_commit
        self.rebuild_index = rebuild_index
        repo_path = Path(repo_root) if repo_root else self.wiki_dir.parent
        self.git_manager = git_manager or WikiGitManager(
            repo_root=str(repo_path),
            wiki_dir=str(self.wiki_dir),
        )

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

        content = self._format_page(meta, transcript_text)
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Created source page: {filepath}")
        return filepath

    def _extract_concepts(self, section: ClassifiedSection) -> List[ExtractedConcept]:
        """Use LLM to extract concepts from a classified section."""
        if not self.llm_client:
            return []

        try:
            response = self.llm_client.models.generate_content(
                model=self.model_name,
                contents=section.text[:8000],
                config={"system_instruction": EXTRACT_CONCEPTS_PROMPT},
            )
            result_text = response.text.strip()
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

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Concept extraction failed: {e}")
            return []

    def _upsert_concept(self, concept: ExtractedConcept, date_str: str) -> bool:
        """Create or update a concept page. Returns True if updated existing."""
        self.concepts_dir.mkdir(parents=True, exist_ok=True)

        slug = self._slugify(concept.name)
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
        content = self._format_page(meta, body)
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

        prompt = UPDATE_CONCEPT_PROMPT.format(
            existing_content=existing_content,
            new_info=new_info,
        )

        try:
            response = self.llm_client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            result_text = response.text.strip()
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
            return self._format_page(meta, body)

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
        return self._format_page(meta, new_body)

    def _format_page(self, meta: WikiPageMeta, body: str) -> str:
        """Format a wiki page with YAML frontmatter + body."""
        frontmatter = yaml.dump(meta.to_dict(), default_flow_style=False, sort_keys=False)
        return f"---\n{frontmatter}---\n\n{body}\n"

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
        slug = name.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s]+", "_", slug)
        return slug
