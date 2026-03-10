"""
Progress dialog for Git operations.

Shows real-time output from git commands with error highlighting.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from opentree.core.i18n import tr


class ProgressDialog(tk.Toplevel):
    """
    Dialog that shows progress of a git operation.
    
    Displays the command being run, its output in real-time,
    and highlights errors in red.
    """
    
    def __init__(self, parent: tk.Widget, title: str, 
                 command: str = "", on_cancel: Optional[Callable] = None) -> None:
        super().__init__(parent)
        
        self.title(title)
        self.transient(parent)
        
        self._on_cancel = on_cancel
        self._cancelled = False
        self._finished = False
        self._has_errors = False
        self._show_full_output = tk.BooleanVar(value=True)
        
        self._setup_ui(command)
        
        # Window size and position
        # Dynamic sizing - let geometry manager determine size
        self.minsize(600, 300) 
        
        # Auto-size first
        self.geometry("")
        self.update_idletasks()
        
        # Get requested size
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        
        # Ensure minimums
        w = max(w, 600)
        h = max(h, 300)
        
        # Center
        root_x = parent.winfo_rootx()
        root_y = parent.winfo_rooty()
        root_w = parent.winfo_width()
        root_h = parent.winfo_height()
        
        x = root_x + (root_w - w) // 2
        y = root_y + (root_h - h) // 2
        
        if y < 0: y = 0
        
        # Set geometry
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        # Protocol for window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.grab_set()
    
    def _setup_ui(self, command: str) -> None:
        """Create the UI layout."""
        # Main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar at top
        self._status_label = ttk.Label(main_frame, text=tr("la_running"), 
                                       font=("Segoe UI", 10, "bold"))
        self._status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Command being run
        if command:
            cmd_label = ttk.Label(main_frame, text=command, 
                                 font=("Consolas", 9))
            cmd_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Output text area
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self._output_text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self._output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Apply theme to text widget
        from opentree.core.theme import ThemeManager
        theme = ThemeManager.get_instance().theme
        self._output_text.configure(
            background=theme.bg_primary,
            foreground=theme.text_primary,
            insertbackground=theme.text_primary,
            selectbackground=theme.accent_primary,
            selectforeground="#ffffff"
        )
        
        scrollbar = ttk.Scrollbar(text_frame, command=self._output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._output_text.configure(yscrollcommand=scrollbar.set)
        
        # Configure tags for error highlighting - remove background for better compatibility
        self._output_text.tag_configure("error", foreground=theme.status_danger)
        self._output_text.tag_configure("warning", foreground=theme.status_warning)
        self._output_text.tag_configure("success", foreground=theme.status_success)
        self._output_text.tag_configure("command", foreground=theme.text_secondary, font=("Consolas", 9, "italic"))
        
        # Status message at bottom
        self._bottom_status = ttk.Label(main_frame, text="")
        self._bottom_status.pack(anchor=tk.W, pady=(10, 0))
        
        # Button frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Rename "Close" to "Done" as requested
        done_text = "Done" # Fallback
        try:
             # Try to start using "Done" if available, else hardcode
             done_text = "Done" 
        except:
             pass
             
        self._close_btn = ttk.Button(btn_frame, text=done_text, 
                                     command=self.destroy, state=tk.DISABLED)
        self._close_btn.pack(side=tk.RIGHT)
    
    def append_output(self, text: str, is_error: bool = False) -> None:
        """Add text to the output area."""
        # Always show full output now
            
        self._output_text.configure(state=tk.NORMAL)
        
        # Determine tag
        tag = None
        if is_error:
            tag = "error"
            self._has_errors = True
        elif "warning" in text.lower():
            tag = "warning"
        elif any(s in text.lower() for s in ["success", "done", "complete"]):
            tag = "success"
        
        if tag:
            self._output_text.insert(tk.END, text + "\n", tag)
        else:
            self._output_text.insert(tk.END, text + "\n")
        
        self._output_text.see(tk.END)
        self._output_text.configure(state=tk.DISABLED)
        self.update_idletasks()
    
    def append_command(self, command: str) -> None:
        """Add a command line to output (styled differently)."""
        self._output_text.configure(state=tk.NORMAL)
        self._output_text.insert(tk.END, command + "\n", "command")
        self._output_text.see(tk.END)
        self._output_text.configure(state=tk.DISABLED)
        self.update_idletasks()
    
    def set_status(self, status: str) -> None:
        """Update the status label."""
        self._status_label.configure(text=status)
    
    def finish(self, success: bool = True, message: str = "") -> None:
        """Mark the operation as finished."""
        self._finished = True
        
        # Update buttons
        # Update buttons
        self._close_btn.configure(state=tk.NORMAL)
        
        # Update status
        if success and not self._has_errors:
            self._status_label.configure(text="✓ " + (message or "Completed"))
            self._bottom_status.configure(text="")
        else:
            self._status_label.configure(text="✗ " + (message or "Failed"))
            self._bottom_status.configure(
                text=tr("la_completed_with_errors"),
                foreground="#cc0000"
            )
    
    def _cancel(self) -> None:
        """Cancel the operation."""
        self._cancelled = True
        if self._on_cancel:
            self._on_cancel()
        self.finish(False, "Cancelled")
    
    def _on_close(self) -> None:
        """Handle window close button."""
        if self._finished:
            self.destroy()
        else:
            self._cancel()
    
    @property
    def cancelled(self) -> bool:
        """Check if the operation was cancelled."""
        return self._cancelled
    
    def wait_for_close(self) -> None:
        """Wait for the dialog to be closed."""
        self.wait_window(self)
