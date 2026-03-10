"""
Search panel for OpenTree.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from opentree.core.i18n import tr
from opentree.core.models import CommitInfo
from opentree.core.theme import ThemeManager
from opentree.ui.widgets import CommitListView, DiffViewer


class SearchPanel(ttk.Frame):
    """Panel for searching commits."""

    def __init__(self, parent: tk.Widget, on_search: Callable[[str, str], None], **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self._on_search = on_search

        ctrl_frame = ttk.Frame(self, padding=5)
        ctrl_frame.pack(fill=tk.X)

        ttk.Label(ctrl_frame, text=tr("la_search", "Search") + ":").pack(side=tk.LEFT)

        self._search_term = ttk.Entry(ctrl_frame, width=40)
        self._search_term.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self._search_term.bind("<Return>", lambda e: self._do_search())

        self._search_type = tk.StringVar(value="grep")
        ttk.Radiobutton(ctrl_frame, text=tr("la_message", "Message"), variable=self._search_type, value="grep").pack(
            side=tk.LEFT,
            padx=5,
        )
        ttk.Radiobutton(ctrl_frame, text=tr("la_author", "Author"), variable=self._search_type, value="author").pack(
            side=tk.LEFT,
            padx=5,
        )

        ttk.Button(ctrl_frame, text=tr("la_search", "Search"), command=self._do_search).pack(side=tk.LEFT, padx=5)

        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.LabelFrame(paned, text=tr("la_results", "Results"))
        paned.add(list_frame, weight=1)

        self.commit_list = CommitListView(list_frame)
        self.commit_list.pack(fill=tk.BOTH, expand=True)

        details_frame = ttk.Frame(paned)
        paned.add(details_frame, weight=1)

        theme = ThemeManager.get_instance().theme
        self._details_text = tk.Text(
            details_frame,
            height=6,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=(theme.font_mono, theme.font_size_md),
            bg=theme.bg_primary,
            fg=theme.text_primary,
            insertbackground=theme.text_primary,
            selectbackground=theme.accent_primary,
        )
        self._details_text.pack(fill=tk.X)

        self.diff_viewer = DiffViewer(details_frame)
        self.diff_viewer.pack(fill=tk.BOTH, expand=True)

    def _do_search(self) -> None:
        term = self._search_term.get().strip()
        search_type = self._search_type.get()
        if term:
            self._on_search(term, search_type)

    def set_results(self, commits: list[CommitInfo]) -> None:
        """Set search results."""
        self.commit_list.set_commits(commits)

    def set_details(self, text: str) -> None:
        """Set commit details."""
        self._details_text.configure(state=tk.NORMAL)
        self._details_text.delete("1.0", tk.END)
        self._details_text.insert("1.0", text)
        self._details_text.configure(state=tk.DISABLED)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        theme = ThemeManager.get_instance().theme
        self.commit_list.refresh_theme()
        self.diff_viewer.refresh_theme()
        self._details_text.configure(
            bg=theme.bg_primary,
            fg=theme.text_primary,
            insertbackground=theme.text_primary,
            selectbackground=theme.accent_primary,
            font=(theme.font_mono, theme.font_size_md),
        )
