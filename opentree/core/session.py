"""
Repository session management.

Handles state and operations for a single open repository tab.
"""

import tkinter as tk
from pathlib import Path
from typing import Optional
import tempfile

from opentree.core.models import (
    BranchInfo,
    CommitInfo,
    CommandResult,
    FileStatus,
    RepoInfo,
)
from opentree.core.state import AppState
from opentree.git.runner import GitRunner, SyncGitRunner
from opentree.git import commands, parsers
from opentree.ui.main_window import RepoView
from opentree.ui.task_runner import TaskRunner
from opentree.git.auth import get_auth_remote_url
from opentree.ui.dialogs import (
    CreateTagDialog,
    ErrorDialog,
    MergeDialog,
    NewBranchDialog,
    ConfirmDialog,
    InfoDialog,
    ResetDialog,
    StashDialog,
)

class RepoSession:
    """
    Manages a single repository session (tab).
    """
    
    def __init__(self, master: tk.Widget, repo_path: Path, app_state: AppState):
        self._master = master
        self._root = master.winfo_toplevel()
        self.repo_path = repo_path
        self.app_state = app_state
        
        # Repo info
        self.repo = RepoInfo(path=repo_path)
        
        # Git runners
        git_path = app_state.git_executable or "git"
        self._git = GitRunner(self._root, git_path)
        self._sync_git = SyncGitRunner(git_path)
        self._task_runner = TaskRunner(self._root)
        
        if app_state.ssh_key_path:
            self._git.set_ssh_key(app_state.ssh_key_path)
            
        # UI
        self.view = RepoView(master)
        
        # State
        self._staged_files: list[FileStatus] = []
        self._unstaged_files: list[FileStatus] = []
        self._status_request_serial = 0
        self._history_requested_count = max(20, self.app_state.history_limit)
        self._history_has_more = True
        self._history_loading = False
        
        self._setup_bindings()
        
        # Initial refresh
        self.view.set_status(f"Repository: {self.repo.name}")
        self.view.enable_repo_actions(True)
        self._update_author_info()
        
        # Initialize UI state
        self.view.file_status_panel.set_push_immediately(self.app_state.push_after_commit)
        
        self.refresh()
        
    def _setup_bindings(self) -> None:
        """Setup UI event bindings for this session."""
        view = self.view
        tb = view.toolbar
        fsp = view.file_status_panel
        hp = view.history_panel
        
        # Toolbar
        tb.pull_btn.configure(command=self.cmd_pull)
        tb.push_btn.configure(command=self.cmd_push)
        tb.fetch_btn.configure(command=self.cmd_fetch)
        tb.branch_btn.configure(command=self.cmd_new_branch)
        tb.merge_btn.configure(command=self.cmd_merge)
        tb.refresh_btn.configure(command=self.cmd_refresh)
        tb.stash_btn.configure(command=self.cmd_stash_manager)
        # Settings button handled by App
        
        # File Status Panel
        fsp.stage_btn.configure(command=self.cmd_stage)
        fsp.stage_all_btn.configure(command=self.cmd_stage_all)
        fsp.unstage_btn.configure(command=self.cmd_unstage)
        fsp.unstage_all_btn.configure(command=self.cmd_unstage_all)
        fsp.commit_btn.configure(command=self.cmd_commit)
        
        fsp.unstaged_list._on_select = self._on_unstaged_select
        fsp.staged_list._on_select = self._on_staged_select
        
        # History Panel
        hp.commit_list._on_select = self._on_commit_select
        hp.commit_list._on_reach_bottom = self._load_more_history
        
        # Sidebar
        view.sidebar.branch_tree._tree.bind("<Double-1>", self._on_branch_double_click)
        view.sidebar.branch_tree.bind_context_menu(self._show_branch_context_menu)
        view.sidebar.tag_tree._on_select = self._on_tag_select
        view.sidebar.tag_tree.bind_context_menu(self._show_tag_context_menu)
        view.sidebar.stash_tree._on_select = self._on_stash_select
        
        # Search Panel
        view.search_panel._on_search = self._on_search_request
        view.search_panel.commit_list._on_select = self._on_search_commit_select
        
        # Context menus
        hp.commit_list.bind_context_menu(self._show_history_commit_context_menu)
        view.search_panel.commit_list.bind_context_menu(self._show_search_commit_context_menu)
        fsp.unstaged_list.bind_context_menu(self._show_unstaged_context_menu)
        fsp.staged_list.bind_context_menu(self._show_staged_context_menu)
        
        # Bind push toggle
        view.file_status_panel._commit_panel.bind_push_toggled(self._on_push_toggled)

    def _on_push_toggled(self, value: bool) -> None:
        """Save push preference immediately."""
        if self.app_state.push_after_commit != value:
            self.app_state.push_after_commit = value
            self.app_state.save()

    def _update_author_info(self) -> None:
        """Update author info from settings or git config."""
        name = self.app_state.user_name
        email = self.app_state.user_email
        
        if not name:
            result = self._sync_git.run(["git", "config", "user.name"], self.repo_path)
            name = result.stdout.strip() if result.success else "Unknown"
        if not email:
            result = self._sync_git.run(["git", "config", "user.email"], self.repo_path)
            email = result.stdout.strip() if result.success else ""
        
        author = f"{name} <{email}>" if email else name
        self.view.file_status_panel.set_author(author)

    def refresh(self) -> None:
        """Refresh all data for this repository."""
        self._refresh_status()
        self._refresh_branches()
        self._refresh_log()
        self._refresh_tags()
        self._refresh_stashes()

    def apply_settings(self, refresh_repo: bool = False) -> None:
        """Apply updated app settings to the current open session."""
        self._update_author_info()
        self.view.file_status_panel.set_push_immediately(self.app_state.push_after_commit)
        if refresh_repo:
            self.cmd_refresh()

    def cmd_refresh(self) -> None:
        """Force a responsive refresh from the toolbar."""
        self._git.cancel_all()
        self._refresh_status_sync()
        self._refresh_branches()
        self._refresh_log()
        self._refresh_tags()
        self._refresh_stashes()

    def _wrap_gitx(self, cmd: list[str], password: str = "") -> list[str]:
        from opentree.git.wrapper import get_git_command
        git_args = cmd[1:] if (cmd and cmd[0] == "git") else cmd
        extra_flags = [
            "-c", "diff.mnemonicprefix=false",
            "-c", "core.quotepath=false",
            "--no-optional-locks"
        ]
        return get_git_command(extra_flags + git_args, password=password)

    # --- Git Operations ---

    def _next_status_request_id(self) -> int:
        """Allocate a new status request id to ignore stale callbacks."""
        self._status_request_serial += 1
        return self._status_request_serial

    def _refresh_status(self) -> None:
        request_id = self._next_status_request_id()
        self._git.run(
            commands.cmd_status(),
            self.repo_path,
            lambda result, request_id=request_id: self._on_status_result(result, request_id),
        )

    def _refresh_status_sync(self) -> None:
        """Refresh file status immediately for the toolbar refresh action."""
        request_id = self._next_status_request_id()
        result = self._sync_git.run(commands.cmd_status(), self.repo_path)
        self._on_status_result(result, request_id)

    def _on_status_result(self, result: CommandResult, request_id: Optional[int] = None) -> None:
        if request_id is not None and request_id != self._status_request_serial:
            return
        if result.success:
            file_status_panel = self.view.file_status_panel
            staged_selection = file_status_panel.staged_list.get_selected_paths()
            unstaged_selection = file_status_panel.unstaged_list.get_selected_paths()
            files = parsers.parse_status_v2(result.stdout.encode("utf-8") if isinstance(result.stdout, str) else result.stdout)
            staged, unstaged, untracked, conflicts = parsers.split_status_by_kind(files)
            
            self._staged_files = staged
            self._unstaged_files = unstaged + untracked + conflicts
            
            file_status_panel.staged_list.set_files(self._staged_files)
            file_status_panel.unstaged_list.set_files(self._unstaged_files)
            file_status_panel.staged_list.restore_selection(staged_selection)
            file_status_panel.unstaged_list.restore_selection(unstaged_selection)
            
            # Update repo branch info if changed (status output often has branch info)
            if result.stdout:
                lines = (result.stdout if isinstance(result.stdout, str) else result.stdout.decode("utf-8", errors="ignore")).splitlines()
                if lines and lines[0].startswith("##"):
                    # Extract branch name from status header if needed
                    pass
        else:
            print(f"Status failed: {result.stderr}")

    def _refresh_branches(self) -> None:
        self._git.run(commands.cmd_branch_list(), self.repo_path, self._on_branches_result)

    def _on_branches_result(self, result: CommandResult) -> None:
        if result.success:
            branches = parsers.parse_branches(result.stdout)
            self.repo.branches = branches
            # self.repo.current_branch is a property derived from branches, no setter needed
            current = next((b for b in branches if b.is_current), None)
            
            self.view.sidebar.set_branches(branches)
            if current:
                self.view.set_status(f"Repository: {self.repo.name} ({current.name})")

    def _refresh_log(self) -> None:
        self._history_requested_count = self._history_page_size()
        self._history_has_more = True
        self._history_loading = False
        self.view.history_panel.commit_list.reset_load_more_state()
        self._request_history_log()

    def _request_history_log(
        self,
        preserve_view: bool = False,
    ) -> None:
        """Request commit history using the current paging window."""
        if self._history_loading:
            return

        commit_list = self.view.history_panel.commit_list
        top_hash = commit_list.get_top_visible_commit_hash() if preserve_view else None
        selected_hash = commit_list.get_selected_hash() if preserve_view else None
        requested_count = self._history_requested_count

        self._history_loading = True
        self._git.run(
            commands.cmd_log(requested_count),
            self.repo_path,
            lambda result, requested_count=requested_count, top_hash=top_hash, selected_hash=selected_hash:
                self._on_log_result(result, requested_count, top_hash, selected_hash),
        )

    def _on_log_result(
        self,
        result: CommandResult,
        requested_count: Optional[int] = None,
        top_hash: Optional[str] = None,
        selected_hash: Optional[str] = None,
    ) -> None:
        self._history_loading = False
        if result.success:
            commits = parsers.parse_log(result.stdout)
            self.repo.commits = commits
            self._history_has_more = len(commits) >= (requested_count or self._history_requested_count)
            commit_list = self.view.history_panel.commit_list
            commit_list.set_commits(commits)
            if top_hash or selected_hash:
                commit_list.restore_view(top_hash=top_hash, selected_hash=selected_hash)

    def _history_page_size(self) -> int:
        """Get the number of commits to request per page."""
        return max(20, self.app_state.history_limit)

    def _load_more_history(self) -> None:
        """Expand the history window when the user scrolls near the bottom."""
        if self._history_loading or not self._history_has_more:
            return
        self._history_requested_count += self._history_page_size()
        self._request_history_log(preserve_view=True)

    def _refresh_tags(self) -> None:
        self._git.run(commands.cmd_tag_list(), self.repo_path, self._on_tags_result)

    def _on_tags_result(self, result: CommandResult) -> None:
        if result.success:
            tags = parsers.parse_tags(result.stdout)
            self.repo.tags = tags
            self.view.sidebar.set_tags(tags)

    def _refresh_stashes(self) -> None:
        self._git.run(commands.cmd_stash_list(), self.repo_path, self._on_stashes_result)

    def _on_stashes_result(self, result: CommandResult) -> None:
        if result.success:
            stashes = parsers.parse_stash_list(result.stdout)
            self.repo.stashes = stashes
            self.view.sidebar.stash_tree.set_stashes(stashes)

    # --- Commands ---

    def _find_branch(self, name: str) -> Optional[BranchInfo]:
        """Find branch info by name."""
        return next((branch for branch in self.repo.branches if branch.name == name), None)

    def _run_refresh_action(
        self,
        title: str,
        command: list[str],
        success_message: Optional[str] = None,
    ) -> None:
        """Run a git command and refresh UI on success."""
        self._git.run(
            command,
            self.repo_path,
            lambda result: self._on_refresh_action_complete(title, result, success_message),
        )

    def _on_refresh_action_complete(
        self,
        title: str,
        result: CommandResult,
        success_message: Optional[str] = None,
    ) -> None:
        """Refresh the repo after an action."""
        if result.success:
            self.refresh()
            if success_message:
                InfoDialog.show(self._root, title, success_message)
        else:
            ErrorDialog.show(self._root, f"{title} Failed", result.stderr or result.stdout)

    def cmd_fetch(self) -> None:
        orig_url, auth_url, env, password = get_auth_remote_url(self.repo_path, self.app_state)
        cmd = commands.cmd_fetch()
        if orig_url and auth_url:
            cmd = ["git", "-c", f"url.{auth_url}.insteadOf={orig_url}"] + cmd[1:]
        
        if password:
            env["GIT_PASSWORD"] = password
            env["SSH_PASSPHRASE"] = password
            
        cmd = self._wrap_gitx(cmd, password)
        self._task_runner.run_with_progress("Fetching", cmd, cwd=str(self.repo_path), env=env, on_success=self._on_fetch_complete)

    def _on_fetch_complete(self, result: CommandResult) -> None:
        if result.success:
            self.refresh()
        else:
            ErrorDialog.show(self._root, "Fetch Failed", result.stderr)

    def cmd_pull(self) -> None:
        orig_url, auth_url, env, password = get_auth_remote_url(self.repo_path, self.app_state)
        rebase = self.app_state.use_rebase_for_pull
        remote = "origin"
        branch = self.repo.current_branch.name if self.repo.current_branch else None
        
        cmd = commands.cmd_pull(remote=remote, branch=branch, rebase=rebase)
        if orig_url and auth_url:
            cmd = ["git", "-c", f"url.{auth_url}.insteadOf={orig_url}"] + cmd[1:]
        
        if password:
            env["GIT_PASSWORD"] = password
            env["SSH_PASSPHRASE"] = password
            
        cmd = self._wrap_gitx(cmd, password)
        self._task_runner.run_with_progress("Pulling", cmd, cwd=str(self.repo_path), env=env, on_success=self._on_pull_complete)

    def _on_pull_complete(self, result: CommandResult) -> None:
        if result.success:
            self.refresh()
        else:
            ErrorDialog.show(self._root, "Pull Failed", result.stderr)

    def cmd_push(self) -> None:
        orig_url, auth_url, env, password = get_auth_remote_url(self.repo_path, self.app_state)
        force = self.app_state.allow_force_push and self.app_state.safe_force_push
        cmd = commands.cmd_push(force=force)
        
        if orig_url and auth_url:
            cmd = ["git", "-c", f"url.{auth_url}.insteadOf={orig_url}"] + cmd[1:]
            
        if password:
            env["GIT_PASSWORD"] = password
            env["SSH_PASSPHRASE"] = password
            
        cmd = self._wrap_gitx(cmd, password)
        self._task_runner.run_with_progress("Pushing", cmd, cwd=str(self.repo_path), env=env, on_success=self._on_push_complete)

    def _on_push_complete(self, result: CommandResult) -> None:
        if result.success:
            self.refresh()
            InfoDialog.show(self._root, "Push", "Push completed successfully.")
        else:
            ErrorDialog.show(self._root, "Push Failed", result.stderr)

    def cmd_stage(self) -> None:
        files = self.view.file_status_panel.unstaged_list.get_selected()
        if files:
            paths = [f.path for f in files]
            self._git.run(commands.cmd_add(paths), self.repo_path, lambda r: self._on_stage_complete(r))

    def cmd_stage_all(self) -> None:
        files = self.view.file_status_panel.unstaged_list.get_all()
        if files:
            paths = [f.path for f in files]
            self._git.run(commands.cmd_add(paths), self.repo_path, lambda r: self._on_stage_complete(r))

    def _on_stage_complete(self, result: CommandResult) -> None:
        self._refresh_status()

    def cmd_unstage(self) -> None:
        files = self.view.file_status_panel.staged_list.get_selected()
        if files:
            paths = [f.path for f in files]
            self._git.run(commands.cmd_restore_staged(paths), self.repo_path, lambda r: self._on_stage_complete(r))

    def cmd_unstage_all(self) -> None:
        files = self.view.file_status_panel.staged_list.get_all()
        if files:
            paths = [f.path for f in files]
            self._git.run(commands.cmd_restore_staged(paths), self.repo_path, lambda r: self._on_stage_complete(r))

    def cmd_discard_selected(self) -> None:
        """Discard unstaged changes for selected files."""
        files = self.view.file_status_panel.unstaged_list.get_selected()
        if not files:
            return

        tracked_paths = [file.path for file in files if file.unstaged_status != "?"]
        untracked_paths = [file.path for file in files if file.unstaged_status == "?"]
        if not ConfirmDialog.show(
            self._root,
            "Discard Changes",
            f"Discard changes in {len(files)} selected file(s)?",
            is_destructive=True,
        ):
            return

        if tracked_paths:
            self._git.run(
                commands.cmd_restore(tracked_paths),
                self.repo_path,
                lambda result: self._on_discard_tracked_complete(result, untracked_paths),
            )
        elif untracked_paths:
            self._run_refresh_action("Discard Changes", commands.cmd_clean(untracked_paths))

    def _on_discard_tracked_complete(self, result: CommandResult, untracked_paths: list[str]) -> None:
        """Continue discard flow for untracked files after restore."""
        if not result.success:
            ErrorDialog.show(self._root, "Discard Changes Failed", result.stderr or result.stdout)
            return
        if untracked_paths:
            self._run_refresh_action("Discard Changes", commands.cmd_clean(untracked_paths))
        else:
            self.refresh()

    def cmd_commit(self) -> None:
        message = self.view.file_status_panel.get_commit_message()
        if not message:
            ErrorDialog.show(self._root, "Cannot Commit", "Please enter a commit message.")
            return
        if not self._staged_files:
            ErrorDialog.show(self._root, "Cannot Commit", "No files are staged.")
            return
            
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(message)
            message_file = Path(f.name)
            
        self._git.run(commands.cmd_commit(message_file), self.repo_path, lambda r: self._on_commit_complete(r, message_file))

    def _on_commit_complete(self, result: CommandResult, message_file: Path) -> None:
        try:
            message_file.unlink()
        except:
            pass

        if result.success:
            self.view.file_status_panel.clear_commit_message()
            self.refresh()

            push_now = self.view.file_status_panel.push_immediately
            if push_now != self.app_state.push_after_commit:
                self.app_state.push_after_commit = push_now
                self.app_state.save()

            if push_now:
                self.cmd_push()
        else:
            ErrorDialog.show(self._root, "Commit Failed", result.stderr)

    def cmd_new_branch(self) -> None:
        dialog = NewBranchDialog(self._root)
        name = dialog.wait()
        if name:
            self._run_refresh_action("Create Branch", commands.cmd_new_branch(name))

    def _create_branch_from_ref(self, ref: str, label: str) -> None:
        """Create and checkout a branch from the given ref."""
        dialog = NewBranchDialog(
            self._root,
            title="Create Branch",
            prompt=f"Branch name from {label}:",
        )
        name = dialog.wait()
        if name:
            self._run_refresh_action("Create Branch", commands.cmd_new_branch(name, start_point=ref))

    def _create_tag_from_ref(self, ref: str, label: str) -> None:
        """Create a tag from the given ref."""
        dialog = CreateTagDialog(self._root, target_label=label)
        result = dialog.wait()
        if result:
            name, message, force = result
            self._run_refresh_action(
                "Create Tag",
                commands.cmd_create_tag(name, target=ref, message=message or None, force=force),
            )

    def _delete_tag(self, tag_name: str) -> None:
        """Delete a tag after confirmation."""
        if ConfirmDialog.show(
            self._root,
            "Delete Tag",
            f"Delete tag '{tag_name}'?",
            is_destructive=True,
        ):
            self._run_refresh_action("Delete Tag", commands.cmd_delete_tag(tag_name))

    def _checkout_ref(self, ref: str, label: str, detached: bool = False) -> None:
        """Checkout a branch, tag, or commit."""
        if detached:
            ok = ConfirmDialog.show(
                self._root,
                "Checkout Commit",
                f"Checkout {label} in detached HEAD state?",
                is_destructive=False,
            )
            if not ok:
                return
        self._run_refresh_action("Checkout", commands.cmd_checkout(ref))

    def _checkout_branch(self, branch: BranchInfo) -> None:
        """Checkout a local branch or create a tracking branch from a remote."""
        if branch.is_remote:
            self._run_refresh_action("Checkout", commands.cmd_checkout_track(branch.name))
        else:
            self._checkout_ref(branch.name, branch.name)

    def _cherry_pick_commit(self, commit: CommitInfo) -> None:
        """Cherry-pick a commit onto the current branch."""
        if len(commit.parents) > 1:
            ErrorDialog.show(self._root, "Cherry-pick Failed", "Cherry-picking merge commits is not supported yet.")
            return
        if ConfirmDialog.show(self._root, "Cherry-pick", f"Cherry-pick {commit.short_hash} onto the current branch?"):
            self._run_refresh_action(
                "Cherry-pick",
                commands.cmd_cherry_pick(commit.hash),
                success_message="Cherry-pick completed successfully.",
            )

    def _revert_commit(self, commit: CommitInfo) -> None:
        """Revert a commit on the current branch."""
        if len(commit.parents) > 1:
            ErrorDialog.show(self._root, "Revert Failed", "Reverting merge commits is not supported yet.")
            return
        if ConfirmDialog.show(self._root, "Revert Commit", f"Create a revert commit for {commit.short_hash}?"):
            self._run_refresh_action(
                "Revert Commit",
                commands.cmd_revert(commit.hash),
                success_message="Revert completed successfully.",
            )

    def _reset_to_commit(self, commit: CommitInfo) -> None:
        """Reset current branch to the selected commit."""
        dialog = ResetDialog(self._root, commit.short_hash)
        mode = dialog.wait()
        if not mode:
            return

        confirm = ConfirmDialog.show(
            self._root,
            "Reset Branch",
            f"Reset current branch to {commit.short_hash} using {mode} reset?",
            is_destructive=mode == "hard",
        )
        if confirm:
            self._run_refresh_action(
                "Reset Branch",
                commands.cmd_reset(commit.hash, mode),
                success_message=f"Branch reset ({mode}) completed.",
            )

    def cmd_merge(self) -> None:
        branches = [b.name for b in self.repo.branches]
        current = self.repo.current_branch.name if self.repo.current_branch else ""
        dialog = MergeDialog(self._root, branches, current)
        result = dialog.wait()
        if result:
            branch, squash = result
            self._git.run(commands.cmd_merge(branch, squash=squash), self.repo_path, self._on_merge_complete)

    def _merge_branch(self, branch_name: str) -> None:
        """Merge a specific branch into the current one."""
        self._git.run(commands.cmd_merge(branch_name), self.repo_path, self._on_merge_complete)

    def _on_merge_complete(self, result: CommandResult) -> None:
        if result.success:
            InfoDialog.show(self._root, "Merge", "Merge completed successfully.")
            self.refresh()
        else:
            if "conflict" in result.stdout.lower() or "conflict" in result.stderr.lower():
                ErrorDialog.show(self._root, "Merge Conflicts", "Merge resulted in conflicts.", result.stdout + "\n" + result.stderr)
                self.refresh()
            else:
                ErrorDialog.show(self._root, "Merge Failed", result.stderr)

    def cmd_stash_manager(self) -> None:
        """Open stash manager dialog."""
        dialog = StashDialog(self._root, self.repo.stashes)
        result = dialog.wait()
        
        if not result:
            return
            
        action, data = result
        if action == "push":
            self._git.run(commands.cmd_stash_push(data), self.repo_path, self._on_stash_action_complete)
        elif action == "pop":
            self._git.run(commands.cmd_stash_pop(data), self.repo_path, self._on_stash_action_complete)
        elif action == "apply":
            self._git.run(commands.cmd_stash_apply(data), self.repo_path, self._on_stash_action_complete)
        elif action == "drop":
            self._git.run(commands.cmd_stash_drop(data), self.repo_path, self._on_stash_action_complete)

    def _on_stash_action_complete(self, result: CommandResult) -> None:
        if result.success:
            InfoDialog.show(self._root, "Stash", "Operation completed successfully.")
            self.refresh()
        else:
            ErrorDialog.show(self._root, "Stash Failed", result.stderr)

    # --- Event Handlers ---

    def _on_unstaged_select(self, file: Optional[FileStatus]) -> None:
        if file:
            self.view.file_status_panel.set_diff_file(file.path)
            self._show_diff(file.path, staged=False)

    def _on_staged_select(self, file: Optional[FileStatus]) -> None:
        if file:
            self.view.file_status_panel.set_diff_file(file.path)
            self._show_diff(file.path, staged=True)

    def _show_diff(self, path: str, staged: bool) -> None:
        self._git.run(commands.cmd_diff(path, staged=staged), self.repo_path, lambda r: self._on_diff_result(r))

    def _on_diff_result(self, result: CommandResult) -> None:
        if result.success:
            self.view.file_status_panel.diff_viewer.set_content(result.stdout)

    def _on_commit_select(self, commit: Optional[CommitInfo]) -> None:
        if commit and commit.hash:
            self._git.run(commands.cmd_show(commit.hash, stat_only=True), self.repo_path, self._on_commit_details_result)
            self._git.run(commands.cmd_show(commit.hash, patch_only=True), self.repo_path, self._on_commit_diff_result)

    def _on_commit_details_result(self, result: CommandResult) -> None:
        if result.success:
            self.view.history_panel.set_details(result.stdout)

    def _on_commit_diff_result(self, result: CommandResult) -> None:
        if result.success:
            self.view.history_panel.diff_viewer.set_content(result.stdout)

    def _on_branch_double_click(self, event: tk.Event) -> None:
        branch = self.view.sidebar.get_selected_branch()
        if branch:
            branch_info = self._find_branch(branch)
            if branch_info:
                self._checkout_branch(branch_info)

    def _on_tag_select(self, tag_name: Optional[str]) -> None:
        """Handle tag selection in sidebar."""
        if tag_name:
            self.view._show_view("history")
            self._git.run(commands.cmd_show(tag_name, stat_only=True), self.repo_path, self._on_commit_details_result)
            self._git.run(commands.cmd_show(tag_name, patch_only=True), self.repo_path, self._on_commit_diff_result)

    def _on_stash_select(self, index: Optional[int]) -> None:
        """Handle stash selection in sidebar."""
        if index is not None:
            self.view._show_view("history")
            stash_ref = f"stash@{{{index}}}"
            self._git.run(commands.cmd_show(stash_ref, stat_only=True), self.repo_path, self._on_commit_details_result)
            self._git.run(commands.cmd_show(stash_ref, patch_only=True), self.repo_path, self._on_commit_diff_result)

    def _on_search_request(self, term: str, search_type: str) -> None:
        author = term if search_type == "author" else None
        grep = term if search_type == "grep" else None
        self._git.run(commands.cmd_log(count=100, all_branches=True, author=author, grep=grep), self.repo_path, self._on_search_result)

    def _on_search_result(self, result: CommandResult) -> None:
        if result.success:
            commits = parsers.parse_log(result.stdout)
            self.view.search_panel.set_results(commits)

    def _on_search_commit_select(self, commit: Optional[CommitInfo]) -> None:
        if commit and commit.hash:
            self._git.run(
                commands.cmd_show(commit.hash, stat_only=True),
                self.repo_path,
                self._on_search_commit_details_result,
            )
            self._git.run(
                commands.cmd_show(commit.hash, patch_only=True),
                self.repo_path,
                self._on_search_commit_diff_result,
            )

    def _on_search_commit_details_result(self, result: CommandResult) -> None:
        if result.success:
            self.view.search_panel.set_details(result.stdout)

    def _on_search_commit_diff_result(self, result: CommandResult) -> None:
        if result.success:
            self.view.search_panel.diff_viewer.set_content(result.stdout)

    def _show_history_commit_context_menu(self, event: tk.Event) -> None:
        commit = self.view.history_panel.commit_list.select_at_event(event)
        self._show_commit_context_menu(event, commit)

    def _show_search_commit_context_menu(self, event: tk.Event) -> None:
        commit = self.view.search_panel.commit_list.select_at_event(event)
        self._show_commit_context_menu(event, commit)

    def _show_commit_context_menu(self, event: tk.Event, commit: Optional[CommitInfo]) -> None:
        """Show commit actions menu."""
        if not commit or not commit.hash:
            return

        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="Checkout Commit", command=lambda: self._checkout_ref(commit.hash, commit.short_hash, detached=True))
        menu.add_command(label="Create Branch From Commit...", command=lambda: self._create_branch_from_ref(commit.hash, commit.short_hash))
        menu.add_command(label="Create Tag From Commit...", command=lambda: self._create_tag_from_ref(commit.hash, commit.short_hash))
        menu.add_separator()
        menu.add_command(label="Cherry-pick Commit", command=lambda: self._cherry_pick_commit(commit))
        menu.add_command(label="Revert Commit", command=lambda: self._revert_commit(commit))
        menu.add_separator()
        menu.add_command(label="Reset Current Branch To Here...", command=lambda: self._reset_to_commit(commit))
        menu.tk_popup(event.x_root, event.y_root)

    def _show_branch_context_menu(self, event: tk.Event) -> None:
        """Show branch actions menu."""
        branch_name = self.view.sidebar.branch_tree.select_at_event(event)
        branch = self._find_branch(branch_name) if branch_name else None
        if not branch:
            return

        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="Checkout Branch", command=lambda: self._checkout_branch(branch))
        if not branch.is_remote and not branch.is_current:
            menu.add_command(label="Merge Into Current Branch", command=lambda: self._merge_branch(branch.name))
            menu.add_command(
                label="Delete Branch",
                command=lambda: self._delete_branch(branch.name),
            )
        menu.tk_popup(event.x_root, event.y_root)

    def _delete_branch(self, branch_name: str) -> None:
        """Delete a local branch."""
        if ConfirmDialog.show(
            self._root,
            "Delete Branch",
            f"Delete branch '{branch_name}'?",
            is_destructive=True,
        ):
            self._run_refresh_action("Delete Branch", commands.cmd_delete_branch(branch_name))

    def _show_tag_context_menu(self, event: tk.Event) -> None:
        """Show tag actions menu."""
        tag_name = self.view.sidebar.tag_tree.select_at_event(event)
        if not tag_name:
            return

        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="Checkout Tag", command=lambda: self._checkout_ref(tag_name, tag_name))
        menu.add_command(label="Create Branch From Tag...", command=lambda: self._create_branch_from_ref(tag_name, tag_name))
        menu.add_separator()
        menu.add_command(label="Delete Tag", command=lambda: self._delete_tag(tag_name))
        menu.tk_popup(event.x_root, event.y_root)

    def _show_unstaged_context_menu(self, event: tk.Event) -> None:
        """Show context menu for unstaged files."""
        self.view.file_status_panel.unstaged_list.select_at_event(event)
        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="Stage Selected", command=self.cmd_stage)
        menu.add_command(label="Discard Selected Changes", command=self.cmd_discard_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def _show_staged_context_menu(self, event: tk.Event) -> None:
        """Show context menu for staged files."""
        self.view.file_status_panel.staged_list.select_at_event(event)
        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="Unstage Selected", command=self.cmd_unstage)
        menu.tk_popup(event.x_root, event.y_root)

    def refresh_theme(self) -> None:
        """Update UI for theme change."""
        if hasattr(self.view, "refresh_theme"):
            self.view.refresh_theme()
