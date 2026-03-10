"""
Task runner for executing long-running operations with UI progress.
"""

import threading
import subprocess
import os
import tkinter as tk
from typing import Optional, Callable
from opentree.core.models import CommandResult
from opentree.ui.progress_dialog import ProgressDialog


class TaskRunner:
    """
    Executes commands in a background thread and updates a ProgressDialog.
    """
    
    def __init__(self, root: tk.Widget) -> None:
        self._root = root
        
    def run_with_progress(self, title: str, cmd: list[str], cwd: str, env: dict = {},
                          on_success: Optional[Callable[[CommandResult], None]] = None) -> None:
        """Run a command with a progress dialog."""
        
        # Determine actual command and environment
        # cmd is already the full command list
        # env is additional environment
        
        cmd_env = os.environ.copy()
        cmd_env.update(env)
        
        # Mask sensitive info for display
        cmd_str = " ".join(cmd)
        # Simple heuristic to hide potential passwords in URL auth
        display_cmd = cmd_str
        if "https://" in display_cmd and "@" in display_cmd:
             # Basic masking for https://user:pass@domain
             import re
             display_cmd = re.sub(r'https://([^:]+):([^@]+)@', r'https://\1:***@', display_cmd)
        
        dialog = ProgressDialog(self._root, title, display_cmd)
        
        def run_command():
            try:
                # Prepare startup info to hide console window on Windows
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    env=cmd_env,
                    startupinfo=startupinfo,
                    bufsize=1,
                    universal_newlines=True,
                    encoding='utf-8', 
                    errors='replace'
                )
                
                # Read output
                for line in iter(process.stdout.readline, ''):
                    if dialog.cancelled:
                        process.terminate()
                        break
                    line = line.rstrip()
                    if line:
                        is_error = any(e in line.lower() for e in ['error:', 'fatal:', 'error', 'rejected'])
                        self._root.after(0, lambda l=line, err=is_error: dialog.append_output(l, err))
                
                process.wait()
                
                success = process.returncode == 0 and not dialog.cancelled
                result = CommandResult(
                    success=success,
                    stdout="",
                    stderr="" if success else "Command failed",
                    return_code=process.returncode,
                    command=display_cmd
                )
                
                self._root.after(0, lambda: self._finish(dialog, result, on_success))
                
            except Exception as e:
                result = CommandResult(
                    success=False, stdout="", stderr=str(e), 
                    return_code=-1, command=display_cmd
                )
                self._root.after(0, lambda: self._finish(dialog, result, None))
                
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
        
    def _finish(self, dialog: ProgressDialog, result: CommandResult, 
                on_success: Optional[Callable[[CommandResult], None]]) -> None:
        """Finish the dialog and callback."""
        dialog.finish(result.success)
        if result.success and on_success:
            on_success(result)
