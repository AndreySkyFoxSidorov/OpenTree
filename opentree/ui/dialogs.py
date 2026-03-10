"""
Dialog windows for OpenTree.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional

from opentree.core.i18n import tr


class OpenRepoDialog:
    """Dialog for opening a repository."""
    
    @staticmethod
    def show(parent: tk.Widget) -> Optional[Path]:
        """Show folder selection dialog."""
        path = filedialog.askdirectory(
            parent=parent,
            title=tr("la_select_repo_folder"),
            mustexist=True
        )
        if path:
            return Path(path)
        return None


class NewBranchDialog(tk.Toplevel):
    """Dialog for creating a new branch."""

    def __init__(
        self,
        parent: tk.Widget,
        title: Optional[str] = None,
        prompt: Optional[str] = None,
        initial_name: str = "",
    ) -> None:
        super().__init__(parent)
        self.title(title or tr("la_create_branch"))
        self.transient(parent)
        self.grab_set()

        self._result: Optional[str] = None

        self.minsize(350, 150)
        self.resizable(True, False)
        self.after_idle(self._center_window)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=prompt or (tr("la_branch_name") + ":")).pack(anchor=tk.W)

        self._entry = ttk.Entry(frame, width=40)
        if initial_name:
            self._entry.insert(0, initial_name)
        self._entry.pack(fill=tk.X, pady=5)
        self._entry.focus_set()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text=tr("la_cancel"), command=self._cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_create"), command=self._create).pack(side=tk.RIGHT)

        self.bind("<Return>", lambda e: self._create())
        self.bind("<Escape>", lambda e: self._cancel())

    def _create(self) -> None:
        name = self._entry.get().strip()
        if name:
            self._result = name
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()

    def _center_window(self) -> None:
        """Center window on parent."""
        self.update_idletasks()

        w = self.winfo_reqwidth() + 20
        h = self.winfo_reqheight() + 20
        mw, mh = self.minsize()
        if w < mw:
            w = mw
        if h < mh:
            h = mh

        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        if y < 0:
            y = 0

        self.geometry(f"{w}x{h}+{x}+{y}")

    def wait(self) -> Optional[str]:
        """Wait for dialog close and return branch name."""
        self.wait_window()
        return self._result


class MergeDialog(tk.Toplevel):
    """Dialog for merging a branch."""
    
    def __init__(self, parent: tk.Widget, branches: list[str], current: str) -> None:
        super().__init__(parent)
        self.title(tr("la_merge_branch", "Merge Branch"))
        self.transient(parent)
        self.grab_set()
        
        self._result: Optional[str] = None
        
        # Center on parent
        # Dynamic sizing
        self.minsize(400, 180)
        self.resizable(True, False)
        
        # We'll center after widgets are packed
        self.after_idle(self._center_window)
        
        # Content
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=tr("la_merge_into", "Merge into") + f" {current}:").pack(anchor=tk.W)
        
        # Filter out current branch
        choices = [b for b in branches if b != current]
        
        self._combo = ttk.Combobox(frame, values=choices, state="readonly", width=40)
        self._combo.pack(fill=tk.X, pady=5)
        if choices:
            self._combo.current(0)
            
        # Options
        self._squash = tk.BooleanVar()
        ttk.Checkbutton(frame, text=tr("la_squash", "Squash commits"), 
                       variable=self._squash).pack(anchor=tk.W, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text=tr("la_cancel"), command=self._cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_merge"), command=self._merge).pack(side=tk.RIGHT)
        
        # Bindings
        self.bind("<Return>", lambda e: self._merge())
        self.bind("<Escape>", lambda e: self._cancel())
    
    def _merge(self) -> None:
        selection = self._combo.get()
        if selection:
            self._result = (selection, self._squash.get())
            self.destroy()
    
    def _cancel(self) -> None:
        self.destroy()
    

    def _center_window(self) -> None:
        """Center window on parent."""
        self.update_idletasks()
        
        # Get requested size with some padding
        w = self.winfo_reqwidth() + 20
        h = self.winfo_reqheight() + 20
        
        # Enforce minsize
        mw, mh = self.minsize()
        if w < mw: w = mw
        if h < mh: h = mh
            
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        
        if y < 0: y = 0
        
        self.geometry(f"{w}x{h}+{x}+{y}")

    def wait(self) -> Optional[tuple[str, bool]]:
        self.wait_window()
        return self._result


class CreateTagDialog(tk.Toplevel):
    """Dialog for creating a tag."""

    def __init__(self, parent: tk.Widget, target_label: str = "HEAD") -> None:
        super().__init__(parent)
        self.title(tr("la_create_tag", "Create Tag"))
        self.transient(parent)
        self.grab_set()

        self._result: Optional[tuple[str, str, bool]] = None

        self.minsize(420, 220)
        self.resizable(True, False)
        self.after_idle(self._center_window)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=tr("la_tag_name", "Tag name") + ":").pack(anchor=tk.W)
        self._name = ttk.Entry(frame, width=42)
        self._name.pack(fill=tk.X, pady=(5, 10))
        self._name.focus_set()

        ttk.Label(frame, text=tr("la_target", "Target") + f": {target_label}").pack(anchor=tk.W)

        ttk.Label(frame, text=tr("la_tag_message", "Annotation message (optional)") + ":").pack(anchor=tk.W, pady=(10, 0))
        self._message = tk.Text(frame, height=4, wrap=tk.WORD)
        self._message.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self._force = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text=tr("la_force_replace_tag", "Replace existing tag"), variable=self._force).pack(
            anchor=tk.W,
            pady=(10, 0),
        )

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text=tr("la_cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_create", "Create"), command=self._create).pack(side=tk.RIGHT)

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-Return>", lambda e: self._create())

    def _create(self) -> None:
        name = self._name.get().strip()
        if not name:
            return
        message = self._message.get("1.0", tk.END).strip()
        self._result = (name, message, self._force.get())
        self.destroy()

    def _center_window(self) -> None:
        """Center window on parent."""
        self.update_idletasks()
        w = max(self.winfo_reqwidth() + 20, self.minsize()[0])
        h = max(self.winfo_reqheight() + 20, self.minsize()[1])
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        if y < 0:
            y = 0
        self.geometry(f"{w}x{h}+{x}+{y}")

    def wait(self) -> Optional[tuple[str, str, bool]]:
        """Wait for dialog close and return tag parameters."""
        self.wait_window()
        return self._result


class ResetDialog(tk.Toplevel):
    """Dialog for selecting reset mode."""

    def __init__(self, parent: tk.Widget, target_label: str) -> None:
        super().__init__(parent)
        self.title(tr("la_reset", "Reset"))
        self.transient(parent)
        self.grab_set()

        self._result: Optional[str] = None
        self._mode = tk.StringVar(value="mixed")

        self.minsize(420, 220)
        self.resizable(True, False)
        self.after_idle(self._center_window)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=tr("la_reset_target", "Reset current branch to") + f" {target_label}?").pack(
            anchor=tk.W,
            pady=(0, 10),
        )
        ttk.Radiobutton(
            frame,
            text=tr("la_reset_soft", "Soft: keep index and working tree"),
            variable=self._mode,
            value="soft",
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            frame,
            text=tr("la_reset_mixed", "Mixed: keep working tree, reset index"),
            variable=self._mode,
            value="mixed",
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            frame,
            text=tr("la_reset_hard", "Hard: discard index and working tree changes"),
            variable=self._mode,
            value="hard",
        ).pack(anchor=tk.W, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_frame, text=tr("la_cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_reset", "Reset"), command=self._confirm).pack(side=tk.RIGHT)

        self.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self.destroy())

    def _confirm(self) -> None:
        self._result = self._mode.get()
        self.destroy()

    def _center_window(self) -> None:
        """Center window on parent."""
        self.update_idletasks()
        w = max(self.winfo_reqwidth() + 20, self.minsize()[0])
        h = max(self.winfo_reqheight() + 20, self.minsize()[1])
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        if y < 0:
            y = 0
        self.geometry(f"{w}x{h}+{x}+{y}")

    def wait(self) -> Optional[str]:
        """Wait for dialog close and return reset mode."""
        self.wait_window()
        return self._result


class StashDialog(tk.Toplevel):
    """Dialog for managing stashes."""
    
    def __init__(self, parent: tk.Widget, stashes: list) -> None:
        super().__init__(parent)
        self.title(tr("la_stash_manager", "Stash Manager"))
        self.transient(parent)
        self.grab_set()
        
        self._result: Optional[tuple[str, any]] = None
        self._stashes = stashes
        
        self._stashes = stashes
        
        # Dynamic sizing
        self.minsize(600, 400)
        
        # We'll center after widgets are packed
        self.after_idle(self._center_window)
        
        # Main layout
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Stash list
        list_frame = ttk.LabelFrame(paned, text=tr("la_stashes", "Stashes"))
        paned.add(list_frame, weight=1)
        
        columns = ("index", "branch", "message")
        self._tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self._tree.heading("index", text="Index")
        self._tree.heading("branch", text="Branch")
        self._tree.heading("message", text="Message")
        self._tree.column("index", width=50, stretch=False)
        self._tree.column("branch", width=100)
        self._tree.column("message", width=300)
        
        scr = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scr.set)
        
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate list
        for stash in stashes:
            self._tree.insert("", tk.END, values=(stash.index, stash.branch or "", stash.message))
            
        # Toolbar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text=tr("la_stash_changes", "Stash Changes"), 
                  command=self._stash_push).pack(side=tk.LEFT)
        
        ttk.Frame(btn_frame).pack(side=tk.LEFT, expand=True) # Spacer
        
        ttk.Button(btn_frame, text=tr("la_pop", "Pop"), command=self._pop).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_apply", "Apply"), command=self._apply).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_drop", "Drop"), command=self._drop).pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text=tr("la_close"), command=self._close).pack(side=tk.RIGHT, padx=20)
        
        self.bind("<Escape>", lambda e: self._close())

    def _get_selected_index(self) -> Optional[int]:
        item = self._tree.selection()
        if item:
            return int(self._tree.item(item[0])["values"][0])
        return None

    def _stash_push(self) -> None:
        # Prompt for message
        msg = tk.StringVar()
        
        def push():
            self._result = ("push", msg.get())
            self.destroy()
            
        dialog = tk.Toplevel(self)
        dialog.title(tr("la_stash_message", "Stash Message"))
        # Center this dialog relative to the stash dialog
        geom = self.geometry() # e.g. "600x400+100+100"
        
        dialog.minsize(400, 120)
        # Simple center on parent
        try:
             x = self.winfo_rootx() + (self.winfo_width() - 400) // 2
             y = self.winfo_rooty() + (self.winfo_height() - 120) // 2
             dialog.geometry(f"+{x}+{y}")
        except:
             pass
        
        ttk.Label(dialog, text="Message (optional):").pack(padx=10, pady=10, anchor=tk.W)
        entry = ttk.Entry(dialog, textvariable=msg, width=50)
        entry.pack(padx=10, fill=tk.X)
        entry.focus_set()
        
        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btns, text="Stash", command=push).pack(side=tk.RIGHT)
        
        dialog.transient(self)
        dialog.grab_set()

    def _pop(self) -> None:
        idx = self._get_selected_index()
        if idx is not None:
             self._result = ("pop", idx)
             self.destroy()

    def _apply(self) -> None:
        idx = self._get_selected_index()
        if idx is not None:
             self._result = ("apply", idx)
             self.destroy()

    def _drop(self) -> None:
        idx = self._get_selected_index()
        if idx is not None:
             if messagebox.askyesno("Drop Stash", "Are you sure you want to drop this stash?"):
                 self._result = ("drop", idx)
                 self.destroy()

    def _close(self) -> None:
        self.destroy()

    def _center_window(self) -> None:
        """Center window on parent."""
        self.update_idletasks()
        
        w = self.winfo_reqwidth() + 20
        h = self.winfo_reqheight() + 20
        
        # Enforce minsize
        mw, mh = self.minsize()
        if w < mw: w = mw
        if h < mh: h = mh
            
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        
        if y < 0: y = 0
        
        self.geometry(f"{w}x{h}+{x}+{y}")

    def wait(self) -> Optional[tuple[str, any]]:
        self.wait_window()
        return self._result



class ConfirmDialog:
    """Confirmation dialog."""
    
    @staticmethod
    def show(parent: tk.Widget, title: str, message: str,
             is_destructive: bool = False) -> bool:
        """Show confirmation dialog."""
        if is_destructive:
            return messagebox.askyesno(
                title=title,
                message=message,
                icon=messagebox.WARNING,
                parent=parent
            )
        return messagebox.askyesno(title=title, message=message, parent=parent)


class ErrorDialog:
    """Error dialog."""
    
    @staticmethod
    def show(parent: tk.Widget, title: str, message: str,
             details: str = "") -> None:
        """Show error dialog."""
        full_message = message
        if details:
            full_message += f"\n\nDetails:\n{details}"
        messagebox.showerror(title=title, message=full_message, parent=parent)


class InfoDialog:
    """Information dialog."""
    
    @staticmethod
    def show(parent: tk.Widget, title: str, message: str) -> None:
        """Show info dialog."""
        messagebox.showinfo(title=title, message=message, parent=parent)


class AboutDialog(tk.Toplevel):
    """About dialog."""
    
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title(tr("la_about_opentree"))
        self.transient(parent)
        self.grab_set()
        
        self.grab_set()
        
        # Dynamic sizing
        self.resizable(False, False)
        self.after_idle(self._center_window)
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            frame,
            text="OpenTree",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=(0, 5))
        
        # Version
        from opentree import __version__
        version_label = ttk.Label(frame, text=f"Version {__version__}")
        version_label.pack()
        
        # Description
        desc = ttk.Label(
            frame,
            text="A lightweight cross-platform Git GUI\nbuilt with Python and Tkinter.",
            justify=tk.CENTER
        )
        desc.pack(pady=15)
        
        # Copyright
        copyright_label = ttk.Label(
            frame,
            text="© 2024 OpenTree Contributors",
            foreground="#666666"
        )
        copyright_label.pack()
        
        # Close button
        ttk.Button(frame, text=tr("la_close"), command=self.destroy).pack(pady=15)
        
        self.bind("<Escape>", lambda e: self.destroy())


    def _center_window(self) -> None:
        """Center window on parent."""
        self.update_idletasks()
        
        # Get requested size with extra padding
        w = self.winfo_reqwidth() + 20
        h = self.winfo_reqheight() + 20
        
        # Enforce minsize
        mw, mh = self.minsize()
        if w < mw: w = mw
        if h < mh: h = mh
            
        try:
            x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
            y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
            
            if y < 0: y = 0
            self.geometry(f"{w}x{h}+{x}+{y}")
        except:
             pass

class GitNotFoundDialog(tk.Toplevel):
    """Dialog shown when git is not found."""
    
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title(tr("la_git_not_found"))
        self.transient(parent)
        self.grab_set()
        
        self._result: Optional[str] = None
        
        self._result: Optional[str] = None
        
        # Dynamic sizing
        self.minsize(450, 250)
        self.resizable(True, True)
        self.after_idle(self._center_window)
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="Git executable was not found in your PATH.",
            font=("Segoe UI", 11)
        ).pack(pady=(0, 10))
        
        ttk.Label(
            frame,
            text="Please install Git or specify the path to git.exe:"
        ).pack(anchor=tk.W)
        
        # Path entry
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=tk.X, pady=10)
        
        self._path_entry = ttk.Entry(path_frame)
        self._path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(path_frame, text=tr("la_browse"), command=self._browse).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Exit", command=self._exit).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="OK", command=self._ok).pack(side=tk.RIGHT)
    
    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Git Executable",
            filetypes=[("Executables", "*.exe"), ("All Files", "*.*")]
        )
        if path:
            self._path_entry.delete(0, tk.END)
            self._path_entry.insert(0, path)
    
    def _ok(self) -> None:
        path = self._path_entry.get().strip()
        if path:
            self._result = path
        self.destroy()
    
    def _exit(self) -> None:
        self.destroy()
    
    def _center_window(self) -> None:
        """Center window on parent."""
        self.update_idletasks()
        
        # Auto-size
        self.geometry("")
        self.update_idletasks()
        
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        
        # Enforce minsize
        mw, mh = self.minsize()
        if w < mw: w = mw
        if h < mh: h = mh
            
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        
        if y < 0: y = 0
        
        self.geometry(f"{w}x{h}+{x}+{y}")



    def wait(self) -> Optional[str]:
        self.wait_window()
        return self._result
