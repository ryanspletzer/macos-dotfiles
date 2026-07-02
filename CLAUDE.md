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
- Python packaging rules (never bare `pip`/`pipx`, use `uv`/`uvx`) live in
  the global `~/AGENTS.md`, since they apply machine-wide, not just here
- For detailed reference on all tracked configs (shell, git, tmux, nvim,
  VS Code, Zed, PowerShell, dev environment), invoke the
  `/dotfiles-reference` skill.
