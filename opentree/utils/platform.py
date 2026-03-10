"""
Platform-specific utilities for OpenTree.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def is_git_available(git_path: str = "git") -> bool:
    """Check if git is available on the system."""
    # Ignore git_path, use our wrapper which knows where gitx and git are
    from opentree.git.wrapper import run_git_capture
    result = run_git_capture(["--version"], timeout=5)
    return result.success


def get_git_version(git_path: str = "git") -> Optional[str]:
    """Get the version of git installed."""
    from opentree.git.wrapper import run_git_capture
    result = run_git_capture(["--version"], timeout=5)
    if result.success:
        return result.stdout.strip()
    return None


def reveal_in_explorer(path: Path) -> None:
    """Reveal a file or folder in the system file explorer."""
    path = path.resolve()
    
    if sys.platform == "win32":
        if path.is_file():
            subprocess.run(["explorer", "/select,", str(path)])
        else:
            subprocess.run(["explorer", str(path)])
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)])
    else:
        # Linux - try xdg-open on parent directory
        if path.is_file():
            subprocess.run(["xdg-open", str(path.parent)])
        else:
            subprocess.run(["xdg-open", str(path)])


def open_file(path: Path) -> None:
    """Open a file with the default application."""
    path = path.resolve()
    
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])


def get_default_editor() -> Optional[str]:
    """Get the default text editor."""
    # Check common environment variables
    for var in ["VISUAL", "EDITOR"]:
        if editor := os.environ.get(var):
            return editor
    
    # Platform defaults
    if sys.platform == "win32":
        return "notepad"
    elif sys.platform == "darwin":
        return "open -e"
    else:
        return "nano"
