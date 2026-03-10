import argparse
import os
import subprocess
import sys
from pathlib import Path
import uuid
import signal

def _is_windows() -> bool:
    return sys.platform.lower().startswith("win")

def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def _make_askpass(script_path: Path, password: str) -> None:
    if _is_windows():
        _write_text(
            script_path,
            f"""@echo off
setlocal enableextensions
set "prompt=%*"

if defined prompt (
  echo %prompt% | FINDSTR /I "password" >nul
  if %errorlevel%==0 (
    echo {password}
    exit /b 0
  )

  echo %prompt% | FINDSTR /I "passphrase" >nul
  if %errorlevel%==0 (
    echo {password}
    exit /b 0
  )
)

echo {password}
exit /b 0
""",
        )
    else:
        _write_text(
            script_path,
            f"""#!/bin/sh
prompt="$*"

if echo "$prompt" | grep -i -q "password"; then
  echo "{password}"
  exit 0
fi

if echo "$prompt" | grep -i -q "passphrase"; then
  echo "{password}"
  exit 0
fi

echo "{password}"
exit 0
""",
        )
        script_path.chmod(0o700)

def _build_env(askpass: Path, password: str) -> dict:
    env = os.environ.copy()
    if password:
        env["GIT_ASKPASS"] = str(askpass)
        env["SSH_ASKPASS"] = str(askpass)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["SSH_ASKPASS_REQUIRE"] = "force"
        if not _is_windows() and not env.get("DISPLAY"):
            env["DISPLAY"] = ":0"

    return env

def _run_git(git_args: list[str], env: dict) -> int:
    proc = subprocess.Popen(
        ["git", *git_args],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    while True:
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        sys.stdout.buffer.write(chunk)
        sys.stdout.flush()

    proc.wait()
    return int(proc.returncode or 0)

def _make_local_temp_files(base_dir: Path) -> Path:
    tag = uuid.uuid4().hex
    if _is_windows():
        askpass = base_dir / f".git_auto_askpass_{tag}.cmd"
    else:
        askpass = base_dir / f".git_auto_askpass_{tag}.sh"
    return askpass

def _cleanup(paths: list[Path]) -> None:
    for p in paths:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass

def main() -> int:
    parser = argparse.ArgumentParser(description="Simple Git wrapper to auto-input password/passphrase via ASKPASS for both HTTPS and SSH.")
    parser.add_argument("--password", required=True, help="The password or passphrase to auto-input (insecure!)")
    parser.add_argument("git_args", nargs=argparse.REMAINDER, help="Pass-through args. Use: -- <git args>")
    
    a = parser.parse_args()

    git_args = a.git_args
    if git_args and git_args[0] == "--":
        git_args = git_args[1:]
    if not git_args:
        print("Usage: python git_auto_pass.py --password <pass> -- <git args>", file=sys.stderr)
        return 2

    base_dir = Path(__file__).resolve().parent
    askpass = _make_local_temp_files(base_dir)
    to_cleanup = [askpass]

    def _handle_signal(sig, frame):
        _cleanup(to_cleanup)
        raise KeyboardInterrupt()

    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        _make_askpass(askpass, a.password)
        env = _build_env(askpass, a.password)
        rc = _run_git(git_args, env)
        return rc

    except KeyboardInterrupt:
        print("[git_auto] interrupted", file=sys.stderr)
        return 130

    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
        _cleanup(to_cleanup)

if __name__ == "__main__":
    raise SystemExit(main())