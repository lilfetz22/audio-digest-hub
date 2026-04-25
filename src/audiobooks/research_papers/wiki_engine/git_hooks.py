"""Git hooks — auto-commit wiki changes after writes."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WikiGitManager:
    """Manages git operations for wiki auto-commits.

    Supports two modes:

    **Legacy (non-submodule)**:
        ``repo_root`` is the parent repository root that *contains* ``wiki_dir``.
        ``parent_root`` should be ``None``.

    **Submodule**:
        ``repo_root`` is the wiki folder itself (the submodule's own git root).
        ``parent_root`` is the top-level repository root.
        After committing inside the submodule, the manager also advances the
        submodule pointer commit in the parent repository.
    """

    def __init__(
        self,
        repo_root: str,
        wiki_dir: str,
        parent_root: Optional[str] = None,
        branch: str = "main",
        auto_push: bool = False,
        push_parent: bool = False,
    ):
        self.repo_root = Path(repo_root)
        self.wiki_dir = Path(wiki_dir)
        self.parent_root = Path(parent_root) if parent_root else None
        self.branch = branch
        self.auto_push = auto_push
        self.push_parent = push_parent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def auto_commit(self, message: str = "wiki: auto-update") -> bool:
        """Stage and commit wiki changes, with optional submodule-pointer update.

        In submodule mode (``parent_root`` is set) this performs a two-step
        commit:

        1. Ensure the submodule is on ``self.branch`` (not detached HEAD), then
           commit the markdown changes inside the submodule repo
           (``cwd=self.repo_root``).
        2. Advance the submodule pointer commit in the parent repository
           (``cwd=self.parent_root``).

        If ``auto_push`` is ``True`` the submodule branch is pushed to
        ``origin`` after the submodule commit.

        Args:
            message: Commit message for the wiki content commit.

        Returns:
            True if at least one commit was made, False if there was nothing
            to commit.
        """
        try:
            # ── Step 1: commit inside the submodule / wiki repo ──────────────
            if self.parent_root is not None:
                # Submodule mode — repo_root IS the wiki folder.
                self._ensure_on_branch(cwd=self.repo_root)
                porcelain = self._run_git(
                    ["status", "--porcelain"], cwd=self.repo_root, check=False
                )
                if not porcelain.stdout.strip():
                    logger.info("No wiki changes to commit (submodule)")
                    return False
                self._run_git(["add", "."], cwd=self.repo_root)
            else:
                # Legacy mode — repo_root is the parent; add by relative path.
                wiki_rel = self.wiki_dir.relative_to(self.repo_root)
                porcelain = self._run_git(
                    ["status", "--porcelain", str(wiki_rel)],
                    cwd=self.repo_root,
                    check=False,
                )
                if not porcelain.stdout.strip():
                    logger.info("No wiki changes to commit (legacy)")
                    return False
                self._run_git(["add", str(wiki_rel)], cwd=self.repo_root)

            self._run_git(["commit", "-m", message], cwd=self.repo_root)
            logger.info(f"Wiki committed ({self.repo_root}): {message}")

            # ── Optional push of submodule branch ─────────────────────────────
            if self.auto_push and self.parent_root is not None:
                self._run_git(
                    ["push", "origin", self.branch], cwd=self.repo_root
                )
                logger.info(f"Wiki pushed to origin/{self.branch}")

            # ── Step 2: advance the submodule pointer in the parent repo ──────
            if self.parent_root is not None:
                submodule_rel = self.repo_root.relative_to(self.parent_root)
                parent_porcelain = self._run_git(
                    ["status", "--porcelain", str(submodule_rel)],
                    cwd=self.parent_root,
                    check=False,
                )
                if parent_porcelain.stdout.strip():
                    self._run_git(
                        ["add", str(submodule_rel)], cwd=self.parent_root
                    )
                    self._run_git(
                        ["commit", "-m", "chore: advance wiki submodule pointer"],
                        cwd=self.parent_root,
                    )
                    logger.info("Parent submodule pointer advanced")

                    # ── Optional push of parent pointer commit ─────────────────
                    if self.auto_push and self.push_parent:
                        self._run_git(["push"], cwd=self.parent_root)
                        logger.info("Parent submodule pointer pushed")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git auto-commit failed: {e}")
            return False

    def has_changes(self) -> bool:
        """Check if there are uncommitted wiki changes."""
        try:
            if self.parent_root is not None:
                # Submodule mode — check inside the submodule repo.
                result = self._run_git(
                    ["status", "--porcelain", "."],
                    cwd=self.repo_root,
                    check=False,
                )
            else:
                wiki_rel = self.wiki_dir.relative_to(self.repo_root)
                result = self._run_git(
                    ["status", "--porcelain", str(wiki_rel)],
                    cwd=self.repo_root,
                    check=False,
                )
            return bool(result.stdout.strip())
        except Exception:
            logger.warning("has_changes() failed — assuming no changes", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_on_branch(self, cwd: Path) -> None:
        """Guarantee the repo at *cwd* is on ``self.branch``, not detached HEAD.

        ``git symbolic-ref --short HEAD`` exits non-zero when HEAD is detached.
        In that case ``git checkout <branch>`` is run to reattach before any
        write operations so that new commits are not orphaned.
        """
        result = self._run_git(
            ["symbolic-ref", "--short", "HEAD"], cwd=cwd, check=False
        )
        if result.returncode != 0 or result.stdout.strip() != self.branch:
            logger.warning(
                "Wiki repo is not on branch '%s' (HEAD=%s) — checking out.",
                self.branch,
                result.stdout.strip() or "detached",
            )
            self._run_git(["checkout", self.branch], cwd=cwd)

    def _run_git(
        self, args: list, cwd: Optional[Path] = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command.

        Args:
            args:  Git sub-command and its arguments.
            cwd:   Working directory for the command.  Defaults to
                   ``self.repo_root`` for backward compatibility.
            check: Raise ``CalledProcessError`` on non-zero exit if ``True``.
        """
        cmd = ["git"] + args
        return subprocess.run(
            cmd,
            cwd=str(cwd if cwd is not None else self.repo_root),
            capture_output=True,
            text=True,
            check=check,
            timeout=30,
        )
