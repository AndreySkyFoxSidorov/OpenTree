"""
Theme definitions for OpenTree.

Provides color palettes for Light, Dark, Tokyo Light, and Tokyo Dark themes.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ThemeColors:
    """Complete color palette for a theme."""
    
    # Main colors
    bg: str              # Main background
    bg_alt: str          # Alternative background (panels, frames)
    fg: str              # Main text color
    fg_dim: str          # Dimmed text
    
    # Accent colors
    accent: str          # Primary accent (buttons, links)
    accent_fg: str       # Text on accent background
    
    # Selection
    select_bg: str       # Selection background
    select_fg: str       # Selection text
    
    # Borders
    border: str          # Border color
    
    # Diff colors
    diff_add_bg: str     # Added line background
    diff_add_fg: str     # Added line text
    diff_del_bg: str     # Deleted line background
    diff_del_fg: str     # Deleted line text
    diff_hunk_bg: str    # Hunk header background
    diff_hunk_fg: str    # Hunk header text
    diff_header_bg: str  # Diff header background
    diff_header_fg: str  # Diff header text
    
    # Status colors
    status_modified: str
    status_added: str
    status_deleted: str
    status_renamed: str
    status_untracked: str
    status_conflict: str
    
    # Graph colors (for branch visualization)
    graph_colors: tuple


# ============================================================================
# THEME DEFINITIONS
# ============================================================================

THEME_LIGHT = ThemeColors(
    bg="#ffffff",
    bg_alt="#f6f8fa",
    fg="#24292e",
    fg_dim="#6a737d",
    
    accent="#0366d6",
    accent_fg="#ffffff",
    
    select_bg="#0366d6",
    select_fg="#ffffff",
    
    border="#e1e4e8",
    
    diff_add_bg="#e6ffec",
    diff_add_fg="#22863a",
    diff_del_bg="#ffebe9",
    diff_del_fg="#cb2431",
    diff_hunk_bg="#f1f8ff",
    diff_hunk_fg="#0366d6",
    diff_header_bg="#fafbfc",
    diff_header_fg="#586069",
    
    status_modified="#d68000",
    status_added="#22863a",
    status_deleted="#cb2431",
    status_renamed="#6f42c1",
    status_untracked="#586069",
    status_conflict="#cb2431",
    
    graph_colors=(
        "#0366d6",  # Blue
        "#28a745",  # Green
        "#d73a49",  # Red
        "#6f42c1",  # Purple
        "#f66a0a",  # Orange
        "#0598bc",  # Cyan
        "#ea4aaa",  # Pink
        "#735c0f",  # Brown
    ),
)


THEME_DARK = ThemeColors(
    bg="#1e1e1e",
    bg_alt="#252526",
    fg="#d4d4d4",
    fg_dim="#808080",
    
    accent="#0e639c",
    accent_fg="#ffffff",
    
    select_bg="#094771",
    select_fg="#ffffff",
    
    border="#3c3c3c",
    
    diff_add_bg="#2d4a3e",
    diff_add_fg="#89d185",
    diff_del_bg="#4a2d2d",
    diff_del_fg="#f48771",
    diff_hunk_bg="#2d3748",
    diff_hunk_fg="#79b8ff",
    diff_header_bg="#2d2d2d",
    diff_header_fg="#9da5b4",
    
    status_modified="#dcdcaa",
    status_added="#89d185",
    status_deleted="#f48771",
    status_renamed="#c586c0",
    status_untracked="#808080",
    status_conflict="#f48771",
    
    graph_colors=(
        "#569cd6",  # Blue
        "#6a9955",  # Green
        "#f14c4c",  # Red
        "#c586c0",  # Purple
        "#ce9178",  # Orange
        "#4ec9b0",  # Cyan
        "#d16d9e",  # Pink
        "#d7ba7d",  # Brown
    ),
)


THEME_TOKYO_LIGHT = ThemeColors(
    bg="#d5d6db",
    bg_alt="#cbccd1",
    fg="#343b58",
    fg_dim="#6a6e85",
    
    accent="#34548a",
    accent_fg="#ffffff",
    
    select_bg="#99a7df",
    select_fg="#343b58",
    
    border="#9699a3",
    
    diff_add_bg="#c3e88d30",
    diff_add_fg="#485e30",
    diff_del_bg="#ff757f30",
    diff_del_fg="#8c4351",
    diff_hunk_bg="#7aa2f7",
    diff_hunk_fg="#343b58",
    diff_header_bg="#c4c8da",
    diff_header_fg="#5a5a72",
    
    status_modified="#8f5e15",
    status_added="#485e30",
    status_deleted="#8c4351",
    status_renamed="#5a4a78",
    status_untracked="#6a6e85",
    status_conflict="#8c4351",
    
    graph_colors=(
        "#34548a",  # Blue
        "#485e30",  # Green
        "#8c4351",  # Red
        "#5a4a78",  # Purple
        "#8f5e15",  # Orange
        "#166775",  # Cyan
        "#9854f1",  # Pink
        "#634f30",  # Brown
    ),
)


THEME_TOKYO_DARK = ThemeColors(
    bg="#1a1b26",
    bg_alt="#16161e",
    fg="#a9b1d6",
    fg_dim="#565f89",
    
    accent="#7aa2f7",
    accent_fg="#1a1b26",
    
    select_bg="#33467c",
    select_fg="#c0caf5",
    
    border="#292e42",
    
    diff_add_bg="#20303b",
    diff_add_fg="#9ece6a",
    diff_del_bg="#37222c",
    diff_del_fg="#f7768e",
    diff_hunk_bg="#1f2335",
    diff_hunk_fg="#7aa2f7",
    diff_header_bg="#1f2335",
    diff_header_fg="#565f89",
    
    status_modified="#e0af68",
    status_added="#9ece6a",
    status_deleted="#f7768e",
    status_renamed="#bb9af7",
    status_untracked="#565f89",
    status_conflict="#f7768e",
    
    graph_colors=(
        "#7aa2f7",  # Blue
        "#9ece6a",  # Green
        "#f7768e",  # Red
        "#bb9af7",  # Purple
        "#e0af68",  # Orange
        "#7dcfff",  # Cyan
        "#ff007c",  # Pink
        "#c0caf5",  # Light
    ),
)


# Theme registry
THEMES: Dict[str, ThemeColors] = {
    "light": THEME_LIGHT,
    "dark": THEME_DARK,
    "tokyo_light": THEME_TOKYO_LIGHT,
    "tokyo_dark": THEME_TOKYO_DARK,
}


def get_theme(name: str) -> ThemeColors:
    """Get theme colors by name."""
    return THEMES.get(name, THEME_LIGHT)
