"""
Git executable wrapper.

Central place to locate and run git commands via gitx.py.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Union

from opentree.core.models import CommandResult


def get_gitx_path() -> Path:
    """Get the path to gitx.py script."""
    # Assuming gitx.py is in the parent directory of this file (opentree/git/../gitx.py)
    # i.e., opentree/gitx.py
    return Path(__file__).resolve().parent.parent / "gitx.py"


def get_git_command(args: List[str], password: str = "") -> List[str]:
    """
    Construct command list to run git via gitx.py.
    
    Args:
        args: List of git arguments (e.g. ["status", "-s"] or ["git", "status"])
              If args[0] is "git", it is removed.
        password: The password/passphrase to use for authentication. 
                  Defaults to empty string if not provided.
    """
    cmd_args = list(args)
    if cmd_args and cmd_args[0] == "git":
        cmd_args = cmd_args[1:]
        
    gitx_path = get_gitx_path()
    # [python, gitx.py, --password, <password>, --, <args>]
    return [sys.executable, str(gitx_path), "--password", password, "--"] + cmd_args


def run_git_capture(args: List[str], cwd: Optional[Union[str, Path]] = None, 
                   timeout: Optional[float] = None, env: Optional[dict] = None) -> CommandResult:
    """
    Run a git command synchronously using gitx.py and capture output.
    
    Acts like subprocess.run(..., capture_output=True, text=True).
    """
    full_cmd = get_git_command(args)
    
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
        
    try:
        # Use CREATE_NO_WINDOW on Windows to avoid flashing console
        creationflags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creationflags = subprocess.CREATE_NO_WINDOW
            
        process = subprocess.run(
            full_cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
            creationflags=creationflags,
            encoding='utf-8',
            errors='replace'
        )
        
        return CommandResult(
            success=process.returncode == 0,
            stdout=process.stdout,
            stderr=process.stderr,
            return_code=process.returncode,
            command="git " + " ".join(args)
        )
        
    except subprocess.TimeoutExpired:
        return CommandResult(
            success=False,
            stdout="",
            stderr="Command timed out",
            return_code=-1,
            command="git " + " ".join(args)
        )
    except Exception as e:
        return CommandResult(
            success=False,
            stdout="",
            stderr=str(e),
            return_code=-1,
            command="git " + " ".join(args)
        )
