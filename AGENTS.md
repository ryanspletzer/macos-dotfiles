# Global Agent Instructions

## Markdown

When creating or editing any Markdown — including brand-new files —
the output must pass markdownlint-cli2 (fix issues automatically, never ask)
and use semantic line breaks (one sentence per line).

## Git workflow

When re-syncing a branch with its base branch,
always prefer merge commits over rebasing.

## Python packaging

Never use bare `pip install` or `pip3 install` —
the system Python is externally managed (PEP 668) and Homebrew-owned.
Use `uv pip install` (inside a venv),
`uv add` (for project dependencies),
or `uv tool install` / `uvx` (for standalone CLI tools) instead.
Never use `pipx` —
use `uvx` (replaces `pipx run`) or `uv tool install` (replaces `pipx install`).
Never create virtual environments with `python -m venv` or `virtualenv` —
use `uv venv`.
Run pytest via `uv run pytest`, never bare `pytest`.

## PowerShell module management

Always use the modern PSResourceGet cmdlets
instead of the legacy PowerShellGet ones:
`Get-PSResource` (not `Get-InstalledModule`),
`Find-PSResource` (not `Find-Module`),
`Install-PSResource` (not `Install-Module`),
`Update-PSResource` (not `Update-Module`),
`Uninstall-PSResource` (not `Uninstall-Module`),
and `Publish-PSResource` (not `Publish-Module`).
Plain `Get-Module` is acceptable only for inspecting modules
already imported into the current session.

## Home folder repository (macos-dotfiles)

This section applies when the working directory is the home folder (`~`) itself.
`~` is Ryan Spletzer's source-controlled home folder on macOS.
The repository uses an **ignore-everything-then-selectively-un-ignore**
strategy via `.gitignore`.

### Gitignore strategy

```text
/*                    # Ignore everything by default
!/.bashrc             # Un-ignore specific files with !
!/.config             # Un-ignore directory
/.config/*            # Re-ignore contents
!/.config/fish        # Un-ignore specific subdirectory
```

This pattern allows selective versioning of dotfiles and configs while keeping
everything else out of git.

### Notes for agents

- This is a **home folder repo** — be careful with file operations
- Use the existing `.gitignore` pattern when adding new tracked files
- Shell configs are duplicated across bash/zsh/fish/pwsh — keep them in sync
- The `syncremote` function is for fork workflows
  (origin = fork, upstream = parent)
- pyenv auto-activation depends on `.python-version` files
  in project directories
- `.codex/config.toml` is committed through a git clean filter
  (`.agents/bin/codex-config-clean.py`, wired in `.gitattributes`)
  that strips Codex-written machine state (absolute-path trust entries,
  hook hashes) — the working file and the tracked blob differ by design;
  cross-machine runbook in the `/dotfiles-reference` skill
- This file (`~/AGENTS.md`) is the tool-neutral instruction core shared by
  five agent CLIs (Claude Code, Codex, Cursor, Copilot, Antigravity);
  `~/.agents/` holds the shared enforcement hooks and skills.
  Claude Code (2.1.277+) reads this file natively when the working
  directory is `~`; `~/.claude/CLAUDE.md` imports it for every other
  working directory.
  Never add a `CLAUDE.md` at the `~` root —
  it would silently disable native `AGENTS.md` loading.
  Per-tool wiring lives in `.claude/`, `.codex/`, `.cursor/`, `.copilot/`,
  `.gemini/` (Antigravity `agy` reuses the Gemini CLI directory) —
  details in the `/dotfiles-reference` skill
- For detailed reference on all tracked configs (shell, git, tmux, nvim,
  VS Code, Zed, PowerShell, dev environment), invoke the
  `/dotfiles-reference` skill.
