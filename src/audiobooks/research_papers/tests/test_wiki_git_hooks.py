"""Tests for wiki git hooks (auto-commit)."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from wiki_engine.git_hooks import WikiGitManager


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path), capture_output=True, check=True,
    )
    # Create initial commit
    readme = tmp_path / "README.md"
    readme.write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path), capture_output=True, check=True,
    )
    return tmp_path


@pytest.fixture
def wiki_in_repo(git_repo):
    """Create a wiki directory inside the git repo."""
    wiki_dir = git_repo / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "concepts").mkdir()
    return wiki_dir


class TestWikiGitManager:
    """Tests for WikiGitManager."""

    def test_auto_commit_on_new_file(self, git_repo, wiki_in_repo):
        """Writing a new wiki file and calling auto_commit creates a commit."""
        # Write a file
        (wiki_in_repo / "concepts" / "test.md").write_text("# Test concept")

        manager = WikiGitManager(repo_root=str(git_repo), wiki_dir=str(wiki_in_repo))
        result = manager.auto_commit(message="wiki: added test concept")

        assert result is True

        # Verify commit exists
        log = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=str(git_repo),
            capture_output=True,
            text=True,
        )
        assert "wiki: added test concept" in log.stdout

    def test_auto_commit_no_changes(self, git_repo, wiki_in_repo):
        """auto_commit returns False when nothing to commit."""
        manager = WikiGitManager(repo_root=str(git_repo), wiki_dir=str(wiki_in_repo))
        result = manager.auto_commit()
        assert result is False

    def test_has_changes_detects_new_file(self, git_repo, wiki_in_repo):
        """has_changes returns True when wiki has untracked files."""
        (wiki_in_repo / "concepts" / "new.md").write_text("New content")

        manager = WikiGitManager(repo_root=str(git_repo), wiki_dir=str(wiki_in_repo))
        assert manager.has_changes() is True

    def test_has_changes_clean_repo(self, git_repo, wiki_in_repo):
        """has_changes returns False when no changes in wiki dir."""
        manager = WikiGitManager(repo_root=str(git_repo), wiki_dir=str(wiki_in_repo))
        assert manager.has_changes() is False

    def test_auto_commit_with_modified_file(self, git_repo, wiki_in_repo):
        """Modified files are committed."""
        # Create and commit a file first
        test_file = wiki_in_repo / "concepts" / "existing.md"
        test_file.write_text("Original content")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "add existing"],
            cwd=str(git_repo), capture_output=True, check=True,
        )

        # Modify the file
        test_file.write_text("Modified content")

        manager = WikiGitManager(repo_root=str(git_repo), wiki_dir=str(wiki_in_repo))
        result = manager.auto_commit(message="wiki: updated existing concept")

        assert result is True
