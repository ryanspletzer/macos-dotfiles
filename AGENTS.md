# Home folder repository (macos-dotfiles)

This file describes the home folder (`~`) as a repository.
Apply it only when the working directory is `~` itself.
The tool-neutral global instruction core lives in `~/.agents/AGENTS.md`;
every agent CLI loads that file separately, so nothing global belongs here.

`~` is Ryan Spletzer's source-controlled home folder on macOS.
The repository uses an **ignore-everything-then-selectively-un-ignore**
strategy via `.gitignore`.

## Gitignore strategy

```text
/*                    # Ignore everything by default
!/.bashrc             # Un-ignore specific files with !
!/.config             # Un-ignore directory
/.config/*            # Re-ignore contents
!/.config/fish        # Un-ignore specific subdirectory
```

This pattern allows selective versioning of dotfiles and configs while keeping
everything else out of git.

## Notes for agents

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
- Instruction files: `~/.agents/AGENTS.md` is the global core shared by
  five agent CLIs (Claude Code, Codex, Cursor, Copilot, Antigravity);
  `~/.agents/` also holds the shared enforcement hooks and skills.
  Claude Code (2.1.277+) reads this file natively when the working
  directory is `~`, and `~/.claude/CLAUDE.md` imports the global core.
  Never add a `CLAUDE.md` at the `~` root or in `~/git` —
  it would silently disable native `AGENTS.md` loading.
  Per-tool wiring lives in `.claude/`, `.codex/`, `.cursor/`, `.copilot/`,
  `.gemini/` (Antigravity `agy` reuses the Gemini CLI directory) —
  details in the `/dotfiles-reference` skill
- For detailed reference on all tracked configs (shell, git, tmux, nvim,
  VS Code, Zed, PowerShell, dev environment), invoke the
  `/dotfiles-reference` skill.
