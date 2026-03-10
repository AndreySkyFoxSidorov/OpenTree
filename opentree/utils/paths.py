"""
Path utilities for OpenTree.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def get_config_dir() -> Path:
    """
    Get the configuration directory for OpenTree.
    
    Returns the application root directory where gitx.py and localization.csv are located.
    """
    # Return the parent directory of this file (utils/paths.py) -> opentree/utils -> opentree
    # Actually, gitx.py is in opentree/, so we need opentree/utils/.. -> opentree
    return Path(__file__).parent.parent


def get_cache_dir() -> Path:
    """
    Get the cache directory for OpenTree.
    
    Returns platform-specific cache directory.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return base / "OpenTree" / "cache"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "OpenTree"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / "opentree"


def find_repo_root(path: Path) -> Optional[Path]:
    """
    Find the root of a git repository.
    
    Searches upward from the given path for a .git directory.
    Returns None if not in a git repository.
    """
    current = path.resolve()
    
    # If it's a file, start from its directory
    if current.is_file():
        current = current.parent
    
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    
    # Check root directory
    if (current / ".git").exists():
        return current
    
    return None


def is_valid_repo(path: Path) -> bool:
    """Check if a path is a valid git repository."""
    return find_repo_root(path) is not None


def normalize_path(path: str | Path) -> Path:
    """Normalize a path for the current platform."""
    return Path(path).resolve()
