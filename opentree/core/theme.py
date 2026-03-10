"""
Core theme engine for OpenTree.
Handles color palettes, fonts, and theme switching logic.
"""

import dataclasses
from enum import Enum, auto
from typing import Dict, Any, Optional

class ThemeType(Enum):
    LIGHT = auto()
    DARK = auto()
    CUSTOM = auto()

@dataclasses.dataclass
class Theme:
    name: str
    type: ThemeType
    
    # Semantic Colors
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    
    text_primary: str
    text_secondary: str
    text_tertiary: str
    
    accent_primary: str
    accent_secondary: str
    
    border_subtle: str
    border_focus: str
    
    # Status Colors
    status_success: str
    status_warning: str
    status_danger: str
    status_info: str
    
    # Specific Component Colors
    diff_add_bg: str
    diff_add_fg: str
    diff_del_bg: str
    diff_del_fg: str
    diff_header_bg: str
    diff_header_fg: str
    diff_hunk_bg: str
    diff_hunk_fg: str

    # Font Settings (names, sizes can be dynamic based on OS, but defaults here)
    font_ui: str = "Segoe UI"
    font_mono: str = "Consolas"
    font_size_sm: int = 9
    font_size_md: int = 10
    font_size_lg: int = 11

    @classmethod
    def light(cls) -> "Theme":
        return cls(
            name="Light",
            type=ThemeType.LIGHT,
            
            bg_primary="#ffffff",
            bg_secondary="#f8fafc", # slate-50
            bg_tertiary="#f1f5f9", # slate-100
            
            text_primary="#0f172a", # slate-900
            text_secondary="#475569", # slate-600
            text_tertiary="#94a3b8", # slate-400
            
            accent_primary="#2563eb", # blue-600
            accent_secondary="#3b82f6", # blue-500
            
            border_subtle="#e2e8f0", # slate-200
            border_focus="#3b82f6", # blue-500
            
            status_success="#16a34a", # green-600
            status_warning="#d97706", # amber-600
            status_danger="#dc2626", # red-600
            status_info="#3b82f6", # blue-500
            
            diff_add_bg="#dcfce7", # green-100
            diff_add_fg="#166534", # green-800
            diff_del_bg="#fee2e2", # red-100
            diff_del_fg="#991b1b", # red-800
            diff_header_bg="#f1f5f9", # slate-100
            diff_header_fg="#475569", # slate-600
            diff_hunk_bg="#f8fafc", # slate-50
            diff_hunk_fg="#64748b", # slate-500
        )

    @classmethod
    def dark(cls) -> "Theme":
        return cls(
            name="Dark",
            type=ThemeType.DARK,
            
            bg_primary="#0f172a", # slate-900
            bg_secondary="#1e293b", # slate-800
            bg_tertiary="#334155", # slate-700
            
            text_primary="#f8fafc", # slate-50
            text_secondary="#cbd5e1", # slate-300
            text_tertiary="#94a3b8", # slate-400
            
            accent_primary="#3b82f6", # blue-500
            accent_secondary="#60a5fa", # blue-400
            
            border_subtle="#334155", # slate-700
            border_focus="#3b82f6", # blue-500
            
            status_success="#4ade80", # green-400
            status_warning="#fbbf24", # amber-400
            status_danger="#f87171", # red-400
            status_info="#60a5fa", # blue-400
            
            diff_add_bg="#14532d", # green-900
            diff_add_fg="#dcfce7", # green-100
            diff_del_bg="#7f1d1d", # red-900
            diff_del_fg="#fee2e2", # red-100
            diff_header_bg="#1e293b", # slate-800
            diff_header_fg="#94a3b8", # slate-400
            diff_hunk_bg="#0f172a", # slate-900
            diff_hunk_fg="#64748b", # slate-500
        )

class ThemeManager:
    _instance = None
    _current_theme: Theme = Theme.light()
    _listeners: list = []
    
    @classmethod
    def get_instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
            cls._instance._listeners = []
        return cls._instance
    
    @property
    def theme(self) -> Theme:
        return self._current_theme
    
    def set_theme(self, theme_type: ThemeType) -> None:
        if theme_type == ThemeType.DARK:
            self._current_theme = Theme.dark()
        elif theme_type == ThemeType.LIGHT:
            self._current_theme = Theme.light()
        # Custom theme is set via apply_theme_from_state
        
        self.notify_listeners()

    def apply_theme_from_state(self, state: Any) -> None:
        """Apply theme from AppState.ThemeSettings."""
        # Check if state is ThemeSettings object or similar
        # We construct a Theme object from it
        
        # If the state name suggests a preset, and we want to enforce it?
        # But if type is custom, we load values.
        
        try:
            # Create a Theme instance from state fields
            # We assume state has all the fields of Theme
            
            # Helper to safely get field or default from current theme/light theme
            defaults = dataclasses.asdict(Theme.light())
            
            theme_args = {}
            for field in dataclasses.fields(Theme):
                if field.name == "type":
                    theme_args[field.name] = ThemeType.CUSTOM
                    continue
                    
                val = getattr(state, field.name, None)
                if val is not None:
                    theme_args[field.name] = val
                else:
                    theme_args[field.name] = defaults.get(field.name)
            
            self._current_theme = Theme(**theme_args)
            self.notify_listeners()
            
        except Exception as e:
            print(f"Failed to apply theme from state: {e}")
            self.set_theme(ThemeType.LIGHT)

    def add_listener(self, callback) -> None:
        """Add a listener for theme changes."""
        if callback not in self._listeners:
            self._listeners.append(callback)
    
    def remove_listener(self, callback) -> None:
        """Remove a listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
            
    def notify_listeners(self) -> None:
        """Notify all listeners of theme change."""
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                print(f"Error in theme listener: {e}")
            
    def get_color(self, token: str) -> str:
        """Get color by token name."""
        return getattr(self._current_theme, token, "#ff00ff")
    
    def apply_to_ttk_style(self, style: Any) -> None:
        """Apply current theme to ttk.Style."""
        t = self._current_theme
        
        # Configure standard styling
        style.configure(".", 
            background=t.bg_primary, 
            foreground=t.text_primary,
            fieldbackground=t.bg_primary,
            troughcolor=t.bg_tertiary,
            font=(t.font_ui, t.font_size_md)
        )
        
        # Frames
        style.configure("TFrame", background=t.bg_primary)
        style.configure("Toolbar.TFrame", background=t.bg_secondary)
        
        # Panes
        style.configure("TPanedwindow", background=t.bg_secondary)
        style.configure("TLabel", background=t.bg_primary, foreground=t.text_primary)
        style.configure("TLabelframe", background=t.bg_primary, bordercolor=t.border_subtle)
        style.configure("TLabelframe.Label", background=t.bg_primary, foreground=t.text_secondary)
        
        # Buttons
        style.configure("TButton", 
            padding=(6, 4), 
            relief="flat",
            background=t.bg_secondary,
            foreground=t.text_primary
        )
        style.map("TButton",
            background=[("active", t.bg_tertiary), ("pressed", t.accent_primary)],
            foreground=[("pressed", "#ffffff")]
        )
        
        # Treeview
        style.configure("Treeview", 
            background=t.bg_primary,
            foreground=t.text_primary,
            fieldbackground=t.bg_primary,
            font=(t.font_ui, t.font_size_md),
            rowheight=24
        )
        style.configure("Treeview.Heading", 
            background=t.bg_secondary,
            foreground=t.text_secondary,
            font=(t.font_ui, t.font_size_sm, "bold"),
            relief="flat"
        )
        style.map("Treeview", 
            background=[("selected", t.accent_primary)],
            foreground=[("selected", "#ffffff")]
        )
        
        # Notebook
        style.configure("TNotebook", background=t.bg_secondary)
        style.configure("TNotebook.Tab", 
            padding=(10, 4),
            background=t.bg_secondary,
            foreground=t.text_secondary
        )
        style.map("TNotebook.Tab",
            background=[("selected", t.bg_primary)],
            foreground=[("selected", t.accent_primary)]
        )
        
        # Scrollbars
        style.configure("Vertical.TScrollbar",
            background=t.bg_tertiary,
            troughcolor=t.bg_primary,
            bordercolor=t.border_subtle,
            arrowcolor=t.text_secondary,
            relief="flat"
        )
        style.configure("Horizontal.TScrollbar",
            background=t.bg_tertiary,
            troughcolor=t.bg_primary,
            bordercolor=t.border_subtle,
            arrowcolor=t.text_secondary,
            relief="flat"
        )
        style.map("Vertical.TScrollbar",
            background=[("active", t.accent_secondary), ("pressed", t.accent_primary)]
        )
        style.map("Horizontal.TScrollbar",
            background=[("active", t.accent_secondary), ("pressed", t.accent_primary)]
        )

# Global accessor
theme = ThemeManager.get_instance()
