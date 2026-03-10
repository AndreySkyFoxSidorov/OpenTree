"""
OpenTree Core Package.

Contains core domain models, state management, and event system.
"""

from opentree.core.models import (
    FileStatus,
    FileStatusKind,
    CommitInfo,
    BranchInfo,
    RemoteInfo,
    StashInfo,
    RepoInfo,
    CommandResult,
)
from opentree.core.events import events, Events, EventBus
from opentree.core.state import AppState

__all__ = [
    "FileStatus",
    "FileStatusKind",
    "CommitInfo",
    "BranchInfo",
    "RemoteInfo",
    "StashInfo",
    "RepoInfo",
    "CommandResult",
    "events",
    "Events",
    "EventBus",
    "AppState",
]
