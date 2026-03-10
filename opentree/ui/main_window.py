"""
Main window layout for OpenTree.

SourceTree-style UI with toolbar, sidebar, and content panels.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from opentree.core.models import FileStatus, CommitInfo, BranchInfo
from opentree.core.i18n import tr
from opentree.ui.widgets import (
    BranchTreeView,
    DiffViewer,
    FileListView,
    CommitListView,
    CommitPanel,
    StashSidebarView,
    TagTreeView,
)
from opentree.ui.dialogs import StashDialog


from opentree.ui.search_panel import SearchPanel


from opentree.utils.icons import icons

class Toolbar(ttk.Frame):
    """Main toolbar with action buttons."""
    
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, style="Toolbar.TFrame", **kwargs)
        
        # Helper to create styled buttons
        def create_btn(icon_name: str, text: str) -> ttk.Button:
            icon = icons.get_icon(icon_name, size=16)
            btn = ttk.Button(self, text=text, image=icon, compound=tk.LEFT)
            # Check if image loaded, if not compound fallback is fine (just text)
            if icon:
                btn.image = icon # Keep reference
            return btn

        # Create buttons
        self.pull_btn = create_btn("pull", tr("la_pull"))
        self.pull_btn.pack(side=tk.LEFT, padx=5, pady=8)
        
        self.push_btn = create_btn("push", tr("la_push"))
        self.push_btn.pack(side=tk.LEFT, padx=5, pady=8)
        
        self.fetch_btn = create_btn("fetch", tr("la_fetch"))
        self.fetch_btn.pack(side=tk.LEFT, padx=5, pady=8)
        
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=8)
        
        self.branch_btn = create_btn("branch", tr("la_branch"))
        self.branch_btn.pack(side=tk.LEFT, padx=5, pady=8)
        
        self.merge_btn = create_btn("merge", tr("la_merge"))
        self.merge_btn.pack(side=tk.LEFT, padx=5, pady=8)

        self.stash_btn = create_btn("stash", tr("la_stash"))
        self.stash_btn.pack(side=tk.LEFT, padx=5, pady=8)
        
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=8)
        
        # Refresh icon needed? We have fetch, maybe refresh is for view?
        # Let's use fetch icon for refresh for now or add a distinct one
        # Using fetch icon for refresh button as well for consistency or distinct if exists
        self.refresh_btn = create_btn("fetch", tr("la_refresh")) 
        self.refresh_btn.pack(side=tk.LEFT, padx=5, pady=8)
        
        # Settings on far right
        self.settings_btn = create_btn("settings", tr("la_settings"))
        self.settings_btn.pack(side=tk.RIGHT, padx=5, pady=8)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        # TTK buttons update automatically via style, but we can do extra here if needed.
        pass


class Sidebar(ttk.Frame):
    """Left sidebar with workspace navigation."""
    
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self.configure(width=220)
        
        # WORKSPACE section
        workspace_label = ttk.Label(self, text=tr("la_workspace"), font=("Segoe UI", 9, "bold"))
        workspace_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.workspace_tree = ttk.Treeview(self, show="tree", height=3, selectmode="browse")
        self.workspace_tree.insert("", tk.END, text=tr("la_file_status"), iid="file_status")
        self.workspace_tree.insert("", tk.END, text=tr("la_history"), iid="history")
        self.workspace_tree.insert("", tk.END, text=tr("la_search"), iid="search")
        self.workspace_tree.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.workspace_tree.selection_set("file_status")
        
        # BRANCHES section
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        branches_label = ttk.Label(self, text=tr("la_branches"), font=("Segoe UI", 9, "bold"))
        branches_label.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        self.branch_tree = BranchTreeView(self)
        self.branch_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # TAGS section
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        tags_label = ttk.Label(self, text=tr("la_tags", "Tags"), font=("Segoe UI", 9, "bold"))
        tags_label.pack(anchor=tk.W, padx=10, pady=(0, 5))

        self.tag_tree = TagTreeView(self)
        self.tag_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # STASHES section
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        stashes_label = ttk.Label(self, text=tr("la_stashes"), font=("Segoe UI", 9, "bold"))
        stashes_label.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        self.stash_tree = StashSidebarView(self)
        self.stash_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    def set_branches(self, branches: list[BranchInfo]) -> None:
        """Set the branches in the tree."""
        self.branch_tree.set_branches(branches)
    
    def get_selected_branch(self) -> Optional[str]:
        """Get selected branch name."""
        return self.branch_tree.get_selected()

    def set_tags(self, tags: list) -> None:
        """Set the tags in the tree."""
        self.tag_tree.set_tags(tags)

    def get_selected_tag(self) -> Optional[str]:
        """Get selected tag name."""
        return self.tag_tree.get_selected()

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        from opentree.core.theme import ThemeManager
        # Treeview updates automatically via style
        self.branch_tree.refresh_theme()
        self.tag_tree.refresh_theme()
        self.stash_tree.refresh_theme()


class FileStatusPanel(ttk.Frame):
    """Panel for file status view."""
    
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        # Vertical paned window
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Top section: File lists
        file_frame = ttk.Frame(paned)
        paned.add(file_frame, weight=1)
        
        # Horizontal split for staged/unstaged
        file_paned = ttk.PanedWindow(file_frame, orient=tk.HORIZONTAL)
        file_paned.pack(fill=tk.BOTH, expand=True)
        
        # Unstaged files
        unstaged_frame = ttk.LabelFrame(file_paned, text=tr("la_unstaged_files"))
        file_paned.add(unstaged_frame, weight=1)
        
        # Pack buttons first at bottom to ensure visibility
        unstaged_btn_frame = ttk.Frame(unstaged_frame)
        unstaged_btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.stage_btn = ttk.Button(unstaged_btn_frame, text=tr("la_stage_selected"))
        self.stage_btn.pack(side=tk.LEFT)
        self.stage_all_btn = ttk.Button(unstaged_btn_frame, text=tr("la_stage_all"))
        self.stage_all_btn.pack(side=tk.LEFT, padx=5)
        
        self.unstaged_list = FileListView(unstaged_frame)
        self.unstaged_list.pack(fill=tk.BOTH, expand=True)
        
        # Staged files
        staged_frame = ttk.LabelFrame(file_paned, text=tr("la_staged_files"))
        file_paned.add(staged_frame, weight=1)
        
        # Pack buttons first at bottom
        staged_btn_frame = ttk.Frame(staged_frame)
        staged_btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.unstage_btn = ttk.Button(staged_btn_frame, text=tr("la_unstage_selected"))
        self.unstage_btn.pack(side=tk.LEFT)
        self.unstage_all_btn = ttk.Button(staged_btn_frame, text=tr("la_unstage_all"))
        self.unstage_all_btn.pack(side=tk.LEFT, padx=5)
        
        self.staged_list = FileListView(staged_frame)
        self.staged_list.pack(fill=tk.BOTH, expand=True)
        
        # Middle section: Diff viewer
        diff_frame = ttk.LabelFrame(paned, text=tr("la_diff"))
        paned.add(diff_frame, weight=2)
        
        self._diff_file_label = ttk.Label(diff_frame, text="")
        self._diff_file_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.diff_viewer = DiffViewer(diff_frame)
        self.diff_viewer.pack(fill=tk.BOTH, expand=True)
        
        # Bottom section: Commit
        commit_frame = ttk.LabelFrame(paned, text=tr("la_commit"))
        paned.add(commit_frame, weight=0) # weight 0 to keep it from growing too much
        
        self._commit_panel = CommitPanel(commit_frame)
        self._commit_panel.pack(fill=tk.BOTH, expand=True)
    
    @property
    def commit_btn(self) -> ttk.Button:
        return self._commit_panel.commit_btn
    
    @property
    def push_immediately(self) -> bool:
        return self._commit_panel.push_immediately
        
    def set_push_immediately(self, value: bool) -> None:
        self._commit_panel.set_push_immediately(value)
    
    def set_diff_file(self, path: str) -> None:
        self._diff_file_label.configure(text=path)
    
    def set_author(self, author: str) -> None:
        self._commit_panel.set_author(author)
    
    def get_commit_message(self) -> str:
        return self._commit_panel.get_message()
    
    def clear_commit_message(self) -> None:
        self._commit_panel.clear_message()

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        self.unstaged_list.refresh_theme()
        self.staged_list.refresh_theme()
        self.diff_viewer.refresh_theme()
        self._commit_panel.refresh_theme()


class HistoryPanel(ttk.Frame):
    """Panel for commit history view."""
    
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Commit list
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        
        self.commit_list = CommitListView(list_frame)
        self.commit_list.pack(fill=tk.BOTH, expand=True)
        
        # Details section
        details_frame = ttk.Frame(paned)
        paned.add(details_frame, weight=1)
        
        # Info panel
        info_frame = ttk.LabelFrame(details_frame, text=tr("la_commit_details"))
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._details_text = tk.Text(info_frame, height=6, wrap=tk.WORD,
                                     state=tk.DISABLED, font=("Consolas", 9),
                                     bd=0, padx=5, pady=5)
        self._details_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Diff viewer
        diff_frame = ttk.LabelFrame(details_frame, text=tr("la_changes"))
        diff_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.diff_viewer = DiffViewer(diff_frame)
        self.diff_viewer.pack(fill=tk.BOTH, expand=True)
        
        self.refresh_theme()
    
    def set_details(self, text: str) -> None:
        self._details_text.configure(state=tk.NORMAL)
        self._details_text.delete("1.0", tk.END)
        self._details_text.insert("1.0", text)
        
        # Apply simple highlighting
        # Highlight "commit <hash>"
        import re
        
        # Reset tags
        for tag in self._details_text.tag_names():
            self._details_text.tag_remove(tag, "1.0", tk.END)
            
        # Commit hash line
        commit_match = re.search(r"^commit\s+[0-9a-f]+", text, re.MULTILINE)
        if commit_match:
            self._details_text.tag_add("commit_hash", f"1.{commit_match.start()}", f"1.{commit_match.end()}")
            
        # Headers (Author:, Date:, etc.)
        for match in re.finditer(r"^(Author|Date|Merge):", text, re.MULTILINE):
            # Calculate line number
            line_idx = text.count("\n", 0, match.start()) + 1
            col_start = match.start() - text.rfind("\n", 0, match.start()) - 1
            if col_start < 0: col_start = match.start() # First line case
            
            # Simple line/col calculation might be buggy with mixed EOL, let's use tk search
            pass

        # Better approach: use tk search
        start = "1.0"
        while True:
            pos = self._details_text.search(r"^(Author|Date|Merge):", start, stopindex=tk.END, regexp=True)
            if not pos:
                break
            # Highlight key
            end = f"{pos} lineend"
            # Actually we just want the label
            label_end = self._details_text.search(":", pos, stopindex=end)
            if label_end:
                 self._details_text.tag_add("header_label", pos, f"{label_end}+1c")
            start = f"{pos}+1l"

        # Highlight diff stats (files changed)
        # Look for " X files changed, Y insertions(+), Z deletions(-)"
        start = "1.0"
        while True:
            pos = self._details_text.search(r"^\s*\d+\s+files?\s+changed,", start, stopindex=tk.END, regexp=True)
            if not pos:
                break
            self._details_text.tag_add("stats", pos, f"{pos} lineend")
            start = f"{pos}+1l"
            
        self._details_text.configure(state=tk.DISABLED)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        from opentree.core.theme import ThemeManager
        theme = ThemeManager.get_instance().theme
        
        self.commit_list.refresh_theme()
        self.diff_viewer.refresh_theme()
        
        self._details_text.configure(
            bg=theme.bg_primary,
            fg=theme.text_primary,
            blockcursor=False,
            insertbackground=theme.text_primary,
            selectbackground=theme.accent_primary,
            font=(theme.font_mono, theme.font_size_md)
        )


class RepoView(ttk.Frame):
    """
    Repository view content.
    
    SourceTree-style layout with toolbar, sidebar, and content panels.
    Represents a single tab in the application.
    """
    
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self._setup_layout()
    
    def _setup_layout(self) -> None:
        """Create the main window layout."""
        # Toolbar at top
        self._toolbar = Toolbar(self)
        self._toolbar.pack(fill=tk.X)
        
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        # Main content area
        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Horizontal paned: sidebar | main panel
        self._main_paned = ttk.PanedWindow(content, orient=tk.HORIZONTAL)
        self._main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar
        self._sidebar = Sidebar(self._main_paned)
        self._main_paned.add(self._sidebar, weight=0)
        
        # Right: Content panels (stacked)
        right_frame = ttk.Frame(self._main_paned)
        self._main_paned.add(right_frame, weight=1)
        
        # File Status Panel
        self._file_status_panel = FileStatusPanel(right_frame)
        
        # History Panel
        self._history_panel = HistoryPanel(right_frame)
        
        # Search Panel
        self._search_panel = SearchPanel(right_frame, on_search=lambda t, ty: None) # Callback set later
        
        # Show file status by default
        self._current_view = "file_status"
        self._file_status_panel.pack(fill=tk.BOTH, expand=True)
        
        # Bind workspace selection
        self._sidebar.workspace_tree.bind("<<TreeviewSelect>>", self._on_workspace_select)
        
        # Status bar
        self._status_bar = ttk.Label(self, text=tr("la_ready"), anchor=tk.W)
        self._status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _on_workspace_select(self, event: tk.Event) -> None:
        """Handle workspace tree selection."""
        selection = self._sidebar.workspace_tree.selection()
        if selection:
            view = selection[0]
            self._show_view(view)
    
    def _show_view(self, view: str) -> None:
        """Show the specified view."""
        if view == self._current_view:
            return
        
        if self._current_view == "file_status":
            self._file_status_panel.pack_forget()
        elif self._current_view == "history":
            self._history_panel.pack_forget()
        elif self._current_view == "search":
            self._search_panel.pack_forget()
        
        if view == "file_status":
            self._file_status_panel.pack(fill=tk.BOTH, expand=True)
        elif view == "history":
            self._history_panel.pack(fill=tk.BOTH, expand=True)
        elif view == "search":
            self._search_panel.pack(fill=tk.BOTH, expand=True)
        
        self._current_view = view
    
    @property
    def toolbar(self) -> Toolbar:
        return self._toolbar
    
    @property
    def sidebar(self) -> Sidebar:
        return self._sidebar
    
    @property
    def file_status_panel(self) -> FileStatusPanel:
        return self._file_status_panel
    
    @property
    def history_panel(self) -> HistoryPanel:
        return self._history_panel
    
    @property
    def search_panel(self) -> SearchPanel:
        return self._search_panel
    
    def set_status(self, message: str) -> None:
        """Set status bar text."""
        self._status_bar.configure(text=message)
    
    def set_busy(self, busy: bool) -> None:
        """Set busy state."""
        if busy:
            self._status_bar.configure(text=tr("la_working"))
        else:
            self._status_bar.configure(text=tr("la_ready"))
    
    def enable_repo_actions(self, enabled: bool) -> None:
        """Enable or disable repository-related actions."""
        state = "normal" if enabled else "disabled"
        self._toolbar.pull_btn.configure(state=state)
        self._toolbar.push_btn.configure(state=state)
        self._toolbar.fetch_btn.configure(state=state)
        self._toolbar.branch_btn.configure(state=state)
        self._toolbar.merge_btn.configure(state=state)
        self._toolbar.stash_btn.configure(state=state)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        self._toolbar.refresh_theme()
        self._toolbar.refresh_theme()
        self._sidebar.refresh_theme()
        self._file_status_panel.refresh_theme()
        self._history_panel.refresh_theme()
        self._search_panel.refresh_theme()
