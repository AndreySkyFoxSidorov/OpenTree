"""
Application state management.

Handles persistent storage of application settings and state.
All settings are saved to a JSON file in the user's config directory.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any
import base64
import secrets
from itertools import cycle

from opentree.utils.paths import get_config_dir


@dataclass
class WindowState:
    """Window position and size."""
    
    width: int = 1200
    height: int = 800
    x: Optional[int] = None
    y: Optional[int] = None
    maximized: bool = False


@dataclass
class ThemeSettings:
    """UI theme and color settings."""
    
    name: str = "light"
    
    # Colors
    bg_primary: str = "#ffffff"
    bg_secondary: str = "#f8fafc"
    bg_tertiary: str = "#f1f5f9"
    
    text_primary: str = "#0f172a"
    text_secondary: str = "#475569"
    text_tertiary: str = "#94a3b8"
    
    accent_primary: str = "#2563eb"
    accent_secondary: str = "#3b82f6"
    
    border_subtle: str = "#e2e8f0"
    border_focus: str = "#3b82f6"
    
    # Status Colors
    status_success: str = "#16a34a"
    status_warning: str = "#d97706"
    status_danger: str = "#dc2626"
    status_info: str = "#3b82f6"
    
    # Diff colors
    diff_add_bg: str = "#dcfce7"
    diff_add_fg: str = "#166534"
    diff_del_bg: str = "#fee2e2"
    diff_del_fg: str = "#991b1b"
    diff_header_bg: str = "#f1f5f9"
    diff_header_fg: str = "#475569"
    diff_hunk_bg: str = "#f8fafc"
    diff_hunk_fg: str = "#64748b"
    
    # Fonts
    diff_font: str = "Consolas"
    diff_font_size: int = 10
    ui_font: str = "Segoe UI"
    ui_font_size: int = 9


@dataclass
class AppState:
    """
    Complete application state.
    
    All settings are persisted to JSON automatically when save() is called.
    """
    
    # --- Window ---
    window: WindowState = field(default_factory=WindowState)
    
    # --- Theme ---
    theme: ThemeSettings = field(default_factory=ThemeSettings)
    
    # --- Repositories ---
    current_repo: Optional[str] = None
    recent_repos: list[str] = field(default_factory=list)
    max_recent_repos: int = 10
    
    # List of currently open repositories (paths)
    open_repos: list[str] = field(default_factory=list)
    
    # --- Git executable ---
    git_executable: Optional[str] = None
    
    # --- User info ---
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    
    # --- General settings ---
    default_project_folder: Optional[str] = None
    text_encoding: str = "utf-8"
    language: str = "EN"
    keep_backups: bool = True
    auto_refresh: bool = True
    refresh_on_focus: bool = False
    reopen_repos_on_startup: bool = True
    always_show_console: bool = False
    check_remotes: bool = True
    check_interval_minutes: int = 10
    dpi_scaling: float = 0.0  # 0.0 = Auto, otherwise multiplier (1.0, 1.25, etc.)
    
    # --- Git settings ---
    global_ignore_file: Optional[str] = None
    push_policy: str = "simple"
    use_rebase_for_pull: bool = False
    check_submodules: bool = True
    push_all_tags: bool = True
    no_fast_forward_merge: bool = False
    show_author_date: bool = False
    verbose_console: bool = False
    allow_force_push: bool = False
    safe_force_push: bool = True
    
    # --- Commit settings ---
    history_limit: int = 200
    show_ahead_behind: bool = True
    use_column_guide: bool = False
    column_guide_position: int = 72
    fixed_width_commit_font: bool = False
    push_after_commit: bool = False
    stay_in_commit_dialog: bool = False
    
    # --- Git command templates ---
    git_common_flags: str = "-c diff.mnemonicprefix=false -c core.quotepath=false --no-optional-locks"
    git_fetch_cmd: str = "git {flags} fetch --prune {remote}"
    git_pull_cmd: str = "git {flags} pull {rebase} {remote} {branch}"
    git_push_cmd: str = "git {flags} push {force} {remote} {branch}"
    git_commit_cmd: str = "git {flags} commit -F {file}"
    git_checkout_cmd: str = "git {flags} checkout {branch}"
    
    # --- SSH/Auth settings ---
    ssh_key_path: Optional[str] = None
    ssh_client: str = "OpenSSH"
    ssh_accept_new: bool = False
    auto_start_ssh_agent: bool = False
    use_credential_manager: bool = True
    # Domain-based credentials: {"github.com": {"username": "...", "password": "...", "ssh_key": "..."}}
    credentials: dict = field(default_factory=dict)
    
    # --- Internal ---
    _path: Path = field(default_factory=lambda: get_config_dir() / "state.json", repr=False)
    
    # Security token for obfuscation (generated once per install/config)
    security_token: str = field(default_factory=lambda: secrets.token_hex(32))
    
    def _encrypt(self, text: str) -> str:
        """Encrypt text using XOR + Base64 with security_token."""
        if not text:
            return ""
        if not self.security_token:
            self.security_token = secrets.token_hex(32)
            
        # XOR
        xored = ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(text, cycle(self.security_token)))
        # Base64
        return base64.b64encode(xored.encode("utf-8")).decode("utf-8")

    def _decrypt(self, encrypted_text: str) -> str:
        """Decrypt text using Base64 + XOR with security_token."""
        if not encrypted_text:
            return ""
        if not self.security_token:
            return encrypted_text # Should not happen if data exists, but fallback
            
        try:
            # Base64 decode
            decoded_xor = base64.b64decode(encrypted_text.encode("utf-8")).decode("utf-8")
            # XOR
            return ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(decoded_xor, cycle(self.security_token)))
        except Exception:
            # Fallback for plain text or corruption
            return encrypted_text
    def add_recent_repo(self, path: str) -> None:
        """Add a repository to the recent list."""
        if path in self.recent_repos:
            self.recent_repos.remove(path)
        self.recent_repos.insert(0, path)
        self.recent_repos = self.recent_repos[:self.max_recent_repos]
    
    def remove_recent_repo(self, path: str) -> None:
        """Remove a repository from the recent list."""
        if path in self.recent_repos:
            self.recent_repos.remove(path)
    
    def get_credentials(self, domain: str) -> dict:
        """Get credentials for a domain."""
        return self.credentials.get(domain, {})
    
    def set_credentials(self, domain: str, username: str = "", 
                       password: str = "", ssh_key: str = "") -> None:
        """Set credentials for a domain."""
        self.credentials[domain] = {
            "username": username,
            "password": password,
            "ssh_key": ssh_key
        }
    
    def remove_credentials(self, domain: str) -> None:
        """Remove credentials for a domain."""
        if domain in self.credentials:
            del self.credentials[domain]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-safe dictionary."""
        data = asdict(self)
        del data["_path"]
        
        # Encrypt the entire credentials blob
        if self.credentials:
            json_str = json.dumps(self.credentials)
            data["encrypted_credentials"] = self._encrypt(json_str)
        
        # Don't save plain credentials
        if "credentials" in data:
            del data["credentials"]
            
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any], path: Path) -> "AppState":
        """Create from dictionary."""
        # Handle nested dataclasses - filter to valid fields only
        if "window" in data and isinstance(data["window"], dict):
            window_fields = {"width", "height", "x", "y", "maximized"}
            filtered_window = {k: v for k, v in data["window"].items() if k in window_fields}
            data["window"] = WindowState(**filtered_window)
        else:
            data["window"] = WindowState()
        
        if "theme" in data and isinstance(data["theme"], dict):
            # Map legacy fields if present
            t = data["theme"]
            if "bg_color" in t and "bg_primary" not in t: t["bg_primary"] = t.pop("bg_color")
            if "fg_color" in t and "text_primary" not in t: t["text_primary"] = t.pop("fg_color")
            if "select_color" in t and "accent_primary" not in t: t["accent_primary"] = t.pop("select_color")
            
            theme_fields = {
                "name", 
                "bg_primary", "bg_secondary", "bg_tertiary",
                "text_primary", "text_secondary", "text_tertiary",
                "accent_primary", "accent_secondary",
                "border_subtle", "border_focus",
                "status_success", "status_warning", "status_danger", "status_info",
                "diff_add_bg", "diff_add_fg", "diff_del_bg", "diff_del_fg",
                "diff_header_bg", "diff_header_fg", "diff_hunk_bg", "diff_hunk_fg",
                "diff_font", "diff_font_size", "ui_font", "ui_font_size"
            }
            filtered_theme = {k: v for k, v in t.items() if k in theme_fields}
            data["theme"] = ThemeSettings(**filtered_theme)
        else:
            data["theme"] = ThemeSettings()
        
        # Filter to valid AppState fields
        valid_fields = {
            "window", "theme", "current_repo", "recent_repos", "max_recent_repos",
            "git_executable", "user_name", "user_email", "default_project_folder",
            "text_encoding", "language", "keep_backups", "auto_refresh", "refresh_on_focus",
            "reopen_repos_on_startup", "always_show_console", "check_remotes",
            "check_interval_minutes", "dpi_scaling", "global_ignore_file", "push_policy",
            "use_rebase_for_pull", "check_submodules", "push_all_tags",
            "no_fast_forward_merge", "show_author_date", "verbose_console",
            "allow_force_push", "safe_force_push", "history_limit",
            "show_ahead_behind", "use_column_guide", "column_guide_position",
            "fixed_width_commit_font", "push_after_commit", "stay_in_commit_dialog",
            "git_common_flags", "git_fetch_cmd", "git_pull_cmd", "git_push_cmd",
            "git_commit_cmd", "git_checkout_cmd",
            "ssh_key_path", "ssh_client", "ssh_accept_new", "auto_start_ssh_agent",
            "use_credential_manager", "credentials", "security_token", "open_repos",
        }
        
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        state = cls(**filtered)
        state._path = path
        
        # Handle blob encryption
        if "encrypted_credentials" in data:
            try:
                decrypted_json = state._decrypt(data["encrypted_credentials"])
                if decrypted_json:
                    state.credentials = json.loads(decrypted_json)
            except Exception:
                # If decryption fails, start with empty credentials
                state.credentials = {}
        # Legacy/Migration handling
        elif "credentials" in data:
            state.credentials = data["credentials"]
            # Migrate any "enc_password" fields from previous step
            for domain, creds in state.credentials.items():
                if isinstance(creds, dict) and "enc_password" in creds:
                    creds["password"] = state._decrypt(creds.pop("enc_password"))
        
        return state
    
    def save(self) -> None:
        """Save state to JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"Warning: Failed to save state: {e}")
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppState":
        """Load state from JSON file."""
        if path is None:
            path = get_config_dir() / "state.json"
        
        if not path.exists():
            state = cls()
            state._path = path
            return state
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data, path)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load state: {e}")
            state = cls()
            state._path = path
            return state
