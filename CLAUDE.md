# Home Folder Configuration

This is Ryan Spletzer's source-controlled home folder on macOS.
The repository uses an **ignore-everything-then-selectively-un-ignore**
strategy via `.gitignore`.

## Gitignore Strategy

```text
/*                    # Ignore everything by default
!/.bashrc             # Un-ignore specific files with !
!/.config             # Un-ignore directory
/.config/*            # Re-ignore contents
!/.config/fish        # Un-ignore specific subdirectory
```

This pattern allows selective versioning of dotfiles and configs while keeping
everything else out of git.

## Notes for Claude

- This is a **home folder repo** — be careful with file operations
- Use the existing `.gitignore` pattern when adding new tracked files
- Shell configs are duplicated across bash/zsh/fish/pwsh — keep them in sync
- The `syncremote` function is for fork workflows
  (origin = fork, upstream = parent)
- pyenv auto-activation depends on `.python-version` files
  in project directories
- **Never use bare `pip install` or `pip3 install`** — the system Python is
  externally managed (PEP 668) and Homebrew-owned.
  Use `uv pip install` (inside a venv), `uv add` (for project dependencies),
  or `uv tool install` / `uvx` (for standalone CLI tools) instead.
  **Never use `pipx`** — use `uvx` (replaces `pipx run`) or
  `uv tool install` (replaces `pipx install`).
  PreToolUse hooks enforce both rules.
- For detailed reference on all tracked configs (shell, git, tmux, nvim,
  VS Code, Zed, PowerShell, dev environment), invoke the
  `/dotfiles-reference` skill.
