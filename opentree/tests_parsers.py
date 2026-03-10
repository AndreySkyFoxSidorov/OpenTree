"""
Unit tests for git parsers.

Run with: python -m opentree.tests_parsers
"""

import sys
from datetime import datetime

from opentree.core.models import CommitInfo, FileStatusKind
from opentree.git.parsers import (
    parse_branches,
    parse_log,
    parse_status_v2,
    parse_tags,
    split_status_by_kind,
)
from opentree.ui.graph import build_graph


def test_parse_status_modified():
    """Test parsing modified file status."""
    output = b"1 .M N... 100644 100644 100644 abc123 def456 src/main.py\0"

    result = parse_status_v2(output)

    assert len(result) == 1, f"Expected 1 file, got {len(result)}"
    assert result[0].path == "src/main.py", f"Wrong path: {result[0].path}"
    assert result[0].unstaged_status == "M", f"Wrong status: {result[0].unstaged_status}"
    print("[OK] test_parse_status_modified")


def test_parse_status_staged():
    """Test parsing staged file status."""
    output = b"1 M. N... 100644 100644 100644 abc123 def456 staged.py\0"

    result = parse_status_v2(output)

    assert len(result) == 1
    assert result[0].staged_status == "M"
    assert result[0].is_staged
    print("[OK] test_parse_status_staged")


def test_parse_status_untracked():
    """Test parsing untracked file status."""
    output = b"? new_file.py\0"

    result = parse_status_v2(output)

    assert len(result) == 1
    assert result[0].unstaged_status == "?"
    assert result[0].kind == FileStatusKind.UNTRACKED
    print("[OK] test_parse_status_untracked")


def test_split_status_by_kind():
    """Test splitting file statuses."""
    output = (
        b"1 M. N... 100644 100644 100644 a b staged.py\0"
        b"1 .M N... 100644 100644 100644 a b modified.py\0"
        b"? untracked.py\0"
    )

    files = parse_status_v2(output)
    staged, unstaged, untracked, conflicts = split_status_by_kind(files)

    assert len(staged) == 1, f"Expected 1 staged, got {len(staged)}"
    assert len(unstaged) == 1, f"Expected 1 unstaged, got {len(unstaged)}"
    assert len(untracked) == 1, f"Expected 1 untracked, got {len(untracked)}"
    assert len(conflicts) == 0, f"Expected 0 conflicts, got {len(conflicts)}"
    print("[OK] test_split_status_by_kind")


def test_parse_log_single():
    """Test parsing single commit log in current graph format."""
    output = (
        "* \x00\x1f\x00abc123\x00abc1\x00John Doe\x00john@example.com\x001704067200"
        "\x00Initial commit\x00Body text\x00HEAD -> main\x00parent1 parent2\x00\x1f\n"
    )

    result = parse_log(output)

    assert len(result) == 1
    assert result[0].hash == "abc123"
    assert result[0].author == "John Doe"
    assert result[0].subject == "Initial commit"
    assert result[0].refs == ["HEAD -> main"]
    assert result[0].parents == ["parent1", "parent2"]
    print("[OK] test_parse_log_single")


def test_parse_log_multiple():
    """Test parsing multiple commit logs with graph-only lines."""
    output = (
        "* \x00\x1f\x00abc123\x00abc1\x00John\x00j@e.com\x001704067200\x00First\x00\x00main\x00parent1\x00\x1f\n"
        "|\n"
        "* \x00\x1f\x00def456\x00def4\x00Jane\x00jane@e.com\x001704153600\x00Second\x00\x00origin/main\x00\x00\x1f\n"
    )

    result = parse_log(output)

    assert len(result) == 3
    assert result[0].short_hash == "abc1"
    assert result[1].hash == ""
    assert result[2].short_hash == "def4"
    print("[OK] test_parse_log_multiple")


def test_parse_branches_local_and_remote():
    """Test parsing local and remote branches with ahead/behind state."""
    output = (
        "*refs/heads/main|main|origin/main|ahead 2, behind 1|abc123|Latest commit\n"
        " refs/heads/feature/work|feature/work|origin/feature/work||def456|WIP\n"
        " refs/remotes/origin/main|origin/main|||abc123|Latest commit"
    )

    result = parse_branches(output)

    assert len(result) == 3
    assert result[0].name == "main"
    assert result[0].is_current
    assert result[0].ahead == 2
    assert result[0].behind == 1
    assert result[1].name == "feature/work"
    assert not result[1].is_remote
    assert result[2].name == "origin/main"
    assert result[2].is_remote
    print("[OK] test_parse_branches_local_and_remote")


def test_parse_tags():
    """Test parsing tags."""
    output = "v1.0.0|abc123|1704067200|Initial release\nbeta|def456||Preview build"

    result = parse_tags(output)

    assert len(result) == 2
    assert result[0].name == "v1.0.0"
    assert result[0].target == "abc123"
    assert result[0].subject == "Initial release"
    assert result[1].date is None
    print("[OK] test_parse_tags")


def test_build_graph_keeps_mainline_left():
    """Mainline commits should stay in the left-most lane after a merge."""
    commits = [
        CommitInfo("merge", "merge", "A", "a@e.com", datetime.now(), "Merge", refs=["HEAD -> main"], parents=["main-2", "feat-2"]),
        CommitInfo("feat-2", "feat-2", "A", "a@e.com", datetime.now(), "Feature 2", parents=["base"]),
        CommitInfo("main-2", "main-2", "A", "a@e.com", datetime.now(), "Main 2", parents=["base"]),
        CommitInfo("base", "base", "A", "a@e.com", datetime.now(), "Base", parents=["root"]),
        CommitInfo("root", "root", "A", "a@e.com", datetime.now(), "Root", parents=[]),
    ]

    nodes = build_graph(commits)
    lanes = {node.commit_hash: node.lane for node in nodes}

    assert lanes["merge"] == 0
    assert lanes["main-2"] == 0
    assert lanes["base"] == 0
    assert lanes["feat-2"] > lanes["main-2"]
    print("[OK] test_build_graph_keeps_mainline_left")


def test_build_graph_reuses_branch_lanes():
    """Side lanes should be reused instead of growing forever."""
    commits = [
        CommitInfo("merge-2", "merge-2", "A", "a@e.com", datetime.now(), "Merge 2", refs=["HEAD -> main"], parents=["main-3", "feat-4"]),
        CommitInfo("feat-4", "feat-4", "A", "a@e.com", datetime.now(), "Feature 4", parents=["feat-3"]),
        CommitInfo("feat-3", "feat-3", "A", "a@e.com", datetime.now(), "Feature 3", parents=["main-2"]),
        CommitInfo("main-3", "main-3", "A", "a@e.com", datetime.now(), "Main 3", parents=["merge-1"]),
        CommitInfo("merge-1", "merge-1", "A", "a@e.com", datetime.now(), "Merge 1", parents=["main-1", "feat-2"]),
        CommitInfo("feat-2", "feat-2", "A", "a@e.com", datetime.now(), "Feature 2", parents=["feat-1"]),
        CommitInfo("feat-1", "feat-1", "A", "a@e.com", datetime.now(), "Feature 1", parents=["main-1"]),
        CommitInfo("main-2", "main-2", "A", "a@e.com", datetime.now(), "Main 2", parents=["main-1"]),
        CommitInfo("main-1", "main-1", "A", "a@e.com", datetime.now(), "Main 1", parents=["root"]),
        CommitInfo("root", "root", "A", "a@e.com", datetime.now(), "Root", parents=[]),
    ]

    nodes = build_graph(commits)
    max_lane = max(node.lane for node in nodes)

    assert max_lane <= 2, f"Expected compact graph, got max lane {max_lane}"
    print("[OK] test_build_graph_reuses_branch_lanes")


def run_all_tests():
    """Run all unit tests."""
    print("=" * 50)
    print("Running OpenTree Parser Tests")
    print("=" * 50)

    tests = [
        test_parse_status_modified,
        test_parse_status_staged,
        test_parse_status_untracked,
        test_split_status_by_kind,
        test_parse_log_single,
        test_parse_log_multiple,
        test_parse_branches_local_and_remote,
        test_parse_tags,
        test_build_graph_keeps_mainline_left,
        test_build_graph_reuses_branch_lanes,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as exc:
            print(f"[FAIL] {test.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"[FAIL] {test.__name__}: {type(exc).__name__}: {exc}")
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
