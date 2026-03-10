"""
Custom Menu Bar for OpenTree.

Replaces the native title bar menu to allow for full theming support.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Any, Optional

from opentree.core.i18n import tr
from opentree.core.theme import ThemeManager

class CustomMenuBar(ttk.Frame):
    """
    Themed menu bar that mimics standard window menu but allows custom styling.
    """
    
    def __init__(self, parent: tk.Widget, app: Any, **kwargs) -> None:
        super().__init__(parent, style="MenuBar.TFrame", **kwargs)
        self.app = app
        
        # Configure style
        style = ttk.Style()
        style.configure("MenuBar.TFrame", background=ThemeManager.get_instance().theme.bg_secondary)
        
        # Style for menu buttons to make them look like menu items (flat, no padding)
        style.configure("MenuBar.TMenubutton", 
            background=ThemeManager.get_instance().theme.bg_secondary,
            foreground=ThemeManager.get_instance().theme.text_primary,
            relief="flat",
            padding=(10, 5),
            font=("Segoe UI", 9)
        )
        style.map("MenuBar.TMenubutton",
            background=[("active", ThemeManager.get_instance().theme.bg_tertiary)],
            foreground=[("active", ThemeManager.get_instance().theme.text_primary)]
        )
        
        # Buttons
        self._menus = {}
        
        self._create_menus()
        
    def _create_menus(self) -> None:
        """Create the menu buttons."""
        # File (Alt+F)
        self._add_menu("File", 0, "f", self._create_file_menu)
        self._add_menu("Edit", 0, "e", self._create_edit_menu)
        self._add_menu("View", 0, "v", self._create_view_menu)
        self._add_menu("Repository", 0, "r", self._create_repo_menu)
        self._add_menu("Help", 0, "h", self._create_help_menu)
        
    def _add_menu(self, label: str, underline: int, shortcut: str, creator: Callable[[tk.Menu], None]) -> None:
        """Add a top-level menu item."""
        mb = ttk.Menubutton(self, text=label, underline=underline, style="MenuBar.TMenubutton")
        mb.pack(side=tk.LEFT, padx=0, pady=0)
        
        # Create the dropdown menu
        menu = tk.Menu(mb, tearoff=0)
        creator(menu)
        
        mb.configure(menu=menu)
        self._menus[label] = (mb, menu)
        
        # Bind Alt+Key
        self.app._root.bind(f"<Alt-{shortcut}>", lambda e: self._open_menu(mb))
        self.app._root.bind(f"<Alt-{shortcut.upper()}>", lambda e: self._open_menu(mb))

    def _open_menu(self, mb: ttk.Menubutton) -> None:
        """Programmatically open the menu."""
        # This is tricky with ttk.Menubutton. 
        # We can try 'event_generate("<Button-1>")' but that might not place it right if mouse is elsewhere.
        # Or menu.post() but we need coordinates.
        
        x = mb.winfo_rootx()
        y = mb.winfo_rooty() + mb.winfo_height()
        
        # Find the menu associated
        menu = self.nametowidget(mb['menu'])
        menu.post(x, y)
        
    def _create_file_menu(self, menu: tk.Menu) -> None:
        menu.add_command(label="Open Repository...", command=self.app._cmd_open_repo, accelerator="Ctrl+O")
        menu.add_command(label="Close Tab", command=self.app._cmd_close_current_tab, accelerator="Ctrl+W")
        menu.add_separator()
        menu.add_command(label="Settings...", command=self.app._cmd_settings)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.app._on_close, accelerator="Alt+F4")

    def _create_edit_menu(self, menu: tk.Menu) -> None:
        menu.add_command(label="Refresh", command=self.app._cmd_refresh, accelerator="F5")

    def _create_view_menu(self, menu: tk.Menu) -> None:
        menu.add_command(label="File Status", command=lambda: self.app._invoke_active("_show_view", "file_status"))
        menu.add_command(label="History", command=lambda: self.app._invoke_active("_show_view", "history"))

    def _create_repo_menu(self, menu: tk.Menu) -> None:
        menu.add_command(label="Fetch", command=lambda: self.app._invoke_active("cmd_fetch"))
        menu.add_command(label="Pull", command=lambda: self.app._invoke_active("cmd_pull"))
        menu.add_command(label="Push", command=lambda: self.app._invoke_active("cmd_push"))

    def _create_help_menu(self, menu: tk.Menu) -> None:
        menu.add_command(label="About", command=self.app._cmd_about)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        theme = ThemeManager.get_instance().theme
        style = ttk.Style()
        style.configure("MenuBar.TFrame", background=theme.bg_secondary)
        
        style.configure("MenuBar.TMenubutton", 
            background=theme.bg_secondary,
            foreground=theme.text_primary
        )
        style.map("MenuBar.TMenubutton",
            background=[("active", theme.bg_tertiary)],
            foreground=[("active", theme.text_primary)]
        )
