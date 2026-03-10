"""
Custom UI widgets for OpenTree.

Reusable tkinter widgets for the application.
"""

import re
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from opentree.core.i18n import tr
from opentree.core.models import BranchInfo, CommitInfo, FileStatus, TagInfo
from opentree.core.theme import ThemeManager
from opentree.ui.graph import build_graph, get_lane_color_index
from opentree.utils.text import truncate


class DiffViewer(ttk.Frame):
    """
    Widget for displaying git diffs with gutters and clearer hunk structure.
    """

    _HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    _DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        theme = ThemeManager.get_instance().theme

        self._old_gutter = tk.Text(
            self,
            width=6,
            wrap=tk.NONE,
            state=tk.DISABLED,
            takefocus=0,
            bd=0,
            padx=6,
            pady=4,
            font=(theme.font_mono, theme.font_size_md),
            bg=theme.bg_secondary,
            fg=theme.text_tertiary,
            relief=tk.FLAT,
        )
        self._new_gutter = tk.Text(
            self,
            width=6,
            wrap=tk.NONE,
            state=tk.DISABLED,
            takefocus=0,
            bd=0,
            padx=6,
            pady=4,
            font=(theme.font_mono, theme.font_size_md),
            bg=theme.bg_secondary,
            fg=theme.text_tertiary,
            relief=tk.FLAT,
        )
        self._text = tk.Text(
            self,
            wrap=tk.NONE,
            state=tk.DISABLED,
            takefocus=1,
            bd=0,
            padx=8,
            pady=4,
            font=(theme.font_mono, theme.font_size_md),
            bg=theme.bg_primary,
            fg=theme.text_primary,
            insertbackground=theme.text_primary,
            selectbackground=theme.accent_primary,
            selectforeground="#ffffff",
            exportselection=False,
            cursor="xterm",
        )

        v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._on_vertical_scroll, style="Vertical.TScrollbar")
        h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._text.xview, style="Horizontal.TScrollbar")
        self._text.configure(yscrollcommand=self._on_text_yview, xscrollcommand=h_scroll.set)

        self._old_gutter.grid(row=0, column=0, sticky="ns")
        self._new_gutter.grid(row=0, column=1, sticky="ns")
        self._text.grid(row=0, column=2, sticky="nsew")
        v_scroll.grid(row=0, column=3, sticky="ns")
        h_scroll.grid(row=1, column=2, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)

        for widget in (self._old_gutter, self._new_gutter, self._text):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel)
            widget.bind("<Button-5>", self._on_mousewheel)
            widget.bind("<Control-c>", self._copy_selection)
            widget.bind("<Control-C>", self._copy_selection)

        self._text.bind("<Control-a>", self._select_all)
        self._text.bind("<Control-A>", self._select_all)
        self._copy_menu = tk.Menu(self, tearoff=0)
        self._copy_menu.add_command(label="Copy", command=self._copy_selection)
        self._copy_menu.add_command(label="Copy All", command=self._copy_all)
        self._bind_copy_menu(self._old_gutter)
        self._bind_copy_menu(self._new_gutter)
        self._bind_copy_menu(self._text)

        self._apply_tags()

    def _apply_tags(self) -> None:
        """Configure text tags for current theme."""
        theme = ThemeManager.get_instance().theme

        for widget in (self._old_gutter, self._new_gutter):
            widget.tag_configure("gutter", background=theme.bg_secondary, foreground=theme.text_tertiary)
            widget.tag_configure("header", background=theme.diff_header_bg, foreground=theme.diff_header_fg)
            widget.tag_configure("hunk", background=theme.diff_hunk_bg, foreground=theme.diff_hunk_fg)
            widget.tag_configure("add", background=theme.diff_add_bg, foreground=theme.diff_add_fg)
            widget.tag_configure("del", background=theme.diff_del_bg, foreground=theme.diff_del_fg)
            widget.tag_configure("context", background=theme.bg_primary, foreground=theme.text_tertiary)
            widget.tag_configure("meta", background=theme.bg_secondary, foreground=theme.text_secondary)

        self._text.tag_configure("header", background=theme.diff_header_bg, foreground=theme.diff_header_fg)
        self._text.tag_configure("hunk", background=theme.diff_hunk_bg, foreground=theme.diff_hunk_fg)
        self._text.tag_configure("add", background=theme.diff_add_bg, foreground=theme.diff_add_fg)
        self._text.tag_configure("del", background=theme.diff_del_bg, foreground=theme.diff_del_fg)
        self._text.tag_configure("context", background=theme.bg_primary, foreground=theme.text_primary)
        self._text.tag_configure("meta", background=theme.bg_secondary, foreground=theme.text_secondary)

    def _set_widget_state(self, state: str) -> None:
        for widget in (self._old_gutter, self._new_gutter, self._text):
            widget.configure(state=state)

    def _clear_widgets(self) -> None:
        for widget in (self._old_gutter, self._new_gutter, self._text):
            widget.delete("1.0", tk.END)

    def _insert_row(self, old_no: str, new_no: str, text: str, tag: str) -> None:
        gutter_tag = tag if tag in {"header", "hunk", "add", "del"} else ("meta" if tag == "meta" else "context")
        self._old_gutter.insert(tk.END, f"{old_no:>5}\n" if old_no else "     \n", (gutter_tag, "gutter"))
        self._new_gutter.insert(tk.END, f"{new_no:>5}\n" if new_no else "     \n", (gutter_tag, "gutter"))
        self._text.insert(tk.END, text + "\n", tag)

    def _bind_copy_menu(self, widget: tk.Text) -> None:
        """Bind copy context menu to a text-like widget."""
        if widget.tk.call("tk", "windowingsystem") == "aqua":
            widget.bind("<Button-2>", self._show_copy_menu)
            widget.bind("<Control-1>", self._show_copy_menu)
        else:
            widget.bind("<Button-3>", self._show_copy_menu)

    def _format_file_header(self, raw_line: str) -> str:
        """Convert a raw diff header into a compact file title."""
        match = self._DIFF_HEADER_RE.match(raw_line)
        if not match:
            return raw_line
        old_path, new_path = match.groups()
        if old_path == new_path:
            return old_path
        return f"{old_path} -> {new_path}"

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard if there is anything to copy."""
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    def _copy_selection(self, event: Optional[tk.Event] = None) -> str:
        """Copy selected text from the focused diff pane."""
        widget = event.widget if event else self.focus_get()
        candidates = [widget, self._text, self._old_gutter, self._new_gutter]
        for candidate in candidates:
            if not isinstance(candidate, tk.Text):
                continue
            try:
                selection = candidate.get("sel.first", "sel.last")
            except tk.TclError:
                continue
            if selection:
                self._copy_to_clipboard(selection)
                return "break"
        return "break"

    def _copy_all(self) -> None:
        """Copy the rendered diff body without the gutters."""
        self._copy_to_clipboard(self._text.get("1.0", "end-1c"))

    def _show_copy_menu(self, event: tk.Event) -> str:
        """Show copy actions for the diff viewer."""
        event.widget.focus_set()
        self._copy_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _select_all(self, event: Optional[tk.Event] = None) -> str:
        """Select all rendered diff text."""
        self._text.tag_add(tk.SEL, "1.0", "end-1c")
        self._text.mark_set(tk.INSERT, "1.0")
        self._text.see("1.0")
        return "break"

    def set_content(self, content: str) -> None:
        """Set the diff content."""
        self._set_widget_state(tk.NORMAL)
        self._clear_widgets()

        old_line = 0
        new_line = 0
        current_file = ""
        pending_meta: list[str] = []
        file_header_shown = False
        rendered_anything = False

        def show_file_header() -> None:
            nonlocal file_header_shown, rendered_anything
            if not current_file or file_header_shown:
                return
            if rendered_anything:
                self._insert_row("", "", "", "meta")
            self._insert_row("", "", current_file, "header")
            for meta_line in pending_meta:
                self._insert_row("", "", meta_line, "meta")
            file_header_shown = True
            rendered_anything = True

        def flush_section(show_placeholder: bool = False) -> None:
            if current_file and not file_header_shown and (pending_meta or show_placeholder):
                show_file_header()
                if show_placeholder and not pending_meta:
                    self._insert_row("", "", "No textual line changes.", "meta")

        for raw_line in content.splitlines():
            if raw_line.startswith("diff --git "):
                flush_section()
                current_file = self._format_file_header(raw_line)
                pending_meta = []
                file_header_shown = False
                old_line = 0
                new_line = 0
                continue

            if raw_line.startswith("index ") or raw_line.startswith("---") or raw_line.startswith("+++"):
                continue

            if raw_line.startswith("new file mode "):
                pending_meta.append("New file")
                continue

            if raw_line.startswith("deleted file mode "):
                pending_meta.append("Deleted file")
                continue

            if raw_line.startswith("rename from "):
                pending_meta.append(raw_line)
                continue

            if raw_line.startswith("rename to "):
                pending_meta.append(raw_line)
                continue

            if raw_line.startswith("Binary files ") or raw_line.startswith("GIT binary patch"):
                pending_meta.append("Binary file changed")
                show_file_header()
                continue

            hunk_match = self._HUNK_RE.match(raw_line)
            if hunk_match:
                old_line = int(hunk_match.group(1))
                new_line = int(hunk_match.group(2))
                show_file_header()
                self._insert_row("", "", raw_line, "hunk")
                rendered_anything = True
                continue

            if raw_line.startswith("+") and not raw_line.startswith("+++"):
                show_file_header()
                self._insert_row("", str(new_line), "+ " + raw_line[1:], "add")
                new_line += 1
                rendered_anything = True
                continue

            if raw_line.startswith("-") and not raw_line.startswith("---"):
                show_file_header()
                self._insert_row(str(old_line), "", "- " + raw_line[1:], "del")
                old_line += 1
                rendered_anything = True
                continue

            if raw_line.startswith(" "):
                old_line += 1
                new_line += 1
                continue

            if raw_line.startswith("\\"):
                show_file_header()
                self._insert_row("", "", raw_line, "meta")
                rendered_anything = True
                continue

            if raw_line.strip():
                show_file_header()
                self._insert_row("", "", raw_line, "meta")
                rendered_anything = True

        flush_section(show_placeholder=not rendered_anything)

        if not rendered_anything and self._text.get("1.0", "end-1c").strip() == "":
            self._insert_row("", "", "No changed lines to display.", "meta")

        self._set_widget_state(tk.DISABLED)

    def clear(self) -> None:
        """Clear the diff viewer."""
        self._set_widget_state(tk.NORMAL)
        self._clear_widgets()
        self._set_widget_state(tk.DISABLED)

    def _on_vertical_scroll(self, *args) -> None:
        """Scroll all panes together."""
        self._old_gutter.yview(*args)
        self._new_gutter.yview(*args)
        self._text.yview(*args)

    def _on_text_yview(self, first: str, last: str) -> None:
        """Keep gutters aligned with main text scroll position."""
        self._old_gutter.yview_moveto(first)
        self._new_gutter.yview_moveto(first)
        for child in self.grid_slaves(row=0, column=3):
            child.set(first, last)

    def _on_mousewheel(self, event: tk.Event) -> str:
        """Scroll diff panes with mouse wheel."""
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self._on_vertical_scroll("scroll", delta, "units")
        return "break"

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        theme = ThemeManager.get_instance().theme
        self._old_gutter.configure(bg=theme.bg_secondary, fg=theme.text_tertiary, font=(theme.font_mono, theme.font_size_md))
        self._new_gutter.configure(bg=theme.bg_secondary, fg=theme.text_tertiary, font=(theme.font_mono, theme.font_size_md))
        self._text.configure(
            bg=theme.bg_primary,
            fg=theme.text_primary,
            selectbackground=theme.accent_primary,
            insertbackground=theme.text_primary,
            font=(theme.font_mono, theme.font_size_md),
        )
        self._apply_tags()


class FileListView(ttk.Frame):
    """
    Widget for displaying a list of files with status indicators.
    """

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self._files: list[FileStatus] = []
        self._on_select: Optional[Callable[[Optional[FileStatus]], Any]] = None

        self._tree = ttk.Treeview(self, columns=("status", "path"), show="headings", selectmode="extended")
        self._tree.heading("status", text="")
        self._tree.heading("path", text=tr("la_file"))
        self._tree.column("status", width=30, stretch=False)
        self._tree.column("path", width=300)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview, style="Vertical.TScrollbar")
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.bind("<<TreeviewSelect>>", self._handle_select)

    def _handle_select(self, event: tk.Event) -> None:
        """Handle selection change."""
        if self._on_select:
            selected = self.get_selected()
            self._on_select(selected[0] if selected else None)

    def set_files(self, files: list[FileStatus]) -> None:
        """Set the list of files."""
        self._files = files
        self._tree.delete(*self._tree.get_children())

        for file_status in files:
            status = file_status.staged_status or file_status.unstaged_status or "?"
            self._tree.insert("", tk.END, values=(status, file_status.display_name), tags=(status,))

        theme = ThemeManager.get_instance().theme
        self._tree.tag_configure("M", foreground=theme.status_warning)
        self._tree.tag_configure("A", foreground=theme.status_success)
        self._tree.tag_configure("D", foreground=theme.status_danger)
        self._tree.tag_configure("R", foreground=theme.status_info)
        self._tree.tag_configure("?", foreground=theme.text_tertiary)
        self._tree.tag_configure("U", foreground=theme.status_danger)

    def get_selected(self) -> list[FileStatus]:
        """Get selected files."""
        selection = self._tree.selection()
        indices = [self._tree.index(item) for item in selection]
        return [self._files[i] for i in indices if i < len(self._files)]

    def get_selected_paths(self) -> list[str]:
        """Get selected file paths."""
        return [file_status.path for file_status in self.get_selected()]

    def restore_selection(self, paths: list[str]) -> None:
        """Restore selection by file path after refreshing the list."""
        if not paths:
            return

        selected_items = []
        children = self._tree.get_children("")
        wanted = set(paths)
        for index, file_status in enumerate(self._files):
            if file_status.path in wanted and index < len(children):
                selected_items.append(children[index])

        if selected_items:
            self._tree.selection_set(selected_items)
            self._tree.focus(selected_items[0])

    def select_at_event(self, event: tk.Event) -> list[FileStatus]:
        """Select the row under the pointer and return current selection."""
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._tree.focus(item)
        return self.get_selected()

    def get_all(self) -> list[FileStatus]:
        """Get all files."""
        return self._files.copy()

    def clear(self) -> None:
        """Clear the list."""
        self._files = []
        self._tree.delete(*self._tree.get_children())

    def bind_context_menu(self, callback: Callable[[tk.Event], None]) -> None:
        """Bind context menu event."""
        if self._tree.tk.call("tk", "windowingsystem") == "aqua":
            self._tree.bind("<Button-2>", callback)
            self._tree.bind("<Control-1>", callback)
        else:
            self._tree.bind("<Button-3>", callback)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        theme = ThemeManager.get_instance().theme
        self._tree.tag_configure("M", foreground=theme.status_warning)
        self._tree.tag_configure("A", foreground=theme.status_success)
        self._tree.tag_configure("D", foreground=theme.status_danger)
        self._tree.tag_configure("R", foreground=theme.status_info)
        self._tree.tag_configure("?", foreground=theme.text_tertiary)
        self._tree.tag_configure("U", foreground=theme.status_danger)


class CommitListView(ttk.Frame):
    """
    Widget for displaying commit history with a dedicated graph canvas.
    """

    _ROW_HEIGHT = 20
    _LANE_SPACING = 11
    _GRAPH_PADDING = 6
    _NODE_RADIUS = 4

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self._commits: list[CommitInfo] = []
        self._nodes = []
        self._on_select: Optional[Callable[[Optional[CommitInfo]], Any]] = None
        self._on_reach_bottom: Optional[Callable[[], Any]] = None
        self._suspend_select_callback = False
        self._last_load_more_count = 0

        theme = ThemeManager.get_instance().theme
        self._graph_canvas = tk.Canvas(
            self,
            width=72,
            highlightthickness=0,
            bd=0,
            bg=theme.bg_primary,
        )
        self._tree = ttk.Treeview(
            self,
            columns=("message", "author", "date", "hash"),
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("message", text=tr("la_message"))
        self._tree.heading("author", text=tr("la_author"))
        self._tree.heading("date", text=tr("la_date"))
        self._tree.heading("hash", text=tr("la_hash"))

        self._tree.column("message", width=460)
        self._tree.column("author", width=140)
        self._tree.column("date", width=130)
        self._tree.column("hash", width=90)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._on_vertical_scroll, style="Vertical.TScrollbar")
        self._tree.configure(yscrollcommand=self._on_tree_yview)

        self._graph_canvas.pack(side=tk.LEFT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.bind("<<TreeviewSelect>>", self._handle_select)
        self._tree.bind("<Configure>", lambda e: self._redraw_graph())
        self._graph_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._tree.bind("<MouseWheel>", self._on_mousewheel)
        self._graph_canvas.bind("<Button-4>", self._on_mousewheel)
        self._graph_canvas.bind("<Button-5>", self._on_mousewheel)
        self._tree.bind("<Button-4>", self._on_mousewheel)
        self._tree.bind("<Button-5>", self._on_mousewheel)

    def _graph_palette(self) -> list[str]:
        """Get graph palette derived from current theme."""
        theme = ThemeManager.get_instance().theme
        return [
            theme.accent_primary,
            theme.status_success,
            theme.status_danger,
            theme.status_warning,
            theme.status_info,
            theme.accent_secondary,
            theme.border_focus,
            theme.text_secondary,
        ]

    def _lane_x(self, lane: int) -> int:
        return self._GRAPH_PADDING + lane * self._LANE_SPACING

    def _row_y(self, index: int) -> int:
        return index * self._ROW_HEIGHT + self._ROW_HEIGHT // 2

    def _draw_curve(self, x1: int, y1: int, x2: int, y2: int, color: str, width: int = 2) -> None:
        """Draw a smooth connector between two points."""
        mid_y = (y1 + y2) / 2
        self._graph_canvas.create_line(
            x1,
            y1,
            x1,
            mid_y,
            x2,
            mid_y,
            x2,
            y2,
            fill=color,
            width=width,
            smooth=True,
            splinesteps=20,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
        )

    def _handle_select(self, event: tk.Event) -> None:
        """Handle selection change."""
        self._redraw_graph()
        if self._suspend_select_callback:
            return
        if self._on_select:
            self._on_select(self.get_selected())

    def set_commits(self, commits: list[CommitInfo]) -> None:
        """Set the commit list."""
        self._commits = [commit for commit in commits if commit.hash]
        self._nodes = build_graph(self._commits)
        self._tree.delete(*self._tree.get_children())

        for commit in self._commits:
            refs = ""
            if commit.hash and commit.refs:
                refs_str = ", ".join(commit.refs[:2])
                if len(refs_str) > 28:
                    refs_str = refs_str[:25] + "..."
                refs = f"[{refs_str}] "

            message = refs + truncate(commit.subject, 96)
            self._tree.insert("", tk.END, values=(message, commit.author, commit.display_date, commit.short_hash))

        self._update_graph_geometry()
        self._redraw_graph()

    def _update_graph_geometry(self) -> None:
        """Update canvas width and scroll region."""
        max_lane = max((node.lane for node in self._nodes), default=0)
        extra_lanes = [
            lane
            for node in self._nodes
            for lane in (node.pass_through_lanes or []) + (node.merge_from_lanes or []) + (node.branch_to_lanes or [])
        ]
        fold_lanes = [
            lane
            for node in self._nodes
            for fold in (node.fold_lanes or [])
            for lane in fold
        ]
        if extra_lanes:
            max_lane = max(max_lane, max(extra_lanes))
        if fold_lanes:
            max_lane = max(max_lane, max(fold_lanes))

        width = self._GRAPH_PADDING * 2 + (max_lane + 1) * self._LANE_SPACING
        self._graph_canvas.configure(width=max(width, 44))
        total_height = max(len(self._commits), 1) * self._ROW_HEIGHT
        self._graph_canvas.configure(scrollregion=(0, 0, max(width, 44), total_height))

    def _redraw_graph(self) -> None:
        """Redraw the commit graph."""
        self._graph_canvas.delete("all")
        if not self._commits:
            return

        theme = ThemeManager.get_instance().theme
        self._graph_canvas.configure(bg=theme.bg_primary)

        selected = self.get_selected()
        selected_hash = selected.hash if selected else None
        palette = self._graph_palette()

        total_height = max(len(self._commits), 1) * self._ROW_HEIGHT

        for index, node in enumerate(self._nodes):
            commit = self._commits[index]
            y = self._row_y(index)
            top = y - self._ROW_HEIGHT // 2
            bottom = y + self._ROW_HEIGHT // 2
            lane_color = palette[get_lane_color_index(node.lane) % len(palette)]
            x = self._lane_x(node.lane)

            next_node = self._nodes[index + 1] if index + 1 < len(self._nodes) else None
            next_y = self._row_y(index + 1) if next_node else bottom
            first_parent = commit.parents[0] if commit.parents else None
            first_parent_is_next = bool(first_parent and next_node and next_node.commit_hash == first_parent)
            branch_target_lane = node.branch_to_lanes[0] if node.branch_to_lanes else node.lane

            if index > 0:
                self._graph_canvas.create_line(x, top, x, y, fill=lane_color, width=2, capstyle=tk.ROUND)

            fold_map = {old_lane: new_lane for old_lane, new_lane in (node.fold_lanes or [])}
            for lane in node.pass_through_lanes or []:
                pass_color = palette[get_lane_color_index(lane) % len(palette)]
                pass_x = self._lane_x(lane)
                if lane in fold_map:
                    fold_x = self._lane_x(fold_map[lane])
                    self._graph_canvas.create_line(pass_x, top, pass_x, y, fill=pass_color, width=2, capstyle=tk.ROUND)
                    if fold_x == pass_x:
                        self._graph_canvas.create_line(pass_x, y, pass_x, bottom, fill=pass_color, width=2, capstyle=tk.ROUND)
                    else:
                        self._draw_curve(pass_x, y, fold_x, bottom, pass_color)
                else:
                    self._graph_canvas.create_line(pass_x, top, pass_x, bottom, fill=pass_color, width=2, capstyle=tk.ROUND)

            if node.parents:
                target_x = self._lane_x(branch_target_lane)
                target_y = next_y if first_parent_is_next and branch_target_lane == (next_node.lane if next_node else branch_target_lane) else bottom
                if target_x == x:
                    self._graph_canvas.create_line(x, y, x, target_y, fill=lane_color, width=2, capstyle=tk.ROUND)
                else:
                    self._draw_curve(x, y, target_x, target_y, lane_color)

            for merge_lane in node.merge_from_lanes or []:
                merge_color = palette[get_lane_color_index(merge_lane) % len(palette)]
                merge_x = self._lane_x(merge_lane)
                self._draw_curve(x, y, merge_x, bottom, merge_color)

            radius = self._NODE_RADIUS + (1 if commit.hash == selected_hash else 0)
            self._graph_canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=lane_color,
                outline="#ffffff" if commit.hash == selected_hash else theme.bg_primary,
                width=2 if commit.hash == selected_hash else 1,
            )

    def clear(self) -> None:
        """Clear the list."""
        self._commits = []
        self._nodes = []
        self._last_load_more_count = 0
        self._tree.delete(*self._tree.get_children())
        self._graph_canvas.delete("all")

    def get_selected(self) -> Optional[CommitInfo]:
        """Get the selected commit."""
        selected = self._tree.selection()
        if not selected:
            return None
        idx = self._tree.index(selected[0])
        if idx < len(self._commits):
            return self._commits[idx]
        return None

    def get_selected_hash(self) -> Optional[str]:
        """Get the currently selected commit hash."""
        selected = self.get_selected()
        return selected.hash if selected else None

    def get_top_visible_commit_hash(self) -> Optional[str]:
        """Get the hash of the first visible commit row."""
        item = self._tree.identify_row(1)
        if not item:
            children = self._tree.get_children("")
            item = children[0] if children else ""
        if not item:
            return None
        idx = self._tree.index(item)
        if 0 <= idx < len(self._commits):
            return self._commits[idx].hash
        return None

    def reset_load_more_state(self) -> None:
        """Allow a fresh load-more cycle after a full refresh."""
        self._last_load_more_count = 0

    def restore_view(self, top_hash: Optional[str] = None, selected_hash: Optional[str] = None) -> None:
        """Restore selection and scroll position after reloading history."""
        if selected_hash:
            self._select_commit_by_hash(selected_hash, notify=False)
        if top_hash:
            self._scroll_to_commit(top_hash)

    def select_at_event(self, event: tk.Event) -> Optional[CommitInfo]:
        """Select the row under the pointer and return its commit."""
        item = self._tree.identify_row(event.y)
        if not item:
            return self.get_selected()
        self._tree.selection_set(item)
        self._tree.focus(item)
        self._redraw_graph()
        return self.get_selected()

    def _on_vertical_scroll(self, *args) -> None:
        """Scroll tree and graph together."""
        self._tree.yview(*args)
        self._graph_canvas.yview(*args)

    def _on_tree_yview(self, first: str, last: str) -> None:
        """Keep graph scroll aligned with the tree."""
        self._graph_canvas.yview_moveto(first)
        for child in self.pack_slaves():
            if isinstance(child, ttk.Scrollbar):
                child.set(first, last)
        self._maybe_request_more(last)

    def _on_mousewheel(self, event: tk.Event) -> str:
        """Scroll graph and tree with mouse wheel."""
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self._on_vertical_scroll("scroll", delta, "units")
        return "break"

    def _index_for_commit_hash(self, commit_hash: str) -> Optional[int]:
        """Find commit index by hash."""
        for index, commit in enumerate(self._commits):
            if commit.hash == commit_hash:
                return index
        return None

    def _select_commit_by_hash(self, commit_hash: str, notify: bool = True) -> bool:
        """Select a commit row by hash."""
        idx = self._index_for_commit_hash(commit_hash)
        children = self._tree.get_children("")
        if idx is None or idx >= len(children):
            return False

        if not notify:
            self._suspend_select_callback = True
        item = children[idx]
        self._tree.selection_set(item)
        self._tree.focus(item)
        self._redraw_graph()
        if not notify:
            self.after_idle(self._resume_select_callback)
        return True

    def _scroll_to_commit(self, commit_hash: str) -> bool:
        """Scroll list so the specified commit stays near the current viewport."""
        idx = self._index_for_commit_hash(commit_hash)
        if idx is None:
            return False
        total = max(len(self._commits), 1)
        self._tree.yview_moveto(min(max(idx / total, 0.0), 1.0))
        return True

    def _resume_select_callback(self) -> None:
        """Re-enable selection callback after a silent selection restore."""
        self._suspend_select_callback = False

    def _maybe_request_more(self, last: str) -> None:
        """Request more history when the user reaches the bottom of the list."""
        if not self._on_reach_bottom or not self._commits:
            return
        try:
            last_visible = float(last)
        except (TypeError, ValueError):
            return
        if last_visible >= 0.98 and self._last_load_more_count != len(self._commits):
            self._last_load_more_count = len(self._commits)
            self.after_idle(self._on_reach_bottom)

    def bind_context_menu(self, callback: Callable[[tk.Event], None]) -> None:
        """Bind context menu event."""
        if self._tree.tk.call("tk", "windowingsystem") == "aqua":
            self._tree.bind("<Button-2>", callback)
            self._tree.bind("<Control-1>", callback)
            self._graph_canvas.bind("<Button-2>", callback)
            self._graph_canvas.bind("<Control-1>", callback)
        else:
            self._tree.bind("<Button-3>", callback)
            self._graph_canvas.bind("<Button-3>", callback)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        theme = ThemeManager.get_instance().theme
        self._graph_canvas.configure(bg=theme.bg_primary)
        self._redraw_graph()


class BranchTreeView(ttk.Frame):
    """
    Widget for displaying branches in a tree structure.
    """

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self._tree = ttk.Treeview(self, show="tree", selectmode="browse")
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview, style="Vertical.TScrollbar")
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._local_id = self._tree.insert("", tk.END, text=tr("la_local_branches"), open=True)
        self._remote_id = self._tree.insert("", tk.END, text=tr("la_remote_branches"), open=True)
        self._tree.tag_configure("current", font=("TkDefaultFont", 9, "bold"))

    def set_branches(self, branches: list[BranchInfo]) -> None:
        """Set the branch list."""
        for child in self._tree.get_children(self._local_id):
            self._tree.delete(child)
        for child in self._tree.get_children(self._remote_id):
            self._tree.delete(child)

        for branch in branches:
            parent = self._remote_id if branch.is_remote else self._local_id
            text = branch.display_name
            tags = ("current",) if branch.is_current else ()
            if branch.is_current:
                text = "* " + text
            self._tree.insert(parent, tk.END, text=text, tags=tags)

    def get_selected(self) -> Optional[str]:
        """Get selected branch name."""
        selection = self._tree.selection()
        if not selection:
            return None
        return self._get_branch_name_from_item(selection[0])

    def _get_branch_name_from_item(self, item: str) -> Optional[str]:
        if item in (self._local_id, self._remote_id):
            return None

        text = self._tree.item(item, "text")
        if text.startswith("* "):
            text = text[2:]
        if " [" in text:
            text = text.split(" [", 1)[0]
        return text

    def select_at_event(self, event: tk.Event) -> Optional[str]:
        """Select the row under the pointer and return its branch name."""
        item = self._tree.identify_row(event.y)
        if not item:
            return self.get_selected()
        self._tree.selection_set(item)
        self._tree.focus(item)
        return self._get_branch_name_from_item(item)

    def bind_context_menu(self, callback: Callable[[tk.Event], None]) -> None:
        """Bind context menu event."""
        if self._tree.tk.call("tk", "windowingsystem") == "aqua":
            self._tree.bind("<Button-2>", callback)
            self._tree.bind("<Control-1>", callback)
        else:
            self._tree.bind("<Button-3>", callback)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        self._tree.tag_configure("current", font=("TkDefaultFont", 9, "bold"))


class CommitPanel(ttk.Frame):
    """
    Panel for entering commit messages.
    """

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        author_frame = ttk.Frame(self)
        author_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(author_frame, text=tr("la_author") + ":").pack(side=tk.LEFT)
        self._author_label = ttk.Label(author_frame, text="")
        self._author_label.pack(side=tk.LEFT, padx=5)

        theme = ThemeManager.get_instance().theme
        self._message = tk.Text(
            self,
            height=4,
            wrap=tk.WORD,
            font=(theme.font_mono, theme.font_size_md),
            bg=theme.bg_primary,
            fg=theme.text_primary,
            insertbackground=theme.text_primary,
            selectbackground=theme.accent_primary,
        )
        self._message.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self._push_var = tk.BooleanVar(value=False)
        self._push_chk = ttk.Checkbutton(btn_frame, text=tr("la_push_immediately"), variable=self._push_var)
        self._push_chk.pack(side=tk.LEFT)

        self.commit_btn = ttk.Button(btn_frame, text=tr("la_commit"))
        self.commit_btn.pack(side=tk.RIGHT)

    def set_author(self, author: str) -> None:
        """Set the author label."""
        self._author_label.configure(text=author)

    def get_message(self) -> str:
        """Get the commit message."""
        return self._message.get("1.0", tk.END).strip()

    def clear_message(self) -> None:
        """Clear the commit message."""
        self._message.delete("1.0", tk.END)

    @property
    def push_immediately(self) -> bool:
        """Check if push immediately is checked."""
        return self._push_var.get()

    def set_push_immediately(self, value: bool) -> None:
        """Set push immediately state."""
        self._push_var.set(value)

    def bind_push_toggled(self, callback: Callable[[bool], None]) -> None:
        """Bind callback for push checkbox toggle."""

        def _on_toggle() -> None:
            callback(self._push_var.get())

        self._push_chk.configure(command=_on_toggle)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
        theme = ThemeManager.get_instance().theme
        self._message.configure(bg=theme.bg_primary, fg=theme.text_primary, font=(theme.font_mono, theme.font_size_md))


class TagTreeView(ttk.Frame):
    """
    Widget for displaying tags in the sidebar.
    """

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self._tags: list[TagInfo] = []
        self._on_select: Optional[Callable[[Optional[str]], Any]] = None

        self._tree = ttk.Treeview(self, show="tree", selectmode="browse", height=6)
        self._tree.pack(fill=tk.BOTH, expand=True)
        self._root_id = self._tree.insert("", tk.END, text=tr("la_tags", "Tags"), open=True)
        self._tree.bind("<<TreeviewSelect>>", self._handle_select)

    def set_tags(self, tags: list[TagInfo]) -> None:
        """Set the tag list."""
        self._tags = tags
        for child in self._tree.get_children(self._root_id):
            self._tree.delete(child)
        for tag in tags:
            self._tree.insert(self._root_id, tk.END, text=truncate(tag.display_name, 34), values=(tag.name,))

    def get_selected(self) -> Optional[str]:
        """Get selected tag name."""
        selection = self._tree.selection()
        if not selection:
            return None
        item = selection[0]
        if item == self._root_id:
            return None
        values = self._tree.item(item, "values")
        if values:
            return str(values[0])
        return None

    def select_at_event(self, event: tk.Event) -> Optional[str]:
        """Select the row under the pointer and return its tag name."""
        item = self._tree.identify_row(event.y)
        if not item:
            return self.get_selected()
        self._tree.selection_set(item)
        self._tree.focus(item)
        return self.get_selected()

    def _handle_select(self, event: tk.Event) -> None:
        """Handle selection change."""
        if self._on_select:
            self._on_select(self.get_selected())

    def bind_context_menu(self, callback: Callable[[tk.Event], None]) -> None:
        """Bind context menu event."""
        if self._tree.tk.call("tk", "windowingsystem") == "aqua":
            self._tree.bind("<Button-2>", callback)
            self._tree.bind("<Control-1>", callback)
        else:
            self._tree.bind("<Button-3>", callback)

    def refresh_theme(self) -> None:
        """Update colors from current theme."""


class StashSidebarView(ttk.Frame):
    """
    Widget for displaying stashes in the sidebar.
    """

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self._stashes: list = []
        self._on_select: Optional[Callable[[Optional[int]], Any]] = None

        self._tree = ttk.Treeview(self, show="tree", selectmode="browse", height=5)
        self._tree.pack(fill=tk.BOTH, expand=True)
        self._root_id = self._tree.insert("", tk.END, text=tr("la_stashes", "Stashes"), open=True)
        self._tree.bind("<<TreeviewSelect>>", self._handle_select)

    def set_stashes(self, stashes: list) -> None:
        """Set the stash list."""
        self._stashes = stashes
        for child in self._tree.get_children(self._root_id):
            self._tree.delete(child)
        for stash in stashes:
            label = f"{{{stash.index}}}: {stash.message}"
            self._tree.insert(self._root_id, tk.END, text=truncate(label, 30), values=(stash.index,))

    def get_selected_index(self) -> Optional[int]:
        """Get selected stash index."""
        selection = self._tree.selection()
        if not selection:
            return None
        item = selection[0]
        if item == self._root_id:
            return None
        values = self._tree.item(item, "values")
        if values:
            return int(values[0])
        return None

    def _handle_select(self, event: tk.Event) -> None:
        """Handle selection change."""
        if self._on_select:
            self._on_select(self.get_selected_index())

    def refresh_theme(self) -> None:
        """Update colors from current theme."""
