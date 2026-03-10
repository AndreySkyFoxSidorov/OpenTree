"""
Core domain models for OpenTree.

Data classes representing the main entities used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class FileStatusKind(Enum):
    """Type of file status change."""

    UNTRACKED = "?"
    IGNORED = "!"
    MODIFIED = "M"
    ADDED = "A"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNMERGED = "U"


@dataclass
class FileStatus:
    """
    Represents the status of a single file in the repository.

    Tracks both staged and unstaged changes.
    """

    path: str
    staged_status: Optional[str] = None
    unstaged_status: Optional[str] = None
    original_path: Optional[str] = None

    @property
    def kind(self) -> FileStatusKind:
        """Get the primary status kind."""
        status = self.staged_status or self.unstaged_status or "?"
        try:
            return FileStatusKind(status)
        except ValueError:
            return FileStatusKind.MODIFIED

    @property
    def is_staged(self) -> bool:
        """Check if file has staged changes."""
        return self.staged_status is not None and self.staged_status != " "

    @property
    def is_unstaged(self) -> bool:
        """Check if file has unstaged changes."""
        return self.unstaged_status is not None and self.unstaged_status != " "

    @property
    def display_name(self) -> str:
        """Get display name for the file."""
        if self.original_path:
            return f"{self.original_path} -> {self.path}"
        return self.path


@dataclass
class CommitInfo:
    """
    Information about a single commit.
    """

    hash: str
    short_hash: str
    author: str
    email: str
    date: datetime
    subject: str
    body: str = ""
    refs: list[str] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    graph: str = ""

    @property
    def display_date(self) -> str:
        """Format date for display."""
        return self.date.strftime("%Y-%m-%d %H:%M")


@dataclass
class BranchInfo:
    """
    Information about a branch.
    """

    name: str
    is_current: bool = False
    is_remote: bool = False
    tracking: Optional[str] = None
    ahead: int = 0
    behind: int = 0

    @property
    def display_name(self) -> str:
        """Get display name with tracking info."""
        if self.ahead or self.behind:
            parts = []
            if self.ahead:
                parts.append(f"↑{self.ahead}")
            if self.behind:
                parts.append(f"↓{self.behind}")
            return f"{self.name} [{' '.join(parts)}]"
        return self.name


@dataclass
class TagInfo:
    """
    Information about a tag.
    """

    name: str
    target: str = ""
    subject: str = ""
    date: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        """Get tag display name."""
        if self.subject:
            return f"{self.name} - {self.subject}"
        return self.name


@dataclass
class RemoteInfo:
    """
    Information about a remote repository.
    """

    name: str
    url: str
    fetch_url: Optional[str] = None
    push_url: Optional[str] = None


@dataclass
class StashInfo:
    """
    Information about a stash entry.
    """

    index: int
    message: str
    branch: Optional[str] = None


@dataclass
class RepoInfo:
    """
    Information about a repository.
    """

    path: Path
    commits: list[CommitInfo] = field(default_factory=list)
    branches: list[BranchInfo] = field(default_factory=list)
    tags: list[TagInfo] = field(default_factory=list)
    remotes: list[RemoteInfo] = field(default_factory=list)
    stashes: list[StashInfo] = field(default_factory=list)

    @property
    def name(self) -> str:
        """Get repository name from path."""
        return self.path.name

    @property
    def current_branch(self) -> Optional[BranchInfo]:
        """Get the current branch."""
        for branch in self.branches:
            if branch.is_current:
                return branch
        return None


@dataclass
class CommandResult:
    """
    Result of running a git command.
    """

    success: bool
    stdout: str
    stderr: str
    return_code: int
    command: str = ""
