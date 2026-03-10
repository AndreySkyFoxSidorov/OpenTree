# OpenTree

OpenTree is a lightweight, cross-platform Git desktop client built with Python and Tkinter. It is designed for day-to-day repository work from a native GUI: reviewing changes, staging files, browsing history, searching commits, managing branches, tags, and stashes, and running common remote operations without leaving the app.

## Highlights

- Cross-platform desktop UI with no external Python dependencies
- Multi-repository workflow with tabbed sessions
- Staged, unstaged, untracked, and conflict-aware file views
- Inline diff viewer for working tree changes and commit patches
- Commit history with graph rendering, details, and search
- Branch, tag, stash, merge, cherry-pick, revert, and reset actions
- Theme, localization, SSH, and Git command settings
- Built-in command console for executed Git operations and diagnostics

## Requirements

- Python 3.11 or newer
- Git installed and available in `PATH`, or configured from the app

## Quick Start

```bash
git clone <your-repository-url>
cd OpenTree
python -m opentree
```

Alternative launchers:

- Windows: `run.bat`
- Linux/macOS: `./run.sh`

## What You Can Do

### Working Copy

- Review staged, unstaged, untracked, and conflicted files
- Stage or unstage selected files or all files at once
- Discard local changes with confirmation
- Create commits with subject and body

### History and Search

- Browse recent commit history with a visual graph
- Inspect commit metadata, stats, and full patches
- Search commits by message or author

### Branches, Tags, and Stashes

- Switch, create, track, and delete branches
- List, create, and delete tags
- Create, apply, pop, and drop stashes

### Remote Operations

- Refresh repository state
- Fetch with pruning
- Pull with merge or rebase behavior from settings
- Push, including guarded force-push workflows

## Project Layout

```text
opentree/
  __main__.py          Entry point
  app.py               Application controller
  core/                State, themes, events, sessions, domain models
  git/                 Git command builders, runners, auth helpers, parsers
  ui/                  Main window, dialogs, widgets, search, progress UI
  utils/               Paths, platform helpers, icons, text utilities
  icons/               Application icons
  tests_parsers.py     Lightweight parser and graph tests
```

## Development

Run the parser and graph tests:

```bash
python -m opentree.tests_parsers
```

Local runtime state is written to `opentree/state.json` when running from a source checkout. That file can include recent repositories, user identity, SSH settings, a security token, and encrypted credentials, so it is intentionally ignored by Git and must stay local.

## Troubleshooting

### Git Is Not Detected

1. Install Git from [git-scm.com](https://git-scm.com/downloads).
2. Verify it works from a terminal with `git --version`.
3. If needed, set the full Git executable path from the OpenTree settings dialog.

### Text or Path Encoding Looks Wrong

- Use UTF-8 in the application settings where possible.
- Check `git config --global core.quotepath false`.

## Contributing

Issues and pull requests are welcome. Helpful contributions include bug fixes, UI polishing, performance improvements, parser coverage, and additional Git workflows.
