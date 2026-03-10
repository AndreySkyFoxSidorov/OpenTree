"""
Settings dialog for OpenTree.

Comprehensive settings with tabs for General, Git, Commit, Theme, and Authentication.
"""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
from typing import Optional, Callable, Any

from opentree.core.state import AppState
from opentree.core.theme import ThemeManager, ThemeType
from opentree.core.i18n import tr


class CredentialEditDialog(tk.Toplevel):
    """Dialog for editing domain credentials."""
    
    def __init__(self, parent: tk.Widget, domain: str = "", 
                 username: str = "", password: str = "", ssh_key: str = "") -> None:
        super().__init__(parent)
        self.title(tr("la_edit_credential") if domain else tr("la_add_credential"))
        self.transient(parent)
        self.grab_set()
        
        self._result = None
        
        # Dynamic sizing
        self.minsize(450, 300)
        self.resizable(True, True)
        
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Domain
        ttk.Label(frame, text=tr("la_domain") + ":").pack(anchor=tk.W)
        self._domain = ttk.Entry(frame, width=40)
        self._domain.insert(0, domain)
        self._domain.pack(fill=tk.X, pady=(0, 10))
        self._domain.bind("<FocusOut>", lambda e: self._parse_url())
        
        # Username
        ttk.Label(frame, text=tr("la_username") + ":").pack(anchor=tk.W)
        self._username = ttk.Entry(frame, width=40)
        self._username.insert(0, username)
        self._username.pack(fill=tk.X, pady=(0, 10))
        
        # Password
        ttk.Label(frame, text=tr("la_password") + ":").pack(anchor=tk.W)
        self._password = ttk.Entry(frame, width=40, show="*")
        self._password.insert(0, password)
        self._password.pack(fill=tk.X, pady=(0, 10))
        
        # SSH Key (optional)
        key_frame = ttk.Frame(frame)
        key_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(key_frame, text=tr("la_ssh_key") + ":").pack(anchor=tk.W)
        self._ssh_key = ttk.Entry(key_frame, width=35)
        self._ssh_key.insert(0, ssh_key)
        self._ssh_key.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(key_frame, text="...", width=3, 
                  command=self._browse_ssh).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text=tr("la_cancel"), 
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_save"), 
                  command=self._save).pack(side=tk.RIGHT)
        
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        
        self._domain.focus_set()
    
    def _parse_url(self) -> None:
        """Parse URL in domain field and extract host/username if present."""
        import re
        url = self._domain.get().strip()
        
        if not url:
            return
        
        host = None
        user = None
        
        # SSH URL: ssh://user@host:port/path or ssh://host/path
        if url.startswith('ssh://'):
            match = re.search(r'ssh://(?:([^@]+)@)?([^/:]+)', url)
            if match:
                user = match.group(1)  # May be None
                host = match.group(2)
        # SCP-style: user@host:path
        elif '@' in url and ':' in url:
            match = re.match(r'([^@]+)@([^:]+):', url)
            if match:
                user = match.group(1)
                host = match.group(2)
        # HTTPS URL: https://user@host/path or https://host/path
        elif url.startswith('https://') or url.startswith('http://'):
            match = re.search(r'https?://(?:([^@]+)@)?([^/:]+)', url)
            if match:
                user = match.group(1)  # May be None
                host = match.group(2)
        
        # Update fields if we parsed successfully
        if host and host != url:
            self._domain.delete(0, tk.END)
            self._domain.insert(0, host)
            
            if user and not self._username.get().strip():
                self._username.delete(0, tk.END)
                self._username.insert(0, user)
    
    def _browse_ssh(self) -> None:
        """Browse for SSH key file."""
        path = filedialog.askopenfilename(
            parent=self,
            title=tr("la_select_ssh_key"),
            filetypes=[("All files", "*.*")]
        )
        if path:
            self._ssh_key.delete(0, tk.END)
            self._ssh_key.insert(0, path)
    
    def _save(self) -> None:
        """Save and close."""
        domain = self._domain.get().strip()
        if not domain:
            return
        self._result = (
            domain,
            self._username.get().strip(),
            self._password.get(),
            self._ssh_key.get().strip()
        )
        self.destroy()
    
    def wait(self):
        """Wait for dialog and return result."""
        self.wait_window()
        return self._result

class SettingsDialog(tk.Toplevel):
    """
    Settings dialog with multiple configuration tabs.
    """
    
    def __init__(self, parent: tk.Widget, state: AppState,
                 on_save: Optional[Callable[[], Any]] = None) -> None:
        super().__init__(parent)
        self.title(tr("la_settings"))
        self.transient(parent)
        self.grab_set()
        
        self._state = state
        self._on_save = on_save
        
        # Dynamic sizing
        self.minsize(650, 500)
        
        self._setup_ui()
        self._load_values()
        
        # Calculate size after content is added
        self.update_idletasks()
        
        # Auto-size
        self.geometry("")
        self.update_idletasks()
        
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        
        # Ensure minimums (and reasonable maximums for initial show if needed)
        w = max(w, 750) 
        h = max(h, 600)
        
        # Center relative to parent
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            
            if y < 0: y = 0
            
            self.geometry(f"{w}x{h}+{x}+{y}")
        except:
             self.geometry(f"{w}x{h}")
        
        self.bind("<Escape>", lambda e: self.destroy())
    
    def _setup_ui(self) -> None:
        """Create the UI layout."""
        # Notebook for tabs
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self._create_general_tab()
        self._create_git_tab()
        self._create_git_commands_tab()
        self._create_commit_tab()
        self._create_theme_tab()
        self._create_auth_tab()
        
        # Buttons at bottom
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text=tr("la_cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_apply"), command=self._apply).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=tr("la_ok"), command=self._ok).pack(side=tk.RIGHT)
    
    def _create_general_tab(self) -> None:
        """Create the General settings tab."""
        tab = ttk.Frame(self._notebook, padding=15)
        self._notebook.add(tab, text=tr("la_general"))
        
        # User Information
        user_frame = ttk.LabelFrame(tab, text=tr("la_user_info"), padding=10)
        user_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(user_frame, text=tr("la_full_name") + ":").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._user_name = ttk.Entry(user_frame, width=40)
        self._user_name.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(user_frame, text=tr("la_email") + ":").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._user_email = ttk.Entry(user_frame, width=40)
        self._user_email.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        # Language Settings
        lang_frame = ttk.LabelFrame(tab, text="Language / Мова / Язык", padding=10)
        lang_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(lang_frame, text="Interface language:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._language = ttk.Combobox(lang_frame, values=[
            "EN - English",
            "UK - Українська",
            "RU - Русский",
            "ES - Español",
            "IT - Italiano",
            "DE - Deutsch",
            "KO - 한국어",
            "NL - Nederlands",
            "FR - Français",
            "PT - Português",
            "ZH_TW - 繁體中文",
            "ZH - 简体中文",
            "PL - Polski",
            "CS - Čeština",
        ], width=25, state="readonly")
        self._language.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(lang_frame, text="Requires restart", font=("Segoe UI", 8, "italic")).grid(
            row=0, column=2, sticky=tk.W, padx=10)

        # Appearance Settings (DPI)
        app_frame = ttk.LabelFrame(tab, text=tr("la_appearance", "Appearance"), padding=10)
        app_frame.pack(fill=tk.X, pady=5)
        
        
        ttk.Label(app_frame, text=tr("la_dpi_scaling", "DPI Scaling") + ":").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._dpi_scaling = ttk.Combobox(app_frame, values=[
            "Auto", "25%", "50%", "75%", "100%", "125%", "150%", "175%", "200%", "250%", "300%"
        ], width=15, state="readonly")
        self._dpi_scaling.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        ttk.Label(app_frame, text=tr("la_restart_required", "Requires restart"), font=("Segoe UI", 8, "italic")).grid(
            row=0, column=2, sticky=tk.W, padx=10)

        # Project Settings
        proj_frame = ttk.LabelFrame(tab, text=tr("la_project_settings"), padding=10)
        proj_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(proj_frame, text=tr("la_default_folder") + ":").grid(row=0, column=0, sticky=tk.W, pady=2)
        folder_frame = ttk.Frame(proj_frame)
        folder_frame.grid(row=0, column=1, sticky=tk.W, pady=2)
        self._project_folder = ttk.Entry(folder_frame, width=35)
        self._project_folder.pack(side=tk.LEFT)
        ttk.Button(folder_frame, text="...", width=3,
                   command=self._browse_folder).pack(side=tk.LEFT, padx=2)
        
        # Behavior
        behavior_frame = ttk.LabelFrame(tab, text=tr("la_behavior"), padding=10)
        behavior_frame.pack(fill=tk.X, pady=5)
        
        self._auto_refresh = tk.BooleanVar()
        ttk.Checkbutton(behavior_frame, text=tr("la_auto_refresh"),
                        variable=self._auto_refresh).pack(anchor=tk.W)
        
        self._refresh_on_focus = tk.BooleanVar()
        ttk.Checkbutton(behavior_frame, text=tr("la_refresh_on_focus"),
                        variable=self._refresh_on_focus).pack(anchor=tk.W)
        
        self._reopen_repos = tk.BooleanVar()
        ttk.Checkbutton(behavior_frame, text=tr("la_reopen_repos"),
                        variable=self._reopen_repos).pack(anchor=tk.W)
        
        self._keep_backups = tk.BooleanVar()
        ttk.Checkbutton(behavior_frame, text=tr("la_keep_backups"),
                        variable=self._keep_backups).pack(anchor=tk.W)
        
        # Remote checking
        remote_frame = ttk.Frame(behavior_frame)
        remote_frame.pack(anchor=tk.W, pady=5)
        self._check_remotes = tk.BooleanVar()
        ttk.Checkbutton(remote_frame, text=tr("la_check_remotes"),
                        variable=self._check_remotes).pack(side=tk.LEFT)
        self._check_interval = ttk.Spinbox(remote_frame, from_=1, to=60, width=5)
        self._check_interval.pack(side=tk.LEFT, padx=5)
        ttk.Label(remote_frame, text=tr("la_minutes")).pack(side=tk.LEFT)
    
    def _create_git_tab(self) -> None:
        """Create the Git settings tab."""
        tab = ttk.Frame(self._notebook, padding=15)
        self._notebook.add(tab, text=tr("la_git"))
        
        # Global Ignore
        ignore_frame = ttk.LabelFrame(tab, text=tr("la_global_ignore"), padding=10)
        ignore_frame.pack(fill=tk.X, pady=5)
        
        file_frame = ttk.Frame(ignore_frame)
        file_frame.pack(fill=tk.X)
        ttk.Label(file_frame, text="File:").pack(side=tk.LEFT)
        self._global_ignore = ttk.Entry(file_frame, width=40)
        self._global_ignore.pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="...", width=3,
                   command=self._browse_ignore).pack(side=tk.LEFT)
        
        # Push Settings
        push_frame = ttk.LabelFrame(tab, text=tr("la_push_settings"), padding=10)
        push_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(push_frame, text=tr("la_push_policy") + ":").grid(row=0, column=0, sticky=tk.W)
        self._push_policy = ttk.Combobox(push_frame, values=["simple", "current", "upstream", "matching"], width=20)
        self._push_policy.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Git Options
        opts_frame = ttk.LabelFrame(tab, text=tr("la_options"), padding=10)
        opts_frame.pack(fill=tk.X, pady=5)
        
        self._use_rebase = tk.BooleanVar()
        ttk.Checkbutton(opts_frame, text=tr("la_use_rebase"),
                        variable=self._use_rebase).pack(anchor=tk.W)
        
        self._push_tags = tk.BooleanVar()
        ttk.Checkbutton(opts_frame, text=tr("la_push_tags"),
                        variable=self._push_tags).pack(anchor=tk.W)
        
        self._allow_force = tk.BooleanVar()
        ttk.Checkbutton(opts_frame, text=tr("la_allow_force"),
                        variable=self._allow_force).pack(anchor=tk.W)
        
        # Git Executable
        exe_frame = ttk.LabelFrame(tab, text=tr("la_git_executable"), padding=10)
        exe_frame.pack(fill=tk.X, pady=5)
        
        path_frame = ttk.Frame(exe_frame)
        path_frame.pack(fill=tk.X)
        self._git_path = ttk.Entry(path_frame, width=45)
        self._git_path.pack(side=tk.LEFT)
        ttk.Button(path_frame, text="...", width=3,
                   command=self._browse_git).pack(side=tk.LEFT, padx=2)
    
    def _create_git_commands_tab(self) -> None:
        """Create the Git Commands settings tab for customizing git command templates."""
        tab = ttk.Frame(self._notebook, padding=15)
        self._notebook.add(tab, text=tr("la_git_commands"))
        
        # Instructions
        info_label = ttk.Label(tab, text=tr("la_git_commands_info"), wraplength=500)
        info_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Common flags
        flags_frame = ttk.LabelFrame(tab, text=tr("la_common_flags"), padding=10)
        flags_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(flags_frame, text=tr("la_flags") + ":").pack(anchor=tk.W)
        self._git_common_flags = ttk.Entry(flags_frame, width=70)
        self._git_common_flags.pack(fill=tk.X, pady=2)
        
        # Commands frame
        cmd_frame = ttk.LabelFrame(tab, text=tr("la_command_templates"), padding=10)
        cmd_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Fetch command
        ttk.Label(cmd_frame, text="Fetch:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._git_fetch_cmd = ttk.Entry(cmd_frame, width=60)
        self._git_fetch_cmd.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)
        
        # Pull command
        ttk.Label(cmd_frame, text="Pull:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self._git_pull_cmd = ttk.Entry(cmd_frame, width=60)
        self._git_pull_cmd.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3)
        
        # Push command
        ttk.Label(cmd_frame, text="Push:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self._git_push_cmd = ttk.Entry(cmd_frame, width=60)
        self._git_push_cmd.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=3)
        
        # Commit command
        ttk.Label(cmd_frame, text="Commit:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self._git_commit_cmd = ttk.Entry(cmd_frame, width=60)
        self._git_commit_cmd.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=3)
        
        # Checkout command
        ttk.Label(cmd_frame, text="Checkout:").grid(row=4, column=0, sticky=tk.W, pady=3)
        self._git_checkout_cmd = ttk.Entry(cmd_frame, width=60)
        self._git_checkout_cmd.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=3)
        
        cmd_frame.columnconfigure(1, weight=1)
        
        # Placeholders info
        placeholders = ttk.Label(tab, 
            text="{flags} = Common flags, {remote} = Remote name, {branch} = Branch name,\n"
                 "{rebase} = --rebase if enabled, {force} = --force-with-lease if enabled,\n"
                 "{file} = Commit message file path",
            font=("Segoe UI", 8))
        placeholders.pack(anchor=tk.W, pady=5)
        
        # Reset button
        ttk.Button(tab, text=tr("la_reset_defaults"), 
                   command=self._reset_git_commands).pack(anchor=tk.W, pady=5)
    
    def _reset_git_commands(self) -> None:
        """Reset git commands to defaults."""
        defaults = {
            "git_common_flags": "-c diff.mnemonicprefix=false -c core.quotepath=false --no-optional-locks",
            "git_fetch_cmd": "git {flags} fetch --prune {remote}",
            "git_pull_cmd": "git {flags} pull {rebase} {remote} {branch}",
            "git_push_cmd": "git {flags} push {force} {remote} {branch}",
            "git_commit_cmd": "git {flags} commit -F {file}",
            "git_checkout_cmd": "git {flags} checkout {branch}",
        }
        self._git_common_flags.delete(0, tk.END)
        self._git_common_flags.insert(0, defaults["git_common_flags"])
        self._git_fetch_cmd.delete(0, tk.END)
        self._git_fetch_cmd.insert(0, defaults["git_fetch_cmd"])
        self._git_pull_cmd.delete(0, tk.END)
        self._git_pull_cmd.insert(0, defaults["git_pull_cmd"])
        self._git_push_cmd.delete(0, tk.END)
        self._git_push_cmd.insert(0, defaults["git_push_cmd"])
        self._git_commit_cmd.delete(0, tk.END)
        self._git_commit_cmd.insert(0, defaults["git_commit_cmd"])
        self._git_checkout_cmd.delete(0, tk.END)
        self._git_checkout_cmd.insert(0, defaults["git_checkout_cmd"])
    
    def _create_commit_tab(self) -> None:
        """Create the Commit settings tab."""
        tab = ttk.Frame(self._notebook, padding=15)
        self._notebook.add(tab, text=tr("la_commit"))
        
        # History
        hist_frame = ttk.LabelFrame(tab, text=tr("la_history"), padding=10)
        hist_frame.pack(fill=tk.X, pady=5)
        
        limit_frame = ttk.Frame(hist_frame)
        limit_frame.pack(anchor=tk.W)
        ttk.Label(limit_frame, text=tr("la_log_rows") + ":").pack(side=tk.LEFT)
        self._history_limit = ttk.Spinbox(limit_frame, from_=50, to=1000, width=8)
        self._history_limit.pack(side=tk.LEFT, padx=5)
        
        self._show_ahead_behind = tk.BooleanVar()
        ttk.Checkbutton(hist_frame, text=tr("la_show_ahead_behind"),
                        variable=self._show_ahead_behind).pack(anchor=tk.W, pady=5)
        
        # Commit Message
        msg_frame = ttk.LabelFrame(tab, text=tr("la_commit_message"), padding=10)
        msg_frame.pack(fill=tk.X, pady=5)
        
        guide_frame = ttk.Frame(msg_frame)
        guide_frame.pack(anchor=tk.W)
        self._use_column_guide = tk.BooleanVar()
        ttk.Checkbutton(guide_frame, text=tr("la_show_column_guide"),
                        variable=self._use_column_guide).pack(side=tk.LEFT)
        self._column_position = ttk.Spinbox(guide_frame, from_=50, to=120, width=5)
        self._column_position.pack(side=tk.LEFT, padx=5)
        ttk.Label(guide_frame, text=tr("la_characters")).pack(side=tk.LEFT)
        
        self._fixed_width_font = tk.BooleanVar()
        ttk.Checkbutton(msg_frame, text=tr("la_fixed_width_font"),
                        variable=self._fixed_width_font).pack(anchor=tk.W, pady=5)
        
        # After Commit
        after_frame = ttk.LabelFrame(tab, text=tr("la_after_commit"), padding=10)
        after_frame.pack(fill=tk.X, pady=5)
        
        self._push_after_commit = tk.BooleanVar()
        ttk.Checkbutton(after_frame, text=tr("la_push_after_commit"),
                        variable=self._push_after_commit).pack(anchor=tk.W)
    
    def _create_theme_tab(self) -> None:
        """Create the Theme settings tab."""
        tab = ttk.Frame(self._notebook, padding=20)
        self._notebook.add(tab, text=tr("la_theme"))
        
        # --- Presets Section ---
        preset_frame = ttk.LabelFrame(tab, text="Theme Mode", padding=15)
        preset_frame.pack(fill=tk.X, pady=(0, 15))
        
        self._theme_var = tk.StringVar(value="custom")
        
        modes = [("Light", "light"), ("Dark", "dark"), ("Custom", "custom")]
        for i, (label, mode) in enumerate(modes):
            rb = ttk.Radiobutton(preset_frame, text=label, variable=self._theme_var, value=mode,
                                command=self._on_preset_change)
            rb.pack(side=tk.LEFT, padx=20)
            
        # --- Detailed Customization ---
        details_frame = ttk.LabelFrame(tab, text="Customization", padding=15)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        self._color_vars = {} 
        self._color_entries = {} 
        
        r = 0
        
        # --- UI Base ---
        ttk.Label(details_frame, text="Base Colors", font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky="w", pady=(0, 10)); r+=1
        
        self._add_color_row(details_frame, r, "bg_primary", "Main Background")
        self._add_color_row(details_frame, r, "text_primary", "Main Text", col_offset=3)
        r+=1
        self._add_color_row(details_frame, r, "bg_secondary", "Secondary Bg")
        self._add_color_row(details_frame, r, "text_secondary", "Secondary Text", col_offset=3)
        r+=1
        self._add_color_row(details_frame, r, "bg_tertiary", "Tertiary Bg")
        self._add_color_row(details_frame, r, "text_tertiary", "Muted Text", col_offset=3)
        r+=1
        self._add_color_row(details_frame, r, "border_subtle", "Border Low")
        self._add_color_row(details_frame, r, "border_focus", "Border Focus", col_offset=3)
        r+=1
        self._add_color_row(details_frame, r, "accent_primary", "Primary Accent")
        self._add_color_row(details_frame, r, "accent_secondary", "Secondary Accent", col_offset=3)
        r+=1
        
        ttk.Separator(details_frame, orient=tk.HORIZONTAL).grid(row=r, column=0, columnspan=6, sticky="ew", pady=15); r+=1
        
        # --- Git / Diff ---
        ttk.Label(details_frame, text="Git & Semantic", font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky="w", pady=(0, 10)); r+=1
        
        self._add_color_row(details_frame, r, "diff_add_bg", "Added Line Bg")
        self._add_color_row(details_frame, r, "diff_add_fg", "Added Text", col_offset=3)
        r+=1
        self._add_color_row(details_frame, r, "diff_del_bg", "Deleted Line Bg")
        self._add_color_row(details_frame, r, "diff_del_fg", "Deleted Text", col_offset=3)
        r+=1
        self._add_color_row(details_frame, r, "diff_header_bg", "Diff Header Bg")
        self._add_color_row(details_frame, r, "diff_header_fg", "Diff Header Text", col_offset=3)
        r+=1
        
        self._add_color_row(details_frame, r, "status_success", "Status Success")
        self._add_color_row(details_frame, r, "status_warning", "Status Warning", col_offset=3)
        r+=1
        self._add_color_row(details_frame, r, "status_danger", "Status Danger")
        self._add_color_row(details_frame, r, "status_info", "Status Info", col_offset=3)
        r+=1

        ttk.Separator(details_frame, orient=tk.HORIZONTAL).grid(row=r, column=0, columnspan=6, sticky="ew", pady=15); r+=1
        
        # --- Fonts ---
        ttk.Label(details_frame, text="Typography", font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky="w", pady=(0, 10)); r+=1
        
        font_frame = ttk.Frame(details_frame)
        font_frame.grid(row=r, column=0, columnspan=6, sticky="w")
        
        ttk.Label(font_frame, text="UI Font:").pack(side=tk.LEFT)
        self._ui_font = ttk.Combobox(font_frame, values=["Segoe UI", "Arial", "Helvetica", "Verdana", "Roboto", "Inter"], width=15)
        self._ui_font.pack(side=tk.LEFT, padx=5)
        self._ui_font_size = ttk.Spinbox(font_frame, from_=8, to=18, width=5)
        self._ui_font_size.pack(side=tk.LEFT)
        
        ttk.Label(font_frame, text="Code Font:").pack(side=tk.LEFT, padx=(20, 0))
        self._diff_font = ttk.Combobox(font_frame, values=["Consolas", "Courier New", "Monaco", "Menlo", "Fira Code", "JetBrains Mono"], width=15)
        self._diff_font.pack(side=tk.LEFT, padx=5)
        self._diff_font_size = ttk.Spinbox(font_frame, from_=8, to=24, width=5)
        self._diff_font_size.pack(side=tk.LEFT)
    
    def _add_color_row(self, parent, row, token, label, col_offset=0):
        # Label
        ttk.Label(parent, text=label+":").grid(row=row, column=0+col_offset, sticky="w", padx=5, pady=2)
        
        # Entry
        var = tk.StringVar()
        var.trace("w", lambda *a: self._on_color_change())
        self._color_vars[token] = var
        
        entry = ttk.Entry(parent, width=12, textvariable=var)
        entry.grid(row=row, column=1+col_offset, sticky="w", pady=2)
        self._color_entries[token] = entry
        
        # Picker Button
        btn = tk.Button(parent, width=3, cursor="hand2")
        btn.grid(row=row, column=2+col_offset, padx=5, pady=2)
        
        def pick():
            current = var.get()
            try:
                color = colorchooser.askcolor(parent=self, color=current, title=label)[1]
                if color:
                    var.set(color)
                    btn.configure(bg=color)
            except:
                pass
        
        btn.configure(command=pick)
        
        # Bind entry update to button bg
        def update_btn(*a):
            try:
                c = var.get()
                if c.startswith("#") and len(c) in (4, 7):
                    btn.configure(bg=c)
            except: pass
        var.trace("w", update_btn)
        
    def _on_preset_change(self) -> None:
        """Handle preset selection."""
        mode = self._theme_var.get()
        if mode == "custom":
            return
            
        from opentree.core.theme import Theme
        if mode == "light":
            t = Theme.light()
        else:
            t = Theme.dark()
        
        self._ignore_changes = True
        import dataclasses
        for field in dataclasses.fields(t):
            if field.name in self._color_vars:
                val = getattr(t, field.name)
                self._color_vars[field.name].set(val)
        self._ignore_changes = False
        
    def _on_color_change(self) -> None:
        """Switch to custom if user edits a color."""
        if getattr(self, "_ignore_changes", False):
            return
        if self._theme_var.get() != "custom":
            self._theme_var.set("custom")
    
    def _create_auth_tab(self) -> None:
        """Create the Authentication settings tab with per-domain credentials."""
        tab = ttk.Frame(self._notebook, padding=15)
        self._notebook.add(tab, text=tr("la_authentication"))
        
        # SSH Settings
        ssh_frame = ttk.LabelFrame(tab, text=tr("la_ssh"), padding=10)
        ssh_frame.pack(fill=tk.X, pady=5)
        
        key_frame = ttk.Frame(ssh_frame)
        key_frame.pack(fill=tk.X)
        ttk.Label(key_frame, text=tr("la_ssh_key") + ":").pack(side=tk.LEFT)
        self._ssh_key = ttk.Entry(key_frame, width=40)
        self._ssh_key.pack(side=tk.LEFT, padx=5)
        ttk.Button(key_frame, text="...", width=3, command=self._browse_ssh).pack(side=tk.LEFT)
        
        # New: Accept new host keys
        self._ssh_accept_new = tk.BooleanVar()
        ttk.Checkbutton(ssh_frame, text=tr("la_ssh_accept_new", "Accept new SSH host keys (StrictHostKeyChecking=accept-new)"),
                        variable=self._ssh_accept_new).pack(anchor=tk.W, pady=5)
        
        self._auto_ssh_agent = tk.BooleanVar()
        ttk.Checkbutton(ssh_frame, text=tr("la_auto_start_ssh"),
                        variable=self._auto_ssh_agent).pack(anchor=tk.W)
        
        # Domain-based Credentials
        cred_frame = ttk.LabelFrame(tab, text=tr("la_domain_credentials"), padding=10)
        cred_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self._use_cred_manager = tk.BooleanVar()
        ttk.Checkbutton(cred_frame, text=tr("la_use_cred_manager"),
                        variable=self._use_cred_manager).pack(anchor=tk.W)
        
        # Credentials list
        list_frame = ttk.Frame(cred_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("domain", "username", "auth_type")
        self._creds_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        self._creds_tree.heading("domain", text=tr("la_domain"))
        self._creds_tree.heading("username", text=tr("la_username"))
        self._creds_tree.heading("auth_type", text=tr("la_auth_type"))
        self._creds_tree.column("domain", width=150)
        self._creds_tree.column("username", width=120)
        self._creds_tree.column("auth_type", width=100)
        self._creds_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._creds_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._creds_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        btn_frame = ttk.Frame(cred_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text=tr("la_add"), command=self._add_credential).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=tr("la_edit"), command=self._edit_credential).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=tr("la_remove"), command=self._remove_credential).pack(side=tk.LEFT, padx=2)
    
    def _add_credential(self) -> None:
        """Add a new domain credential."""
        dialog = CredentialEditDialog(self, "", "", "", "")
        result = dialog.wait()
        if result:
            domain, username, password, ssh_key = result
            self._state.set_credentials(domain, username, password, ssh_key)
            self._refresh_credentials_list()
    
    def _edit_credential(self) -> None:
        """Edit selected domain credential."""
        selection = self._creds_tree.selection()
        if not selection:
            return
        domain = self._creds_tree.item(selection[0])["values"][0]
        creds = self._state.get_credentials(domain)
        dialog = CredentialEditDialog(
            self, domain, 
            creds.get("username", ""),
            creds.get("password", ""),
            creds.get("ssh_key", "")
        )
        result = dialog.wait()
        if result:
            new_domain, username, password, ssh_key = result
            if new_domain != domain:
                self._state.remove_credentials(domain)
            self._state.set_credentials(new_domain, username, password, ssh_key)
            self._refresh_credentials_list()
    
    def _remove_credential(self) -> None:
        """Remove selected domain credential."""
        selection = self._creds_tree.selection()
        if not selection:
            return
        domain = self._creds_tree.item(selection[0])["values"][0]
        self._state.remove_credentials(domain)
        self._refresh_credentials_list()
    
    def _refresh_credentials_list(self) -> None:
        """Refresh the credentials treeview."""
        for item in self._creds_tree.get_children():
            self._creds_tree.delete(item)
        for domain, creds in self._state.credentials.items():
            auth_type = "SSH" if creds.get("ssh_key") else "HTTPS"
            self._creds_tree.insert("", tk.END, values=(
                domain, creds.get("username", ""), auth_type
            ))
    
    def _create_color_picker(self, parent: tk.Widget, label: str, row: int) -> ttk.Entry:
        """Create a color picker row."""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        entry = ttk.Entry(parent, width=15)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        
        color_btn = tk.Button(parent, width=3, bg="#ffffff")
        color_btn.grid(row=row, column=2, pady=2)
        
        def pick_color():
            color = colorchooser.askcolor(parent=self)[1]
            if color:
                entry.delete(0, tk.END)
                entry.insert(0, color)
                color_btn.configure(bg=color)
        
        color_btn.configure(command=pick_color)
        entry.color_btn = color_btn
        return entry
    
    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(parent=self)
        if path:
            self._project_folder.delete(0, tk.END)
            self._project_folder.insert(0, path)
    
    def _browse_ignore(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Select Global Ignore File")
        if path:
            self._global_ignore.delete(0, tk.END)
            self._global_ignore.insert(0, path)
    
    def _browse_git(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Git Executable",
            filetypes=[("Executables", "*.exe"), ("All Files", "*.*")]
        )
        if path:
            self._git_path.delete(0, tk.END)
            self._git_path.insert(0, path)
    
    def _browse_ssh(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Select SSH Key")
        if path:
            self._ssh_key.delete(0, tk.END)
            self._ssh_key.insert(0, path)
    
    def _load_values(self) -> None:
        """Load current values from state."""
        s = self._state
        
        # General
        if s.user_name: self._user_name.insert(0, s.user_name)
        if s.user_email: self._user_email.insert(0, s.user_email)
        
        lang_map = {
            "EN": "EN - English", "UK": "UK - Українська", "RU": "RU - Русский",
            "ES": "ES - Español", "IT": "IT - Italiano", "DE": "DE - Deutsch",
            "KO": "KO - 한국어", "NL": "NL - Nederlands", "FR": "FR - Français",
            "PT": "PT - Português", "ZH_TW": "ZH_TW - 繁體中文", "ZH": "ZH - 简体中文",
            "PL": "PL - Polski", "CS": "CS - Čeština",
        }
        self._language.set(lang_map.get(s.language, "EN - English"))
        
        if s.default_project_folder: self._project_folder.insert(0, s.default_project_folder)
        
        self._auto_refresh.set(s.auto_refresh)
        self._refresh_on_focus.set(s.refresh_on_focus)
        self._reopen_repos.set(s.reopen_repos_on_startup)
        self._keep_backups.set(s.keep_backups)
        self._check_remotes.set(s.check_remotes)
        self._check_remotes.set(s.check_remotes)
        self._check_interval.set(str(s.check_interval_minutes))
        
        # DPI
        dpi_map = {
            0.0: "Auto", 0.25: "25%", 0.5: "50%", 0.75: "75%", 
            1.0: "100%", 1.25: "125%", 1.5: "150%", 
            1.75: "175%", 2.0: "200%", 2.5: "250%", 3.0: "300%"
        }
        self._dpi_scaling.set(dpi_map.get(s.dpi_scaling, "Auto"))
        
        # Git
        if s.global_ignore_file: self._global_ignore.insert(0, s.global_ignore_file)
        self._push_policy.set(s.push_policy)
        self._use_rebase.set(s.use_rebase_for_pull)
        self._push_tags.set(s.push_all_tags)
        self._allow_force.set(s.allow_force_push)
        if s.git_executable: self._git_path.insert(0, s.git_executable)
        
        # Commit
        self._history_limit.set(str(s.history_limit))
        self._show_ahead_behind.set(s.show_ahead_behind)
        self._use_column_guide.set(s.use_column_guide)
        self._column_position.set(str(s.column_guide_position))
        self._fixed_width_font.set(s.fixed_width_commit_font)
        self._push_after_commit.set(s.push_after_commit)
        
        # Theme
        tm = ThemeManager.get_instance()
        t = tm.theme
        
        if t.name in ("Light", "light"):
            self._theme_var.set("light")
        elif t.name in ("Dark", "dark"):
            self._theme_var.set("dark")
        else:
            self._theme_var.set("custom")
            
        self._ignore_changes = True
        for token, var in self._color_vars.items():
            val = getattr(t, token, "#ff00ff")
            var.set(val)
        self._ignore_changes = False
            
        self._diff_font.set(t.font_mono)
        self._diff_font_size.set(str(t.font_size_md))
        self._ui_font.set(t.font_ui)
        self._ui_font_size.set(str(t.font_size_md))
        
        # Git Commands
        self._git_common_flags.insert(0, s.git_common_flags)
        self._git_fetch_cmd.insert(0, s.git_fetch_cmd)
        self._git_pull_cmd.insert(0, s.git_pull_cmd)
        self._git_push_cmd.insert(0, s.git_push_cmd)
        self._git_commit_cmd.insert(0, s.git_commit_cmd)
        self._git_checkout_cmd.insert(0, s.git_checkout_cmd)
        
        # Auth
        if s.ssh_key_path: self._ssh_key.insert(0, s.ssh_key_path)
        self._ssh_accept_new.set(getattr(s, "ssh_accept_new", False))
        self._auto_ssh_agent.set(s.auto_start_ssh_agent)
        self._use_cred_manager.set(s.use_credential_manager)
        self._refresh_credentials_list()
    
    def _save_values(self) -> None:
        """Save values to state."""
        s = self._state
        
        # General
        s.user_name = self._user_name.get().strip() or None
        s.user_email = self._user_email.get().strip() or None
        lang_selection = self._language.get()
        s.language = lang_selection.split(" - ")[0] if lang_selection else "EN"
        s.default_project_folder = self._project_folder.get().strip() or None
        s.auto_refresh = self._auto_refresh.get()
        s.refresh_on_focus = self._refresh_on_focus.get()
        s.reopen_repos_on_startup = self._reopen_repos.get()
        s.keep_backups = self._keep_backups.get()
        s.check_remotes = self._check_remotes.get()
        try: s.check_interval_minutes = int(self._check_interval.get())
        except: s.check_interval_minutes = 10
        
        # DPI
        dpi_str = self._dpi_scaling.get()
        if dpi_str in ("Auto", ""):
            s.dpi_scaling = 0.0
        else:
            try:
                # "125%" -> 1.25
                val = float(dpi_str.replace("%", "")) / 100.0
                s.dpi_scaling = val
            except ValueError:
                s.dpi_scaling = 0.0
        
        # Git
        s.global_ignore_file = self._global_ignore.get().strip() or None
        s.push_policy = self._push_policy.get()
        s.use_rebase_for_pull = self._use_rebase.get()
        s.push_all_tags = self._push_tags.get()
        s.allow_force_push = self._allow_force.get()
        s.git_executable = self._git_path.get().strip() or None
        
        # Commit
        try: s.history_limit = int(self._history_limit.get())
        except: s.history_limit = 200
        s.show_ahead_behind = self._show_ahead_behind.get()
        s.use_column_guide = self._use_column_guide.get()
        try: s.column_guide_position = int(self._column_position.get())
        except: s.column_guide_position = 72
        s.fixed_width_commit_font = self._fixed_width_font.get()
        s.push_after_commit = self._push_after_commit.get()
        
        # Theme
        mode = self._theme_var.get()
        s.theme.name = mode.capitalize() if mode != "custom" else "Custom"
        
        for token, var in self._color_vars.items():
            setattr(s.theme, token, var.get())
            
        s.theme.diff_font = self._diff_font.get()
        try: s.theme.diff_font_size = int(self._diff_font_size.get())
        except: s.theme.diff_font_size = 10
        s.theme.ui_font = self._ui_font.get()
        try: s.theme.ui_font_size = int(self._ui_font_size.get())
        except: s.theme.ui_font_size = 9
        
        # Apply immediately
        tm = ThemeManager.get_instance()
        tm.apply_theme_from_state(s.theme)
        
        # Git Commands
        s.git_common_flags = self._git_common_flags.get().strip()
        s.git_fetch_cmd = self._git_fetch_cmd.get().strip()
        s.git_pull_cmd = self._git_pull_cmd.get().strip()
        s.git_push_cmd = self._git_push_cmd.get().strip()
        s.git_commit_cmd = self._git_commit_cmd.get().strip()
        s.git_checkout_cmd = self._git_checkout_cmd.get().strip()
        
        # Auth
        s.ssh_key_path = self._ssh_key.get().strip() or None
        s.ssh_accept_new = self._ssh_accept_new.get()
        s.auto_start_ssh_agent = self._auto_ssh_agent.get()
        s.use_credential_manager = self._use_cred_manager.get()
        
        s.save()
    
    def _apply(self) -> None:
        """Apply settings without closing."""
        self._save_values()
        if self._on_save:
            self._on_save()
    
    def _ok(self) -> None:
        """Save and close."""
        self._save_values()
        if self._on_save:
            self._on_save()
        self.destroy()
    
    def wait(self) -> None:
        """Wait for dialog to close."""
        self.wait_window()
