"""
OpenTree Utils Package.

Utility functions for paths, text processing, and platform operations.
"""

from opentree.utils.paths import (
    get_config_dir,
    get_cache_dir,
    find_repo_root,
    is_valid_repo,
    normalize_path,
)
from opentree.utils.text import (
    safe_decode,
    truncate,
    format_timestamp,
    format_bytes,
    first_line,
    word_wrap,
)
from opentree.utils.platform import (
    is_git_available,
    get_git_version,
    reveal_in_explorer,
    open_file,
    get_default_editor,
)

__all__ = [
    "get_config_dir",
    "get_cache_dir",
    "find_repo_root",
    "is_valid_repo",
    "normalize_path",
    "safe_decode",
    "truncate",
    "format_timestamp",
    "format_bytes",
    "first_line",
    "word_wrap",
    "is_git_available",
    "get_git_version",
    "reveal_in_explorer",
    "open_file",
    "get_default_editor",
]
