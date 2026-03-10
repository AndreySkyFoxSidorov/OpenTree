"""
Commit graph visualization for OpenTree.

Builds and renders a compact lane graph from commit history.
"""

from dataclasses import dataclass
from typing import Optional

from opentree.core.models import CommitInfo


# Graph symbols
SYM_COMMIT = "●"
SYM_VERTICAL = "│"
SYM_BRANCH_RIGHT = "├"
SYM_BRANCH_LEFT = "┤"
SYM_MERGE_DOWN = "┬"
SYM_CORNER_DOWN_RIGHT = "┐"
SYM_CORNER_DOWN_LEFT = "┌"
SYM_CORNER_UP_RIGHT = "┘"
SYM_CORNER_UP_LEFT = "└"
SYM_CROSS = "┼"
SYM_HORIZONTAL = "─"
SYM_SPACE = " "


@dataclass
class GraphNode:
    """Represents a single node in the commit graph."""
    
    commit_hash: str
    lane: int  # Column position (0-based)
    parents: list[str]
    is_merge: bool = False  # Has multiple parents
    
    # Connection directions
    connects_up: bool = True
    connects_down: bool = True
    
    # Lanes that pass through this row
    pass_through_lanes: list[int] = None
    
    # Merge lines to draw
    merge_from_lanes: list[int] = None  # For merge commits
    branch_to_lanes: list[int] = None   # For branches going right
    fold_lanes: list[tuple[int, int]] = None  # Active lanes that fold left on this row


_MAIN_BRANCH_NAMES = {"main", "master", "trunk"}


def _normalize_ref(ref: str) -> str:
    """Normalize a ref decoration to a branch-like name."""
    ref = ref.strip()
    if ref.startswith("tag:"):
        return ""
    if "->" in ref:
        ref = ref.split("->", 1)[1].strip()
    return ref


def _has_main_ref(commit: CommitInfo) -> bool:
    """Check whether a commit is decorated as the main branch tip."""
    for ref in commit.refs:
        name = _normalize_ref(ref)
        if not name:
            continue
        if name in _MAIN_BRANCH_NAMES:
            return True
        if "/" in name and name.split("/")[-1] in _MAIN_BRANCH_NAMES:
            return True
    return False


def _preferred_lanes(commits: list[CommitInfo]) -> dict[str, int]:
    """Compute preferred lane depth for each commit hash."""
    preferred: dict[str, int] = {}

    for commit in commits:
        if commit.hash and _has_main_ref(commit):
            preferred[commit.hash] = 0

    if not preferred:
        first_commit = next((commit for commit in commits if commit.hash), None)
        if first_commit:
            preferred[first_commit.hash] = 0

    for commit in commits:
        if not commit.hash:
            continue
        current_lane = preferred.get(commit.hash, 0)
        if not commit.parents:
            continue

        first_parent = commit.parents[0]
        previous = preferred.get(first_parent)
        if previous is None or current_lane < previous:
            preferred[first_parent] = current_lane

        for offset, parent in enumerate(commit.parents[1:], start=1):
            lane = current_lane + offset
            previous = preferred.get(parent)
            if previous is None or lane < previous:
                preferred[parent] = lane

    return preferred


def _allocate_lane(active_lanes: dict[str, int], preferred_lane: int = 0, min_lane: int = 0, exclude_hash: Optional[str] = None) -> int:
    """Find the next free lane while keeping important lanes left-biased."""
    used = {lane for commit_hash, lane in active_lanes.items() if commit_hash != exclude_hash}
    lane = max(preferred_lane, min_lane)
    while lane in used:
        lane += 1
    return lane


def build_graph(commits: list[CommitInfo]) -> list[GraphNode]:
    """
    Build the graph structure from a list of commits.
    
    Assigns each commit to a lane and tracks parent relationships.
    """
    if not commits:
        return []

    nodes: list[GraphNode] = []
    active_lanes: dict[str, int] = {}
    preferred_lanes = _preferred_lanes([commit for commit in commits if commit.hash])

    for commit in commits:
        if not commit.hash:
            continue

        if commit.hash in active_lanes:
            lane = active_lanes.pop(commit.hash)
        else:
            lane = _allocate_lane(active_lanes, preferred_lanes.get(commit.hash, 0))

        pass_through = sorted(set(active_lanes.values()))
        is_merge = len(commit.parents) > 1
        merge_from = []
        branch_to = []
        fold_lanes = []

        if commit.parents:
            first_parent = commit.parents[0]
            first_parent_lane = active_lanes.get(first_parent)
            desired_lane = preferred_lanes.get(first_parent, preferred_lanes.get(commit.hash, lane))

            if first_parent_lane is None:
                first_parent_lane = _allocate_lane(active_lanes, desired_lane)
                active_lanes[first_parent] = first_parent_lane
            else:
                better_lane = _allocate_lane(active_lanes, desired_lane, exclude_hash=first_parent)
                if better_lane < first_parent_lane:
                    fold_lanes.append((first_parent_lane, better_lane))
                    active_lanes[first_parent] = better_lane
                    first_parent_lane = better_lane

            if first_parent_lane != lane:
                branch_to.append(first_parent_lane)

            for offset, parent in enumerate(commit.parents[1:], start=1):
                parent_lane = active_lanes.get(parent)
                desired_lane = max(
                    preferred_lanes.get(parent, preferred_lanes.get(commit.hash, lane) + offset),
                    lane + 1,
                )
                if parent_lane is None:
                    parent_lane = _allocate_lane(active_lanes, desired_lane, min_lane=lane + 1)
                    active_lanes[parent] = parent_lane
                else:
                    better_lane = _allocate_lane(active_lanes, desired_lane, min_lane=lane + 1, exclude_hash=parent)
                    if better_lane < parent_lane:
                        fold_lanes.append((parent_lane, better_lane))
                        active_lanes[parent] = better_lane
                        parent_lane = better_lane
                merge_from.append(parent_lane)

        node = GraphNode(
            commit_hash=commit.hash,
            lane=lane,
            parents=commit.parents,
            is_merge=is_merge,
            connects_up=True,
            connects_down=len(commit.parents) > 0,
            pass_through_lanes=pass_through if pass_through else None,
            merge_from_lanes=merge_from if merge_from else None,
            branch_to_lanes=branch_to if branch_to else None,
            fold_lanes=fold_lanes if fold_lanes else None,
        )
        nodes.append(node)

    return nodes


def render_graph_line(node: GraphNode, max_lanes: int = 8) -> str:
    """
    Render a single line of the graph as text.
    
    Returns a string representation of the graph for this commit.
    """
    max_lanes = min(max_lanes, 12)
    line = [SYM_SPACE] * max_lanes
    
    # Draw pass-through lanes
    if node.pass_through_lanes:
        for l in node.pass_through_lanes:
            if l < max_lanes:
                line[l] = SYM_VERTICAL
    
    # Draw merge lines
    if node.merge_from_lanes:
        for ml in node.merge_from_lanes:
            if ml < max_lanes and node.lane < max_lanes:
                # Draw horizontal connection
                start, end = min(node.lane, ml), max(node.lane, ml)
                for i in range(start + 1, end):
                    if i < max_lanes:
                        if line[i] == SYM_VERTICAL:
                            line[i] = SYM_CROSS
                        else:
                            line[i] = SYM_HORIZONTAL
    
    # Draw the commit point
    if node.lane < max_lanes:
        line[node.lane] = SYM_COMMIT
    
    return "".join(line)


def get_lane_color_index(lane: int) -> int:
    """Get color index for a lane (for theming)."""
    return lane % 8
