"""
Git output parsers.

Parse git command output into structured data.
"""

from datetime import datetime

from opentree.core.models import BranchInfo, CommitInfo, FileStatus, StashInfo, TagInfo
from opentree.utils.text import safe_decode


def parse_stash_list(output: str) -> list[StashInfo]:
    """Parse git stash list output."""
    stashes = []

    if not output.strip():
        return stashes

    for line in output.strip().split("\n"):
        if not line.strip():
            continue

        parts = line.split("|", 1)
        if len(parts) < 2:
            continue

        ref_log = parts[0].strip()
        message = parts[1].strip()

        index = 0
        if "{" in ref_log and "}" in ref_log:
            try:
                index = int(ref_log.split("{", 1)[1].split("}", 1)[0])
            except ValueError:
                continue

        branch = None
        if "WIP on " in message:
            branch = message.split("WIP on ", 1)[1].split(":", 1)[0].strip()
        elif "On " in message:
            branch = message.split("On ", 1)[1].split(":", 1)[0].strip()

        stashes.append(StashInfo(index=index, message=message, branch=branch))

    return stashes


def parse_status_v2(output: bytes) -> list[FileStatus]:
    """
    Parse git status --porcelain=v2 -z output.
    """
    files = []
    text = safe_decode(output)

    if not text.strip():
        return files

    entries = text.split("\0")
    i = 0

    while i < len(entries):
        entry = entries[i]
        if not entry:
            i += 1
            continue

        if entry.startswith("1 "):
            parts = entry.split(" ", 8)
            if len(parts) >= 9:
                xy = parts[1]
                path = parts[8]
                staged = xy[0] if xy[0] != "." else None
                unstaged = xy[1] if xy[1] != "." else None
                files.append(FileStatus(path=path, staged_status=staged, unstaged_status=unstaged))
        elif entry.startswith("2 "):
            parts = entry.split(" ", 9)
            if len(parts) >= 10:
                xy = parts[1]
                rest = parts[9]
                if "\t" in rest:
                    path, orig_path = rest.split("\t", 1)
                else:
                    path = rest
                    i += 1
                    orig_path = entries[i] if i < len(entries) else ""
                staged = xy[0] if xy[0] != "." else None
                unstaged = xy[1] if xy[1] != "." else None
                files.append(
                    FileStatus(
                        path=path,
                        staged_status=staged,
                        unstaged_status=unstaged,
                        original_path=orig_path,
                    )
                )
        elif entry.startswith("u "):
            parts = entry.split(" ", 10)
            if len(parts) >= 11:
                path = parts[10]
                files.append(FileStatus(path=path, staged_status="U", unstaged_status="U"))
        elif entry.startswith("? "):
            files.append(FileStatus(path=entry[2:], unstaged_status="?"))
        elif entry.startswith("! "):
            files.append(FileStatus(path=entry[2:], unstaged_status="!"))

        i += 1

    return files


def split_status_by_kind(
    files: list[FileStatus],
) -> tuple[list[FileStatus], list[FileStatus], list[FileStatus], list[FileStatus]]:
    """Split file statuses by kind."""
    staged = []
    unstaged = []
    untracked = []
    conflicts = []

    for file_status in files:
        if file_status.staged_status == "U" or file_status.unstaged_status == "U":
            conflicts.append(file_status)
        elif file_status.unstaged_status == "?":
            untracked.append(file_status)
        else:
            if file_status.is_staged:
                staged.append(file_status)
            if file_status.is_unstaged:
                unstaged.append(file_status)

    return staged, unstaged, untracked, conflicts


def parse_log(output: str) -> list[CommitInfo]:
    """Parse git log output with graph."""
    commits = []

    if not output.strip():
        return commits

    marker = "\x00\x1f\x00"

    for line in output.splitlines():
        if not line:
            continue

        if marker not in line:
            commits.append(
                CommitInfo(
                    hash="",
                    short_hash="",
                    author="",
                    email="",
                    date=datetime.now(),
                    subject="",
                    body="",
                    graph=line.rstrip(),
                )
            )
            continue

        graph_part, data_part = line.split(marker, 1)
        if data_part.endswith("\x1f"):
            data_part = data_part[:-1]

        parts = data_part.split("\0")
        if len(parts) < 7:
            continue

        try:
            timestamp = int(parts[4]) if parts[4] else 0
            date = datetime.fromtimestamp(timestamp)
        except (ValueError, OSError):
            date = datetime.now()

        refs = [ref.strip() for ref in parts[7].split(",") if ref.strip()] if len(parts) > 7 and parts[7] else []
        parents = [parent.strip() for parent in parts[8].split() if parent.strip()] if len(parts) > 8 and parts[8] else []

        commits.append(
            CommitInfo(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                date=date,
                subject=parts[5],
                body=parts[6] if len(parts) > 6 else "",
                refs=refs,
                parents=parents,
                graph=graph_part.rstrip(),
            )
        )

    return commits


def parse_branches(output: str) -> list[BranchInfo]:
    """Parse branch list output."""
    branches = []

    for raw_line in output.strip().split("\n"):
        if not raw_line.strip():
            continue

        is_current = raw_line.startswith("*")
        line = raw_line[1:] if is_current else raw_line
        parts = line.split("|")

        if len(parts) < 2:
            continue

        full_name = parts[0].strip()
        short_name = parts[1].strip()
        tracking = parts[2].strip() if len(parts) > 2 else ""
        tracking_state = parts[3].strip() if len(parts) > 3 else ""

        ahead = 0
        behind = 0
        for chunk in tracking_state.split(","):
            item = chunk.strip()
            if item.startswith("ahead "):
                try:
                    ahead = int(item.split(" ", 1)[1])
                except ValueError:
                    ahead = 0
            elif item.startswith("behind "):
                try:
                    behind = int(item.split(" ", 1)[1])
                except ValueError:
                    behind = 0

        is_remote = full_name.startswith("refs/remotes/")
        if full_name.startswith("refs/heads/"):
            name = short_name
        elif full_name.startswith("refs/remotes/"):
            name = short_name
        else:
            name = short_name or full_name

        branches.append(
            BranchInfo(
                name=name,
                is_current=is_current,
                is_remote=is_remote,
                tracking=tracking or None,
                ahead=ahead,
                behind=behind,
            )
        )

    return branches


def parse_tags(output: str) -> list[TagInfo]:
    """Parse tag list output."""
    tags = []

    for line in output.strip().split("\n"):
        if not line.strip():
            continue

        parts = line.split("|", 3)
        name = parts[0].strip() if len(parts) > 0 else ""
        target = parts[1].strip() if len(parts) > 1 else ""
        timestamp = parts[2].strip() if len(parts) > 2 else ""
        subject = parts[3].strip() if len(parts) > 3 else ""

        date = None
        if timestamp:
            try:
                date = datetime.fromtimestamp(int(timestamp))
            except (ValueError, OSError):
                date = None

        if name:
            tags.append(TagInfo(name=name, target=target, subject=subject, date=date))

    return tags
