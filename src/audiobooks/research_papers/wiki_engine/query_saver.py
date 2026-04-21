"""Query saver — saves Q&A results as wiki pages."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .git_hooks import WikiGitManager
from .index_builder import IndexBuilder
from .models import WikiPageMeta

logger = logging.getLogger(__name__)


class QuerySaver:
    """Saves AI Q&A results as wiki pages in the queries folder."""

    def __init__(
        self,
        wiki_dir: str,
        git_manager: Optional[WikiGitManager] = None,
        index_builder: Optional[IndexBuilder] = None,
        auto_commit: bool = False,
        rebuild_index: bool = True,
        repo_root: Optional[str] = None,
    ):
        self.wiki_dir = Path(wiki_dir)
        self.queries_dir = self.wiki_dir / "queries"
        self.auto_commit = auto_commit
        self.rebuild_index = rebuild_index
        self.index_builder = index_builder or IndexBuilder(str(self.wiki_dir))
        repo_path = Path(repo_root) if repo_root else self.wiki_dir.parent
        self.git_manager = git_manager or WikiGitManager(
            repo_root=str(repo_path),
            wiki_dir=str(self.wiki_dir),
        )

    def save(self, question: str, answer: str, sources: list = None) -> Path:
        """Save a Q&A exchange as a wiki page.

        Args:
            question: The user's question.
            answer: The AI's answer.
            sources: Optional list of source URLs referenced.

        Returns:
            Path to the created wiki page.
        """
        self.queries_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = self._slugify(question)
        filename = f"{date_str}_{slug}.md"
        filepath = self.queries_dir / filename

        # Handle collision
        counter = 1
        while filepath.exists():
            filename = f"{date_str}_{slug}_{counter}.md"
            filepath = self.queries_dir / filename
            counter += 1

        meta = WikiPageMeta(
            title=question,
            type="query-result",
            sources=sources or [],
            categories=["query"],
        )

        body = f"""## Question

{question}

## Answer

{answer}
"""
        content = self._format_page(meta, body)
        filepath.write_text(content, encoding="utf-8")

        if self.rebuild_index:
            self.index_builder.rebuild()

        if self.auto_commit:
            self.git_manager.auto_commit(
                message=f"wiki: save query {date_str}"
            )

        logger.info(f"Saved query result: {filepath}")
        return filepath

    def _format_page(self, meta: WikiPageMeta, body: str) -> str:
        """Format a wiki page with YAML frontmatter."""
        frontmatter = yaml.dump(meta.to_dict(), default_flow_style=False, sort_keys=False)
        return f"---\n{frontmatter}---\n\n{body}\n"

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert question text to a filesystem-safe slug."""
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s]+", "_", slug)
        # Truncate to reasonable length
        return slug[:60]
