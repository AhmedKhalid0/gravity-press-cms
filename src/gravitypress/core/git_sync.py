"""Git version control automation, commit tracking, and diff generation engine."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GitCommitRecord:
    hash: str
    author: str
    date: str
    message: str
    relative_file: Optional[str] = None


class GitSyncEngine:
    """Automates Git operations for content files (atomic commits, revision history, diffs)."""

    def __init__(self, repo_path: str | Path = "."):
        self.repo_path = Path(repo_path).resolve()

    def _run_git(self, args: List[str]) -> tuple[int, str, str]:
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except FileNotFoundError:
            return 127, "", "git binary not found on system PATH"

    def is_git_repo(self) -> bool:
        code, out, _ = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return code == 0 and out == "true"

    def init_repo(self) -> bool:
        if not self.is_git_repo():
            code, _, _ = self._run_git(["init"])
            return code == 0
        return True

    def commit_file(self, file_path: str | Path, message: str, author_name: str = "GravityPress CMS") -> Optional[str]:
        """Stages and commits a single content file to Git."""
        if not self.is_git_repo():
            self.init_repo()

        p = Path(file_path)
        try:
            rel_path = p.relative_to(self.repo_path)
        except ValueError:
            rel_path = p

        # Stage file
        code_add, _, _ = self._run_git(["add", str(rel_path)])
        if code_add != 0:
            return None

        # Commit with custom message
        code_commit, out_commit, _ = self._run_git([
            "-c", f"user.name={author_name}",
            "-c", "user.email=bot@gravitypress.local",
            "commit",
            "-m", message,
            str(rel_path),
        ])

        if code_commit == 0:
            # Extract commit hash
            _, hash_out, _ = self._run_git(["rev-parse", "--short", "HEAD"])
            return hash_out
        return None

    def get_file_history(self, file_path: str | Path, max_count: int = 10) -> List[GitCommitRecord]:
        """Retrieves commit history for a specific content file."""
        if not self.is_git_repo():
            return []

        p = Path(file_path)
        try:
            rel_path = str(p.relative_to(self.repo_path))
        except ValueError:
            rel_path = str(p)

        code, out, _ = self._run_git([
            "log",
            f"-n{max_count}",
            "--pretty=format:%h|%an|%ad|%s",
            "--date=short",
            "--",
            rel_path,
        ])

        if code != 0 or not out:
            return []

        records = []
        for line in out.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                records.append(
                    GitCommitRecord(
                        hash=parts[0],
                        author=parts[1],
                        date=parts[2],
                        message=parts[3],
                        relative_file=rel_path,
                    )
                )
        return records

    def get_recent_commits(self, max_count: int = 10) -> List[GitCommitRecord]:
        """Retrieves recent repository-wide commits."""
        if not self.is_git_repo():
            return []

        code, out, _ = self._run_git([
            "log",
            f"-n{max_count}",
            "--pretty=format:%h|%an|%ad|%s",
            "--date=short",
        ])

        if code != 0 or not out:
            return []

        records = []
        for line in out.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                records.append(
                    GitCommitRecord(
                        hash=parts[0],
                        author=parts[1],
                        date=parts[2],
                        message=parts[3],
                    )
                )
        return records
