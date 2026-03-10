"""
Git command builders.

Functions that generate git command argument lists.
"""

from pathlib import Path
from typing import Optional


def cmd_status() -> list[str]:
    """Get status command arguments."""
    return ["git", "status", "--porcelain=v2", "-z"]


def cmd_log(
    count: int = 100,
    all_branches: bool = False,
    author: Optional[str] = None,
    grep: Optional[str] = None,
) -> list[str]:
    """Get log command arguments."""
    marker = "%x00%x1f%x00"
    args = [
        "git",
        "log",
        "--graph",
        f"-n{count}",
        f"--format={marker}%H%x00%h%x00%an%x00%ae%x00%at%x00%s%x00%b%x00%D%x00%P%x00%x1f",
    ]
    if all_branches:
        args.append("--all")
    if author:
        args.append(f"--author={author}")
    if grep:
        args.append(f"--grep={grep}")
        args.append("--regexp-ignore-case")
    return args


def cmd_diff(path: Optional[str] = None, staged: bool = False) -> list[str]:
    """Get diff command arguments."""
    args = ["git", "diff"]
    if staged:
        args.append("--cached")
    if path:
        args.extend(["--", path])
    return args


def cmd_show(commit: str, stat_only: bool = False, patch_only: bool = False) -> list[str]:
    """Get show command arguments."""
    args = ["git", "show", commit]
    if stat_only:
        args.append("--stat")
    elif patch_only:
        args.extend(["--format=", "-p"])
    return args


def cmd_add(paths: list[str]) -> list[str]:
    """Get add command arguments."""
    return ["git", "add", "--"] + paths


def cmd_restore(paths: list[str]) -> list[str]:
    """Get restore command arguments (discard changes)."""
    return ["git", "restore", "--"] + paths


def cmd_clean(paths: list[str]) -> list[str]:
    """Get clean command arguments for removing untracked paths."""
    return ["git", "clean", "-fd", "--"] + paths


def cmd_restore_staged(paths: list[str]) -> list[str]:
    """Get restore --staged command arguments (unstage)."""
    return ["git", "restore", "--staged", "--"] + paths


def cmd_commit(message_file: Path) -> list[str]:
    """Get commit command arguments."""
    return ["git", "commit", "-F", str(message_file)]


def cmd_branch_list() -> list[str]:
    """Get branch list command arguments."""
    return [
        "git",
        "branch",
        "-a",
        "-v",
        "--format=%(HEAD)%(refname)|%(refname:short)|%(upstream:short)|%(upstream:track,nobracket)|%(objectname:short)|%(subject)",
    ]


def cmd_checkout(ref: str) -> list[str]:
    """Get checkout command arguments."""
    return ["git", "checkout", ref]


def cmd_checkout_track(remote_ref: str) -> list[str]:
    """Get checkout command arguments for creating a local tracking branch."""
    return ["git", "checkout", "--track", remote_ref]


def cmd_new_branch(name: str, checkout: bool = True, start_point: Optional[str] = None) -> list[str]:
    """Get new branch command arguments."""
    if checkout:
        args = ["git", "checkout", "-b", name]
    else:
        args = ["git", "branch", name]
    if start_point:
        args.append(start_point)
    return args


def cmd_delete_branch(name: str, force: bool = False) -> list[str]:
    """Get delete branch command arguments."""
    flag = "-D" if force else "-d"
    return ["git", "branch", flag, name]


def cmd_fetch(remote: Optional[str] = None, prune: bool = True) -> list[str]:
    """Get fetch command arguments."""
    args = ["git", "fetch"]
    if prune:
        args.append("--prune")
    if remote:
        args.append(remote)
    else:
        args.append("--all")
    return args


def cmd_pull(remote: Optional[str] = None, branch: Optional[str] = None, rebase: bool = False) -> list[str]:
    """Get pull command arguments."""
    args = ["git", "pull"]
    if rebase:
        args.append("--rebase")
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)
    return args


def cmd_push(
    remote: Optional[str] = None,
    branch: Optional[str] = None,
    set_upstream: bool = False,
    force: bool = False,
) -> list[str]:
    """Get push command arguments."""
    args = ["git", "push"]
    if set_upstream:
        args.append("-u")
    if force:
        args.append("--force-with-lease")
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)
    return args


def cmd_stash_list() -> list[str]:
    """Get stash list command arguments."""
    return ["git", "stash", "list", "--format=%gd|%s"]


def cmd_stash_push(message: Optional[str] = None) -> list[str]:
    """Get stash push command arguments."""
    args = ["git", "stash", "push"]
    if message:
        args.extend(["-m", message])
    return args


def cmd_stash_pop(index: int = 0) -> list[str]:
    """Get stash pop command arguments."""
    return ["git", "stash", "pop", f"stash@{{{index}}}"]


def cmd_stash_apply(index: int = 0) -> list[str]:
    """Get stash apply command arguments."""
    return ["git", "stash", "apply", f"stash@{{{index}}}"]


def cmd_stash_drop(index: int = 0) -> list[str]:
    """Get stash drop command arguments."""
    return ["git", "stash", "drop", f"stash@{{{index}}}"]


def cmd_merge(branch: str, squash: bool = False, no_commit: bool = False) -> list[str]:
    """Get merge command arguments."""
    args = ["git", "merge", branch]
    if squash:
        args.append("--squash")
    if no_commit:
        args.append("--no-commit")
    return args


def cmd_tag_list() -> list[str]:
    """Get tag list command arguments."""
    return [
        "git",
        "for-each-ref",
        "refs/tags",
        "--sort=-creatordate",
        "--format=%(refname:short)|%(objectname:short)|%(creatordate:unix)|%(subject)",
    ]


def cmd_create_tag(
    name: str,
    target: str = "HEAD",
    message: Optional[str] = None,
    force: bool = False,
) -> list[str]:
    """Get create tag command arguments."""
    args = ["git", "tag"]
    if force:
        args.append("--force")
    if message:
        args.extend(["-a", "-m", message, name, target])
    else:
        args.extend([name, target])
    return args


def cmd_delete_tag(name: str) -> list[str]:
    """Get delete tag command arguments."""
    return ["git", "tag", "-d", name]


def cmd_cherry_pick(commit: str) -> list[str]:
    """Get cherry-pick command arguments."""
    return ["git", "cherry-pick", commit]


def cmd_revert(commit: str) -> list[str]:
    """Get revert command arguments."""
    return ["git", "revert", "--no-edit", commit]


def cmd_reset(target: str, mode: str = "mixed") -> list[str]:
    """Get reset command arguments."""
    flag = {
        "soft": "--soft",
        "mixed": "--mixed",
        "hard": "--hard",
    }.get(mode, "--mixed")
    return ["git", "reset", flag, target]
