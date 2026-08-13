"""Wiki linter — finds contradictions, orphans, and implicit concepts."""

import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .git_hooks import WikiGitManager
from .utils import (
    load_prompt,
    slugify,
    parse_json_response,
    coerce_json_list,
    build_response_format,
)
from .index_builder import IndexBuilder  # Added import for IndexBuilder

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

_LINT_SYSTEM_FALLBACK = """You are a knowledge base auditor. Review the following wiki pages and identify:

1. CONTRADICTIONS: Cases where two pages make conflicting claims about the same topic.
2. IMPLICIT CONCEPTS: Terms or concepts that are mentioned frequently but do not have their own dedicated page.

For each issue found, provide:
- "type": "contradiction" or "implicit_concept"
- "description": What the issue is
- "pages_involved": List of page filenames involved
- "severity": "high", "medium", or "low"

Return a JSON object of the form {"issues": [...]}. Respond ONLY with valid JSON."""

LINT_SYSTEM_PROMPT = load_prompt(PROMPTS_DIR, "lint_system.txt", _LINT_SYSTEM_FALLBACK)


class _LintIssue(BaseModel):
    """Structured-output contract for a single lint issue."""

    model_config = ConfigDict(extra="forbid")

    type: str
    description: str
    pages_involved: list[str]
    severity: str


class _LintIssueList(BaseModel):
    """Object wrapper — json_schema requires an object root, not a bare array."""

    model_config = ConfigDict(extra="forbid")

    issues: list[_LintIssue]


# OpenRouter structured-output schema derived from the pydantic models above.
_LINT_RESPONSE_FORMAT = build_response_format("lint_issues", _LintIssueList)

_TECH_TERM_PATTERN = re.compile(
    r"\b(?:transformer|attention|diffusion|reinforcement learning|"
    r"state space|mixture of experts|fine-tuning|"
    r"knowledge distillation|quantization|pruning)\b",
    re.IGNORECASE,
)


class WikiLinter:
    """Performs maintenance passes on the wiki to find issues."""

    def __init__(
        self,
        wiki_dir: str,
        llm_client=None,
        model_name: str = "gemini-3.1-flash-lite-preview",
        git_manager: Optional[WikiGitManager] = None,
        index_builder: Optional[IndexBuilder] = None,  # Added index_builder
        auto_commit: bool = False,
        repo_root: Optional[str] = None,
        parent_root: Optional[str] = None,  # Added parent_root
        branch: list[str] = [
            "main",
            "feat/kokoro-cpu-tts",
        ],  # Updated to include the new branch
        auto_push: bool = False,  # Added auto_push
        push_parent: bool = False,  # Added push_parent
    ):
        self.wiki_dir = Path(wiki_dir)
        self.concepts_dir = self.wiki_dir / "concepts"
        self.sources_dir = self.wiki_dir / "sources"
        self.queries_dir = self.wiki_dir / "queries"
        self.llm_client = llm_client
        self.model_name = model_name
        self.git_manager = git_manager or WikiGitManager(
            repo_root=str(repo_root) if repo_root else self.wiki_dir.parent,
            wiki_dir=str(self.wiki_dir),
            parent_root=parent_root,
            branch=branch,
            auto_push=auto_push,
            push_parent=push_parent,
        )
        self.index_builder = index_builder or IndexBuilder(
            str(self.wiki_dir)
        )  # Initialize index_builder
        self.auto_commit = auto_commit

    def run_full_lint(self) -> dict:
        """Run all lint checks and generate a report.

        Returns:
            Dict with keys: orphans, contradictions, implicit_concepts, report_path
        """
        result = {
            "orphans": [],
            "contradictions": [],
            "implicit_concepts": [],
            "report_path": "",
        }

        # 1. Find orphan pages
        result["orphans"] = self.find_orphan_pages()

        # 2. Find contradictions (LLM-powered)
        result["contradictions"] = self.find_contradictions()

        # 3. Find implicit concepts
        result["implicit_concepts"] = self.find_implicit_concepts()

        # 4. Write report
        report_path = self._write_report(result)
        result["report_path"] = str(report_path)
        result["auto_committed"] = False

        if self.auto_commit:
            result["auto_committed"] = self.git_manager.auto_commit(
                message=f"wiki: lint pass {datetime.now().strftime('%Y-%m-%d')}"
            )

        return result

    def find_orphan_pages(self) -> List[str]:
        """Find pages that have no inbound [[wikilinks]] from other pages.

        Returns:
            List of orphan page filenames.
        """
        if not self.concepts_dir.exists():
            return []

        # Collect all concept page slugs
        all_pages: Set[str] = set()
        for f in self.concepts_dir.glob("*.md"):
            all_pages.add(f.stem)

        # Collect all wikilink targets across all wiki files
        linked_pages: Set[str] = set()
        for md_file in self.wiki_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                links = re.findall(r"\[\[([^\]]+)\]\]", content)
                for link in links:
                    linked_pages.add(slugify(link))
            except Exception:
                continue

        # Orphans are pages with no inbound links
        orphans = []
        for page in all_pages:
            if page not in linked_pages:
                orphans.append(f"{page}.md")

        return sorted(orphans)

    def find_contradictions(self) -> List[dict]:
        """Use LLM to find contradictions between concept pages.

        Returns:
            List of contradiction dicts with description, pages_involved, severity.
        """
        if not self.llm_client or not self.concepts_dir.exists():
            return []

        # Gather recently updated concept pages (limit to avoid token overflow)
        pages_content = []
        concept_files = sorted(
            self.concepts_dir.glob("*.md"),
            key=self._updated_sort_key,
            reverse=True,
        )
        for f in concept_files[:20]:
            try:
                content = f.read_text(encoding="utf-8")
                pages_content.append(f"=== {f.name} ===\n{content[:2000]}")
            except Exception:
                continue

        if not pages_content:
            return []

        combined = "\n\n".join(pages_content)

        data = parse_json_response(
            lambda: self._llm_generate(
                combined, LINT_SYSTEM_PROMPT, _LINT_RESPONSE_FORMAT
            ),
            context="find_contradictions",
        )
        if data is None:
            return []

        contradictions = []
        for item in coerce_json_list(data, "issues"):
            if not isinstance(item, dict):
                continue
            try:
                issue = _LintIssue.model_validate(item)
            except ValidationError as e:
                logger.warning("Skipping lint issue failing schema validation: %s", e)
                continue
            if issue.type == "contradiction":
                contradictions.append(issue.model_dump())
        return contradictions

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

    def find_implicit_concepts(self, min_mentions: int = 3) -> List[dict]:
        """Find terms mentioned frequently that lack their own concept page.

        Args:
            min_mentions: Minimum number of mentions to flag a term.

        Returns:
            List of dicts with term and mention_count.
        """
        if not self.wiki_dir.exists():
            return []

        # Get existing concept page names
        existing_concepts: Set[str] = set()
        if self.concepts_dir.exists():
            for f in self.concepts_dir.glob("*.md"):
                existing_concepts.add(f.stem.replace("_", " "))

        # Count term frequency across all pages
        term_counter: Counter = Counter()
        for md_file in self.wiki_dir.rglob("*.md"):
            if md_file.name == "index.md" or md_file.name == "lint_report.md":
                continue
            try:
                content = md_file.read_text(encoding="utf-8")
                # Extract potential concept terms (capitalized multi-word phrases)
                terms = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", content)
                # Also capture common technical terms
                tech_terms = _TECH_TERM_PATTERN.findall(content)
                for term in terms + tech_terms:
                    normalized = term.lower().strip()
                    if normalized not in existing_concepts and len(normalized) > 3:
                        term_counter[normalized] += 1
            except Exception:
                continue

        # Filter by minimum mentions
        implicit = []
        for term, count in term_counter.most_common():
            if count >= min_mentions:
                implicit.append({"term": term, "mention_count": count})
            else:
                break

        # Optional LLM refinement: keep only terms that are truly concept-worthy.
        if self.llm_client and implicit:
            try:
                llm_prompt = (
                    "Given candidate implicit concepts from a wiki, return only true "
                    "missing concepts as JSON array with entries containing "
                    "type='implicit_concept', description, pages_involved, severity, term, mention_count.\n\n"
                    f"Candidates: {json.dumps(implicit)}"
                )
                response = self.llm_client.models.generate_content(
                    model=self.model_name,
                    contents=llm_prompt,
                    config={"system_instruction": LINT_SYSTEM_PROMPT},
                )
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("\n", 1)[1]
                    result_text = result_text.rsplit("```", 1)[0]
                data = json.loads(result_text)
                refined = []
                for item in data:
                    if item.get("type") == "implicit_concept":
                        refined.append(
                            {
                                "term": item.get("term", "").lower().strip(),
                                "mention_count": item.get("mention_count", 0),
                            }
                        )
                if refined:
                    implicit = refined
            except Exception as e:
                logger.warning(f"Implicit concept refinement failed: {e}")

        return implicit

    def _write_report(self, result: dict) -> Path:
        """Write a lint report to wiki/lint_report.md."""
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.wiki_dir / "lint_report.md"

        date_str = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Wiki Lint Report — {date_str}\n",
            f"\n## Orphan Pages ({len(result['orphans'])} found)\n",
        ]

        if result["orphans"]:
            for orphan in result["orphans"]:
                lines.append(f"- `{orphan}` — no inbound links\n")
        else:
            lines.append("- None found.\n")

        lines.append(f"\n## Contradictions ({len(result['contradictions'])} found)\n")
        if result["contradictions"]:
            for c in result["contradictions"]:
                lines.append(
                    f"- **{c.get('severity', 'medium')}**: {c.get('description', '')}\n"
                )
                lines.append(f"  - Pages: {', '.join(c.get('pages_involved', []))}\n")
        else:
            lines.append("- None found.\n")

        lines.append(
            f"\n## Implicit Concepts ({len(result['implicit_concepts'])} found)\n"
        )
        if result["implicit_concepts"]:
            for ic in result["implicit_concepts"]:
                lines.append(
                    f"- **{ic['term']}** — mentioned {ic['mention_count']} times, no dedicated page\n"
                )
        else:
            lines.append("- None found.\n")

        report_path.write_text("".join(lines), encoding="utf-8")
        logger.info(f"Lint report written to {report_path}")
        return report_path

    def _updated_sort_key(self, filepath: Path) -> str:
        """Sort concept pages by YAML `updated` metadata."""
        try:
            content = filepath.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    data = yaml.safe_load(parts[1]) or {}
                    return str(data.get("updated", ""))
        except Exception:
            pass
        return ""
