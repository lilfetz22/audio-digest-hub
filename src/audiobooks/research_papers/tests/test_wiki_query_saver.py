"""Tests for the wiki query saver."""

from unittest.mock import MagicMock, patch

import yaml
import pytest

from wiki_engine.query_saver import QuerySaver


@pytest.fixture
def tmp_wiki(tmp_path):
    """Create a temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "queries").mkdir()
    return wiki_dir


class TestQuerySaver:
    """Tests for QuerySaver."""

    @patch("wiki_engine.query_saver.datetime")
    def test_save_query_result(self, mock_dt, tmp_wiki):
        """Saving a Q&A creates a file in wiki/queries/ with correct content."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"

        saver = QuerySaver(wiki_dir=str(tmp_wiki))
        path = saver.save(
            question="How does MoE relate to SSMs?",
            answer="Both are scalability approaches but target different bottlenecks.",
            sources=["https://arxiv.org/abs/2024.12345"],
        )

        assert path.exists()
        assert path.parent.name == "queries"

        content = path.read_text(encoding="utf-8")
        assert "How does MoE relate to SSMs?" in content
        assert "Both are scalability approaches" in content

    @patch("wiki_engine.query_saver.datetime")
    def test_query_file_has_yaml_frontmatter(self, mock_dt, tmp_wiki):
        """Query result has valid YAML frontmatter with type: query-result."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"

        saver = QuerySaver(wiki_dir=str(tmp_wiki))
        path = saver.save(
            question="What is attention?",
            answer="A mechanism for weighted token interactions.",
        )

        content = path.read_text(encoding="utf-8")
        assert content.startswith("---")
        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])

        assert meta["type"] == "query-result"
        assert meta["title"] == "What is attention?"
        assert "created" in meta
        assert "updated" in meta

    @patch("wiki_engine.query_saver.datetime")
    def test_query_file_naming(self, mock_dt, tmp_wiki):
        """Query files follow the {date}_{slug}.md naming convention."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"

        saver = QuerySaver(wiki_dir=str(tmp_wiki))
        path = saver.save(
            question="How does today's paper relate to last week?",
            answer="They share a common framework.",
        )

        assert path.name.startswith("2026-04-15_")
        assert path.suffix == ".md"
        # Slug should be filesystem-safe
        assert " " not in path.stem

    @patch("wiki_engine.query_saver.datetime")
    def test_query_handles_collision(self, mock_dt, tmp_wiki):
        """If file already exists, appends a counter."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"

        saver = QuerySaver(wiki_dir=str(tmp_wiki))

        path1 = saver.save(question="Same question", answer="Answer 1")
        path2 = saver.save(question="Same question", answer="Answer 2")

        assert path1 != path2
        assert path1.exists()
        assert path2.exists()

    @patch("wiki_engine.query_saver.datetime")
    def test_query_includes_sources(self, mock_dt, tmp_wiki):
        """Sources are included in the YAML frontmatter."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"

        saver = QuerySaver(wiki_dir=str(tmp_wiki))
        path = saver.save(
            question="What is MoE?",
            answer="A scaling technique.",
            sources=["https://paper1.com", "https://paper2.com"],
        )

        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])

        assert "https://paper1.com" in meta["sources"]
        assert "https://paper2.com" in meta["sources"]

    def test_slugify(self):
        """Slugify produces filesystem-safe names."""
        assert QuerySaver._slugify("How does X work?") == "how_does_x_work"
        assert QuerySaver._slugify("What's the deal with AI?") == "whats_the_deal_with_ai"
        assert len(QuerySaver._slugify("A" * 100)) <= 60

    @patch("wiki_engine.query_saver.datetime")
    def test_creates_queries_dir_if_missing(self, mock_dt, tmp_path):
        """Creates the queries directory if it doesn't exist."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"

        wiki_dir = tmp_path / "wiki"
        wiki_dir.mkdir()
        # Don't create queries/ subdirectory

        saver = QuerySaver(wiki_dir=str(wiki_dir))
        path = saver.save(question="Test", answer="Answer")

        assert path.exists()
        assert (wiki_dir / "queries").exists()

    @patch("wiki_engine.query_saver.datetime")
    def test_save_rebuilds_index(self, mock_dt, tmp_wiki):
        """Saving query rebuilds wiki index by default."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"
        saver = QuerySaver(wiki_dir=str(tmp_wiki))
        saver.save(question="Q", answer="A")

        index_path = tmp_wiki / "index.md"
        assert index_path.exists()

    @patch("wiki_engine.query_saver.datetime")
    def test_save_calls_auto_commit_when_enabled(self, mock_dt, tmp_wiki):
        """Saving query triggers auto-commit when enabled."""
        mock_dt.now.return_value.strftime.return_value = "2026-04-15"
        mock_git_manager = MagicMock()
        mock_git_manager.auto_commit.return_value = True

        saver = QuerySaver(
            wiki_dir=str(tmp_wiki),
            git_manager=mock_git_manager,
            auto_commit=True,
        )
        saver.save(question="Q", answer="A")

        mock_git_manager.auto_commit.assert_called_once()
