"""
Git authentication utilities.

Handles URL rewriting and environment variable generation for Git operations
that require authentication (fetch, pull, push).
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from opentree.core.state import AppState


def get_auth_remote_url(repo_path: Path, state: AppState, remote: str = "origin") -> tuple[Optional[str], Optional[str], dict, str]:
    """
    Get remote URL and version with embedded credentials if available.
    
    Returns tuple: (original_url, auth_url, env_dict, password)
    - original_url: the original remote URL
    - auth_url: URL with embedded credentials (for HTTPS fallback)
    - env_dict: environment variables for authentication (for SSH)
    - password: password/passphrase for gitx.py
    
    For HTTPS: credentials embedded in URL work directly, or passed via gitx.
    For SSH: keys provided via GIT_SSH_COMMAND, or password passed via gitx.
    """
    from opentree.git.wrapper import run_git_capture
    
    if not repo_path.exists():
        return None, None, {}, ""
    
    env = {}
    password = ""
    
    try:
        # Get remote URL
        result = run_git_capture(
            ["remote", "get-url", remote],
            cwd=repo_path,
        )
        if not result.success:
            return None, None, {}, ""
            
        remote_url = result.stdout.strip()
        domain = None
        is_ssh = False
        ssh_port = None
        
        # Extract domain and detect SSH
        if remote_url.startswith('ssh://'):
            is_ssh = True
            match = re.search(r'ssh://(?:[^@]+@)?([^/:]+)(?::(\d+))?', remote_url)
            if match:
                domain = match.group(1)
                ssh_port = match.group(2)
        elif remote_url.startswith('https://') or remote_url.startswith('http://'):
            match = re.search(r'https?://(?:[^@]+@)?([^/:]+)', remote_url)
            if match:
                domain = match.group(1)
        elif '@' in remote_url and ':' in remote_url and not remote_url.startswith('git://'):
            is_ssh = True
            match = re.match(r'[^@]+@([^:]+):', remote_url)
            if match:
                domain = match.group(1)
        
        if not domain:
            return remote_url, None, {}, ""
        
        # Get credentials for domain
        creds = state.get_credentials(domain)
        if not creds:
            # Fallback/Default password for testing as per request
            # However, we should only use it if we are sure? 
            # The prompt said: "Use the password from gitx_test.cmd as a fallback or default if no other credentials are found"
            # Let's use it if nothing else is found, but maybe only if it looks like a test env?
            # Or just return empty string and let gitx fail/prompt?
            # User said: "I will assume this is a testing credential, but please confirm if I should use it as a default fallback."
            # User APPROVED the plan which said "We will use the password from gitx_test.cmd as a default for testing/development"
            pass
        
        # Determine password to return
        if creds:
            password = creds.get("password", "")
            if not password and creds.get("ssh_key_passphrase"):
                password = creds.get("ssh_key_passphrase")
        
        # If no password found in creds, use the fallback from gitx_test.cmd
        if not password:
             # This is a bit risky for production, but per instructions:
             password = "guest"

        if creds:
            username = creds.get("username", "guest")
            ssh_key = creds.get("ssh_key", "")
            
            # For SSH with key - use GIT_SSH_COMMAND
            if is_ssh and ssh_key and Path(ssh_key).exists():
                port_arg = f"-p {ssh_port}" if ssh_port else ""
                strict_checking = "accept-new" if getattr(state, "ssh_accept_new", False) else "yes"
                env["GIT_SSH_COMMAND"] = f'ssh {port_arg} -i "{ssh_key}" -o StrictHostKeyChecking={strict_checking} -o IdentitiesOnly=yes'
                return remote_url, None, env, password
            
            # For HTTPS - embed credentials in URL (Legacy/Fallback method combined with gitx)
            # gitx.py handles auth via askpass, so we might not need to embed in URL if gitx does its job.
            # But keeping it doesn't hurt as double layer unless they conflict.
            # actually, if we use gitx, git might prompt, and gitx answers.
            # If we embed in URL, git might not prompt.
            # Let's keep returning auth_url for now to be safe, but gitx is the primary target.
            
            encoded_user = quote(username, safe='') if username else ""
            encoded_pass = quote(password, safe='') if password else ""
            
            if encoded_user and encoded_pass:
                auth = f"{encoded_user}:{encoded_pass}@"
            elif encoded_user:
                auth = f"{encoded_user}@"
            else:
                auth = ""

            auth_url = None
            if auth:
                if remote_url.startswith('https://'):
                    auth_url = re.sub(r'https://([^@]+@)?', f'https://{auth}', remote_url)
                elif remote_url.startswith('http://'):
                    auth_url = re.sub(r'http://([^@]+@)?', f'http://{auth}', remote_url)
            
            return remote_url, auth_url, {}, password
            
    except Exception:
        pass
    
    return None, None, {}, password
