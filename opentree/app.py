"""
OpenTree main application controller.

Coordinates between UI components and Git operations.
"""

import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable, Dict

from opentree.core.models import RepoInfo, CommandResult
from opentree.core.state import AppState
from opentree.core.events import events, Events
from opentree.core.i18n import tr
from opentree.core.session import RepoSession
from opentree.ui.dialogs import (
    OpenRepoDialog,
    GitNotFoundDialog,
    AboutDialog,
    ConfirmDialog,
)
from opentree.ui.settings_dialog import SettingsDialog
from opentree.utils.paths import is_valid_repo, find_repo_root
from opentree.utils.platform import is_git_available


class OpenTreeApp:
    """
    Main application class for OpenTree.
    
    Manages the Tk root window and multiple repository sessions (tabs).
    """
    
    def __init__(self) -> None:
        # Enable DPI awareness on Windows
        self._enable_dpi_awareness()
        
        self._root = tk.Tk()
        self._root.title("Open Tree - Open Source Git Utility")
        
        # Set application icon
        try:
            icon_path = Path(__file__).parent / "icons" / "app.ico"
            if icon_path.exists():
                self._root.iconbitmap(str(icon_path))
        except Exception:
            pass
            
        self._root.minsize(900, 600)
        
        # Default starting size (larger than min, but not fixed)
        # We will let state restore handle specific position/size if available
        # Otherwise we start with a reasonable default
        if not AppState.load().window.width:
             self._root.geometry("1200x800")
        
        # Load state
        self._state = AppState.load()

        # Apply DPI scaling
        self._apply_dpi_scaling()

        # Set style
        self._setup_style()
        
        # Initialize localization
        from opentree.core.i18n import set_language
        set_language(self._state.language)
        
        # Apply saved window geometry
        self._apply_window_state()
        
        # Managing sessions
        self._sessions: Dict[str, RepoSession] = {} # tab_id -> Session
        
        # Check for git
        git_path = self._state.git_executable or "git"
        if not is_git_available(git_path):
            self._root.withdraw()
            dialog = GitNotFoundDialog(self._root)
            result = dialog.wait()
            if result:
                self._state.git_executable = result
                self._state.save()
            else:
                self._root.destroy()
                return
            self._root.deiconify()
        
        # Setup UI
        self._setup_menu()
        
        # Main Notebook for tabs
        self._notebook = ttk.Notebook(self._root)
        self._notebook.pack(fill=tk.BOTH, expand=True)
        self._notebook.enable_traversal() # Ctrl+Tab support
        
        # Wire up events
        self._setup_event_handlers()
        
        # Apply saved theme
        # self._apply_theme() # TODO: Implement theme applying to all sessions or root
        
        # Restore open sessions
        if self._state.open_repos:
            for repo_path_str in self._state.open_repos:
                path = Path(repo_path_str)
                if path.exists():
                    try:
                        self._open_repo(path, save_state=False)
                    except Exception as e:
                        print(f"Failed to restore repo {path}: {e}")
            
            # Select last active repo
            if self._state.current_repo:
                # Find tab with this repo
                # This is tricky because we need to map repo path to tab
                pass # Selection logic is implicit or default
        elif self._state.current_repo and Path(self._state.current_repo).exists():
           # Fallback for migration
           self._root.after(100, lambda: self._open_repo(Path(self._state.current_repo)))
        
        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _enable_dpi_awareness(self) -> None:
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
    
    def _apply_dpi_scaling(self) -> None:
        """Apply DPI scaling based on settings and system configuration."""
        try:
            # 1. Scaling Factor from Settings
            scaling_factor = self._state.dpi_scaling
            
            # If Auto (0.0), try to detect system DPI
            if scaling_factor <= 0:
                try:
                    # Get DPI from system (Windows)
                    import ctypes
                    user32 = ctypes.windll.user32
                    user32.SetProcessDPIAware()
                    dpi = user32.GetDpiForSystem()
                    scaling_factor = dpi / 96.0
                except:
                    # Fallback to tkinter's detection
                    dpi = self._root.winfo_fpixels('1i')
                    scaling_factor = dpi / 72.0 # 72 is standard legacy for tk scaling? actually 96 usually.
                    # Tk uses 72 points per inch internally for fonts? 
                    # Standard Windows DPI is 96. 
                    # If winfo_fpixels('1i') returns 96, scaling should be ~1.333 (96/72) to match standard 96dpi look?
                    # No, 'tk scaling' sets pixels per point. Standard is ~1.3333 (96/72).
                    # If we want 1.0 (100%), we set tk scaling to 1.3333 (assuming 96dpi screen).
                    pass

            # If still invalid or default, assure at least 1.0 equivalent
            if scaling_factor <= 0:
                scaling_factor = 1.0

            # 2. Apply to Tkinter
            # Tkinter 'scaling' is pixels per point. Standard (100%) is usually ~1.3333 (96/72).
            # If user wants 150% (1.5), we should set scaling to 1.3333 * 1.5 = 2.0 approx.
            # However, high-dpi displays might report 144dpi (1.5x) naturally.
            
            # Let's force it based on 96dpi baseline
            # 1.0 (100%) -> 96 dpi -> 96/72 = 1.3333
            target_ppi = 96.0 * scaling_factor
            tk_step = target_ppi / 72.0
            
            self._root.tk.call('tk', 'scaling', tk_step)
            
            # Also apply to font defaults if possible (optional, but helps)
            # We already have configurable fonts in settings, so user can adjust there too.
            
            # 3. Windows Specific: Inform OS about scaling if using "Auto" or forcing custom
            # (Already handled by _enable_dpi_awareness for "Auto")
            
        except Exception as e:
            print(f"DPI Scaling failed: {e}")
    
    def _update_window_theme(self) -> None:
        """Update window theme (Windows Titlebar)."""
        import sys
        if sys.platform != "win32":
            return
            
        try:
            import ctypes
            from opentree.core.theme import ThemeType
            
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            # Note: This works on Windows 10 build 19041+ and Windows 11
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            
            # Check if theme is dark
            is_dark = self.theme_manager.theme.type == ThemeType.DARK
            # Or if custom but using dark background (heuristic)
            if self.theme_manager.theme.type == ThemeType.CUSTOM:
                bg = self.theme_manager.theme.bg_primary
                # Simple check: if R,G,B are all < 128
                try:
                    r = int(bg[1:3], 16)
                    g = int(bg[3:5], 16)
                    b = int(bg[5:7], 16)
                    is_dark = (r + g + b) / 3 < 128
                except:
                    pass
            
            set_dark = 1 if is_dark else 0
            
            hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
            value = ctypes.c_int(set_dark)
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(value), 
                ctypes.sizeof(value)
            )
        except Exception:
            pass

    def _setup_style(self) -> None:
        from opentree.core.theme import ThemeManager, ThemeType
        
        # Initialize theme manager
        self.theme_manager = ThemeManager.get_instance()
        
        # Determine theme based on settings
        if self._state.theme:
            self.theme_manager.apply_theme_from_state(self._state.theme)
        else:
            self.theme_manager.set_theme(ThemeType.LIGHT)
        
        # Apply to TTK
        style = ttk.Style()
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass
            
        self.theme_manager.apply_to_ttk_style(style)
        
        # Apply to Root
        t = self.theme_manager.theme
        self._root.configure(background=t.bg_primary)
        
        self._update_window_theme()
    
    def _apply_window_state(self) -> None:
        ws = self._state.window
        if ws.x is not None and ws.y is not None:
             self._root.geometry(f"{ws.width}x{ws.height}+{ws.x}+{ws.y}")
        else:
             self._root.geometry(f"{ws.width}x{ws.height}")
        if ws.maximized:
            self._root.state("zoomed")
    
    def _save_window_state(self) -> None:
        ws = self._state.window
        ws.maximized = self._root.state() == "zoomed"
        if not ws.maximized:
            geo = self._root.geometry()
            size, pos = geo.split("+", 1)
            w, h = size.split("x")
            x, y = pos.split("+")
            ws.width = int(w)
            ws.height = int(h)
            ws.x = int(x)
            ws.y = int(y)

    def _setup_menu(self) -> None:
        from opentree.ui.menu_bar import CustomMenuBar
        
        # Remove native menu if any
        self._root.config(menu="")
        
        # Create custom menu bar
        self._menubar = CustomMenuBar(self._root, self)
        self._menubar.pack(side=tk.TOP, fill=tk.X)
        
        # Bind Shortcuts globally since native menu isn't handling them automatically anymore
        # (Though menu accelerators usually only display text, some frameworks handle them. 
        # Tkinter native menus handle them. Custom ones might not.)
        
        self._root.bind("<Control-o>", lambda e: self._cmd_open_repo())
        self._root.bind("<Control-w>", lambda e: self._cmd_close_current_tab())
        self._root.bind("<F5>", lambda e: self._cmd_refresh())
        self._root.bind("<Alt-F4>", lambda e: self._on_close())

    def _setup_event_handlers(self) -> None:
        # Global events
        self.theme_manager.add_listener(self._on_theme_changed)

    def _on_theme_changed(self) -> None:
        """Handle theme change event."""
        # Re-apply style to ttk
        style = ttk.Style()
        self.theme_manager.apply_to_ttk_style(style)
        
        # Update root background
        t = self.theme_manager.theme
        self._root.configure(background=t.bg_primary)
        
        # Update all sessions
        for session in self._sessions.values():
            try:
                session.refresh_theme()
            except Exception as e:
                print(f"Failed to refresh session theme: {e}")
        
        # Update window titlebar (Windows specific)
        self._update_window_theme()

        # Update custom menu bar
        if hasattr(self, "_menubar") and hasattr(self._menubar, "refresh_theme"):
            self._menubar.refresh_theme()

    def _get_active_session(self) -> Optional[RepoSession]:
        try:
            select_id = self._notebook.select()
            if select_id:
                # select_id is the widget name/path
                return self._sessions.get(select_id)
        except tk.TclError:
            pass
        return None

    def _invoke_active(self, method: str, *args, **kwargs) -> None:
        """Invoke method on active session."""
        session = self._get_active_session()
        if session:
            # Check if method is on session
            func = getattr(session, method, None)
            if callable(func):
                func(*args, **kwargs)
                return
            
            # Check if method is on view
            if hasattr(session, "view"):
                func = getattr(session.view, method, None)
                if callable(func):
                    func(*args, **kwargs)

    def _cmd_open_repo(self) -> None:
        path = OpenRepoDialog.show(self._root)
        if path:
            self._open_repo(path)

    def _open_repo(self, path: Path, save_state: bool = True) -> None:
        repo_root = find_repo_root(path)
        if not repo_root:
             from opentree.ui.dialogs import ErrorDialog
             ErrorDialog.show(self._root, "Invalid Repository", f"'{path}' is not a Git repository.")
             return
        
        # Check if already open
        str_path = str(repo_root)
        for session in self._sessions.values():
            if str(session.repo_path) == str_path:
                self._notebook.select(session.view)
                return

        # Create session
        session = RepoSession(self._notebook, repo_root, self._state)
        
        # Wire up app-level actions to session toolbar
        session.view.toolbar.settings_btn.configure(command=self._cmd_settings)
        
        # Add to notebook
        self._notebook.add(session.view, text=repo_root.name)
        self._notebook.select(session.view)
        
        # Track session
        tab_id = str(session.view)
        self._sessions[tab_id] = session
        
        # Update state
        self._state.add_recent_repo(str(repo_root))
        self._state.current_repo = str(repo_root)
        
        if str_path not in self._state.open_repos:
            self._state.open_repos.append(str_path)
            
        if save_state:
            self._state.save()
        
        self._root.title(f"OpenTree - {repo_root.name}")

    def _cmd_close_current_tab(self) -> None:
        session = self._get_active_session()
        if session:
            tab_id = str(session.view)
            repo_path = str(session.repo_path)
            
            self._notebook.forget(session.view)
            session.view.destroy()
            del self._sessions[tab_id]
            
            if repo_path in self._state.open_repos:
                self._state.open_repos.remove(repo_path)
            
            # Select another tab if available
            if self._notebook.tabs():
                pass # notebook automatically selects another
            else:
                self._root.title("OpenTree")
                self._state.current_repo = None
            
            self._state.save()

    def _cmd_refresh(self) -> None:
        session = self._get_active_session()
        if session:
            session.cmd_refresh()

    def _cmd_settings(self) -> None:
        dialog = SettingsDialog(self._root, self._state, self._apply_settings)
        dialog.wait()
        
    def _apply_settings(self) -> None:
        self._state.save()
        active_session = self._get_active_session()

        for session in self._sessions.values():
            try:
                session.apply_settings(refresh_repo=session is active_session)
            except Exception as e:
                print(f"Failed to apply session settings: {e}")

    def _cmd_about(self) -> None:
        AboutDialog(self._root)

    def _on_close(self) -> None:
        self._save_window_state()
        self._state.save()
        self._root.destroy()

    def run(self) -> None:
        self._root.mainloop()

if __name__ == "__main__":
    from opentree.core.state import AppState
    app = OpenTreeApp()
    app.run()
