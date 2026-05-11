"""Index builder — regenerates wiki/index.md from current wiki state."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)


class IndexBuilder:
    """Rebuilds the wiki index.md from the current wiki contents."""

    def __init__(self, wiki_dir: str):
        self.wiki_dir = Path(wiki_dir)

    def rebuild(self) -> Path:
        """Rebuild wiki/index.md by scanning all pages.

        Returns:
            Path to the generated index.md.
        """
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        index_path = self.wiki_dir / "index.md"

        pages_by_type: Dict[str, List[dict]] = {
            "concept": [],
            "source": [],
            "query-result": [],
        }

        # Scan all markdown files
        for md_file in self.wiki_dir.rglob("*.md"):
            if md_file.name in ("index.md", "lint_report.md"):
                continue
            meta = self._extract_meta(md_file)
            if meta:
                page_type = meta.get("type", "concept")
                rel_path = md_file.relative_to(self.wiki_dir)
                if page_type not in pages_by_type:
                    logger.warning(
                        "Skipping page %s with unknown type %r",
                        md_file.name,
                        page_type,
                    )
                else:
                    pages_by_type[page_type].append({
                        "title": meta.get("title", md_file.stem),
                        "path": str(rel_path).replace("\\", "/"),
                        "updated": meta.get("updated", ""),
                        "categories": meta.get("categories", []),
                    })

        # Generate index content
        date_str = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# LLM Wiki Index\n",
            f"\n*Last rebuilt: {date_str}*\n",
            f"\n---\n",
        ]

        # Concepts section
        concepts = sorted(pages_by_type.get("concept", []), key=lambda p: p["title"])
        lines.append(f"\n## Concepts ({len(concepts)} pages)\n\n")
        for page in concepts:
            cats = ", ".join(page["categories"]) if page["categories"] else ""
            cat_suffix = f" — {cats}" if cats else ""
            lines.append(f"- [[{page['title']}]]({page['path']}){cat_suffix}\n")

        # Sources section
        sources = sorted(pages_by_type.get("source", []), key=lambda p: p["updated"], reverse=True)
        lines.append(f"\n## Sources ({len(sources)} pages)\n\n")
        for page in sources:
            lines.append(f"- [{page['title']}]({page['path']}) — {page['updated']}\n")

        # Queries section
        queries = sorted(pages_by_type.get("query-result", []), key=lambda p: p["updated"], reverse=True)
        lines.append(f"\n## Saved Queries ({len(queries)} pages)\n\n")
        for page in queries:
            lines.append(f"- [{page['title']}]({page['path']}) — {page['updated']}\n")

        index_path.write_text("".join(lines), encoding="utf-8")
        logger.info(f"Rebuilt index: {len(concepts)} concepts, {len(sources)} sources, {len(queries)} queries")
        return index_path

    def _extract_meta(self, filepath: Path) -> dict:
        """Extract YAML frontmatter from a markdown file."""
        try:
            content = filepath.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return yaml.safe_load(parts[1]) or {}
        except Exception:
            pass
        return {}
