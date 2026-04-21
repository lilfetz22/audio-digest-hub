"""Git hooks — auto-commit wiki changes after writes."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class WikiGitManager:
    """Manages git operations for wiki auto-commits."""

    def __init__(self, repo_root: str, wiki_dir: str):
        self.repo_root = Path(repo_root)
        self.wiki_dir = Path(wiki_dir)

    def auto_commit(self, message: str = "wiki: auto-update") -> bool:
        """Stage all wiki changes and commit.

        Args:
            message: Commit message.

        Returns:
            True if a commit was made, False if nothing to commit.
        """
        try:
            # Stage wiki directory changes
            wiki_rel = self.wiki_dir.relative_to(self.repo_root)
            self._run_git(["add", str(wiki_rel)])

            # Check if there are staged changes
            result = self._run_git(["diff", "--cached", "--quiet"], check=False)
            if result.returncode == 0:
                logger.info("No wiki changes to commit")
                return False

            # Commit
            self._run_git(["commit", "-m", message])
            logger.info(f"Wiki auto-committed: {message}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git auto-commit failed: {e}")
            return False

    def has_changes(self) -> bool:
        """Check if there are uncommitted wiki changes."""
        try:
            wiki_rel = self.wiki_dir.relative_to(self.repo_root)
            result = self._run_git(
                ["status", "--porcelain", str(wiki_rel)],
                check=False,
            )
            return bool(result.stdout.strip())
        except Exception:
            logger.warning("has_changes() failed — assuming no changes", exc_info=True)
            return False

    def _run_git(self, args: list, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the repo root."""
        cmd = ["git"] + args
        return subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=check,
            timeout=30,
        )
