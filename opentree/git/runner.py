"""
Git command runner with async support.

Runs git commands in background threads with callbacks.
"""

import subprocess
import threading
import queue
import sys
import os
from pathlib import Path
from typing import Callable, Optional, Any
from dataclasses import dataclass

from opentree.core.models import CommandResult
from opentree.core.events import events, Events
from opentree.utils.text import safe_decode


@dataclass
class QueuedCommand:
    """A command waiting to be executed."""
    command: list[str]
    cwd: Path
    callback: Callable[[CommandResult], Any]
    env: Optional[dict] = None


class GitRunner:
    """
    Async git command runner.
    
    Runs commands in background threads and calls back on the main thread.
    Uses tkinter's after() method for thread-safe callbacks.
    """
    
    def __init__(self, root, git_path: str = "git", env: Optional[dict] = None) -> None:
        self._root = root
        self._git_path = git_path
        self._env = env or {}  # Additional environment variables
        self._queue: queue.Queue[QueuedCommand] = queue.Queue()
        self._busy = False
        self._cancel_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        self._thread: Optional[threading.Thread] = None

    def set_env(self, key: str, value: str) -> None:
        """Set environment variable for git commands."""
        self._env[key] = value
    
    def set_ssh_key(self, key_path: str) -> None:
        """Configure SSH key for git commands."""
        if key_path and os.path.exists(key_path):
            # gitx.py doesn't handle key path directly via env var for the ssh command itself easily
            # without constructing the command. 
            # Standard git way: core.sshCommand
            # But we can also set GIT_SSH_COMMAND env var which gitx.py preserves/uses?
            # gitx.py checks: if a.ssh_accept_new: env["GIT_SSH_COMMAND"] = ...
            # We can set GIT_SSH_COMMAND in _env and git should pick it up.
            # However, gitx.py might override it if ssh_accept_new is set.
            # Let's set it here, and if we need accept-new we might need to append it or handle it.
            
            # For now, let's set GIT_SSH_COMMAND.
            # Note: We need to use forward slashes for paths in Git bash usually, but on Windows python
            # might handle it.
            key_path = str(Path(key_path).as_posix())
            self._env["GIT_SSH_COMMAND"] = f'ssh -i "{key_path}" -o StrictHostKeyChecking=no'

    def set_credentials(self, username: str, password: str) -> None:
        """Configure credentials for gitx.py."""
        # gitx.py uses GIT_USERNAME and GIT_PASSWORD for HTTPS
        # and SSH_PASSPHRASE / SSH_PASSWORD for SSH.
        # We'll set both sets if we don't know the transport, or just set generic ones.
        # Based on settings_dialog, we might know if it's SSH key or password.
        # For now, map 'password' to both HTTPS password and SSH passphrase/password
        # to cover all bases, as the UI treats them somewhat generically.
        
        if username:
            self._env["GIT_USERNAME"] = username
        
        if password:
            self._env["GIT_PASSWORD"] = password
            self._env["SSH_PASSPHRASE"] = password
            self._env["SSH_PASSWORD"] = password
            
    def _prepare_command(self, command: list[str]) -> list[str]:
        """Prepare command list using gitx.py."""
        from opentree.git.wrapper import get_git_command
        
        # command should start with "git"
        git_args = command[1:] if (command and command[0] == "git") else command
        
        # Extract password from env if available
        # We look for GIT_PASSWORD or SSH_PASSPHRASE
        password = self._env.get("GIT_PASSWORD", "")
        if not password:
            password = self._env.get("SSH_PASSPHRASE", "")
            
        return get_git_command(git_args, password=password)

    def run(self, command: list[str], cwd: Path,
            callback: Callable[[CommandResult], Any],
            env: Optional[dict] = None) -> None:
        """Queue a command for execution."""
        
        # Prepare the real command using gitx.py
        full_command = self._prepare_command(command)
        
        # Merge environment
        cmd_env = {**self._env}
        if env:
            cmd_env.update(env)
        
        queued = QueuedCommand(full_command, cwd, callback, cmd_env if cmd_env else None)
        self._queue.put(queued)
        
        if not self._busy:
            self._process_queue()
    
    def _process_queue(self) -> None:
        """Process the next command in the queue."""
        if self._queue.empty():
            return
        
        self._busy = True
        events.emit(Events.BUSY_CHANGED, True)
        
        queued = self._queue.get()
        # Log the git command part for readability, not the full python wrapper
        # The last part of queued.command is the git args (after --)
        try:
            dash_index = queued.command.index("--")
            display_cmd = "git " + " ".join(queued.command[dash_index+1:])
        except ValueError:
            display_cmd = " ".join(queued.command)
            
        events.emit(Events.COMMAND_STARTED, display_cmd)
        
        self._thread = threading.Thread(
            target=self._run_command,
            args=(queued, display_cmd),
            daemon=True
        )
        self._thread.start()
    
    def _run_command(self, queued: QueuedCommand, display_cmd: str) -> None:
        """Run a command in a background thread."""
        
        # Build environment
        run_env = os.environ.copy()
        if queued.env:
            run_env.update(queued.env)
        
        try:
            # We must NOT use shell=True on Windows if we want to avoid cmd window popping up
            # properly with CREATE_NO_WINDOW.
            # Also gitx.py expects to inherit environment.
            
            process = subprocess.Popen(
                queued.command,
                cwd=str(queued.cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                env=run_env,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            stdout, stderr = process.communicate()
            
            result = CommandResult(
                success=process.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                return_code=process.returncode,
                command=display_cmd
            )
            
        except Exception as e:
            result = CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command=display_cmd
            )
        
        # Schedule callback on main thread
        self._root.after(0, lambda: self._on_complete(result, queued.callback))
    
    def _on_complete(self, result: CommandResult,
                     callback: Callable[[CommandResult], Any]) -> None:
        """Handle command completion on main thread."""
        events.emit(Events.COMMAND_FINISHED, result)
        
        try:
            callback(result)
        except Exception as e:
            print(f"Callback error: {e}")
        
        self._busy = False
        events.emit(Events.BUSY_CHANGED, False)
        
        # Process next command if any
        if not self._queue.empty():
            self._process_queue()
    
    def cancel_all(self) -> None:
        """Cancel all pending commands."""
        self._cancel_flag.set()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._cancel_flag.clear()
    
    @property
    def is_busy(self) -> bool:
        """Check if runner is busy."""
        return self._busy


class SyncGitRunner:
    """
    Synchronous git command runner.
    
    For simple commands that need immediate results.
    """
    
    def __init__(self, git_path: str = "git") -> None:
        # We ignore git_path mostly and use gitx.py
        self._git_path = git_path
        self._env = {}

    def set_env(self, key: str, value: str) -> None:
        """Set environment variable for git commands."""
        self._env[key] = value

    def run(self, command: list[str], cwd: Path | str,
            timeout: float = 30.0) -> CommandResult:
        """Run a command synchronously."""
        
        from opentree.git.wrapper import get_git_command
        git_args = command[1:] if (command and command[0] == "git") else command
        
        # Extract credentials
        password = self._env.get("GIT_PASSWORD", "")
        if not password:
            password = self._env.get("SSH_PASSPHRASE", "")
            
        full_command = get_git_command(git_args, password=password)
        
        env = os.environ.copy()
        env.update(self._env)

        try:
            process = subprocess.run(
                full_command,
                cwd=str(cwd),
                capture_output=True,
                timeout=timeout,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            return CommandResult(
                success=process.returncode == 0,
                stdout=process.stdout,
                stderr=process.stderr,
                return_code=process.returncode,
                command="git " + " ".join(git_args)
            )
            
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr="Command timed out",
                return_code=-1,
                command="git " + " ".join(git_args)
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command="git " + " ".join(git_args)
            )

