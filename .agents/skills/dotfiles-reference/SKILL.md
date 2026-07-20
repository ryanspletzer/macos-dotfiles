---
name: dotfiles-reference
description: >-
  Detailed reference for all tracked configurations in this dotfiles repo
  (shell, git, tmux, nvim, micro, helix, VS Code, Zed, PowerShell,
  dev environment,
  Claude Code plugins). Use when editing specific config files.
disable-model-invocation: true
---

# Dotfiles Configuration Reference

## Shell Configurations

| Shell | Files |
| ----- | ----- |
| **Bash** | `.bash_profile`, `.bashrc` |
| **Zsh** | `.zprofile`, `.zshenv`, `.zshrc` |
| **Fish** | `.config/fish/config.fish`, `conf.d/rustup.fish`, etc. |
| **PowerShell** | `.config/powershell/Microsoft.PowerShell_profile.ps1`, etc. |

All shells share consistent aliases and functions:

- `cls` - clear screen
- `openremote` - open git remote URL in browser
- `syncremote` - sync fork from upstream (handles main/master, optional branch deletion)
- `finder` - open Finder at path
- `textedit` - open file in TextEdit
- `caf` - run `caffeinate -disu` (optional `-s` for screensaver)
- `code` - launch VS Code with selective extensions
  (reads `.vscode/extensions.json`, disables non-recommended extensions;
  warns if a recommended extension is manually disabled in workspace storage)

## Prompt Theme

**Oh My Posh** with custom theme at `.oh-my-posh/themes/mytheme.yaml`:

- Powerline-style segments
- Shows: user, path, git status, language versions, Azure/AWS context
- Right-aligned: shell name, execution time, clock
- Color-coded git status (yellow for changes, purple for ahead/behind)

## Git Configuration

| File | Purpose |
| ---- | ------- |
| `.gitconfig` | Main config: GPG signing, push defaults, LFS, credential helper; includes `~/.gitconfig.local` |
| `.gitconfig.local.example` | Template for the gitignored per-machine `~/.gitconfig.local` (identity + host creds) |
| `.gitattributes` | LFS patterns, line ending rules, `codex-config` clean filter |
| `.gnupg/gpg.conf` | GPG preferences (`no-tty` for non-interactive signing) |

Key settings:

- GPG commit signing enabled (`signingKey = 787AEF0BAE232359`)
- `push.autoSetupRemote = true` (auto-track remote branches)
- Git Credential Manager for auth
- Git LFS enabled
- `.codex/config.toml` is committed through the `codex-config` clean filter —
  see the runbook below

### Codex config.toml across machines (codex-config clean filter)

`~/.codex/config.toml` mixes portable user settings
(`model`, `[tui] status_line`) with machine state Codex writes itself
(absolute-path `[projects]` trust entries, `[hooks.state]` hashes,
notice/nux counters), and Codex offers no way to separate them.
The file is therefore committed through the `codex-config` git clean filter
(`.agents/bin/codex-config-clean.py`, wired in `.gitattributes`),
which strips the machine-state sections at commit time:
the tracked blob stays portable while the live file keeps local state.
The working file and the tracked blob differ **by design**.

**New machine setup** — nothing Codex-specific to do.
The filter definition (`[filter "codex-config"]` in the tracked `.gitconfig`),
the `.gitattributes` wiring, and the script all arrive with the dotfiles,
and dev-machine-setup re-asserts the filter as `--global` config
(`examples/macOS_vars.yaml`, `custom_commands_user`).
Verify with:

```sh
git config --get filter.codex-config.clean
# → ~/.agents/bin/codex-config-clean.py
```

Codex then builds up that machine's own trust entries locally as you use it.

**Day-to-day** — nothing.
Codex churns its state in the live file;
the filter strips it at commit time;
`git status` stays clean.

**Changing a portable setting (statusline items, model)** —
edit the live `~/.codex/config.toml` and commit via the normal PR flow;
only the portable parts land.
When *another* machine pulls that change,
git overwrites its working `config.toml` with the new portable blob
(the filter has no smudge step to merge local state back),
so that machine's Codex re-prompts once for folder trust,
and hooks need a one-time re-trust via `/hooks` in the Codex TUI.
To skip the re-prompts,
back up `~/.codex/config.toml` before pulling and
paste the `[projects]`/`[hooks.state]` sections back afterward.

**Failure mode** — if a machine has the filter unconfigured,
commits from it silently include that machine's state sections.
Nothing breaks;
`/Users/...` paths reappearing in a PR diff is the tell.
Run the verify command above on that machine.

## AI Agent CLI Configuration

Four agent CLIs share one set of conventions and enforcement assets:
Claude Code, OpenAI Codex CLI, Cursor CLI, and GitHub Copilot CLI.

### Shared assets

- `AGENTS.md` (home root) - tool-neutral instruction core
  (markdown, git workflow, Python packaging)
- `.agents/hooks/` - shared PreToolUse enforcement scripts
  (Claude/Codex hook schema; identical payloads):
  - `_utils.py` - Shared utility module with `strip_quoted_content()`;
    strips heredocs, quoted strings, and comments so enforcement hooks
    only match actual command tokens (not keywords in commit messages,
    echo strings, etc.)
  - `approve-variants.py` - Auto-approves safe Bash command variants
    (handles wrappers like `timeout`, env vars, `.venv/bin/`)
  - `check-uv-pytest.py` - Enforces `uv run pytest` instead of bare `pytest`
  - `check-uv-venv.py` - Enforces `uv venv` instead of `python -m venv`
    or `virtualenv`
  - `check-pip-install.py` - Blocks bare `pip install`;
    use `uv pip install`, `uv add`, or `uv tool install` instead
  - `check-pipx.py` - Blocks `pipx`;
    use `uvx` (for `pipx run`) or `uv tool install` (for `pipx install`)
  - `filter-test-output.py` - Rewrites known test-runner commands to log
    full output and surface only failures + summary
  - `adapters/cursor-shell-gate.py`, `adapters/cursor-filter-tests.py` -
    bridge the shared scripts to Cursor's hook dialect
  - `adapters/cursor-session-context.py` - injects `~/AGENTS.md` into
    Cursor sessions as context (sessionStart hook)
- `.agents/skills/dotfiles-reference/` - this skill; symlinked into
  `.claude/skills/`, `.codex/skills/`, `.cursor/skills/`
  (Copilot reads `~/.agents/skills/` natively)

### Per-tool wiring

| Tool | Instructions | Hooks | Sounds |
| ---- | ------------ | ----- | ------ |
| Claude Code | `.claude/CLAUDE.md` imports `@~/AGENTS.md` | `settings.json` → `.agents/hooks/` | Morse / Ping |
| Codex CLI | `.codex/AGENTS.md` → `~/AGENTS.md` | `.codex/hooks.json` → `.agents/hooks/` | Glass / Tink |
| Cursor CLI | sessionStart hook injects `~/AGENTS.md` (see note) | `.cursor/hooks.json` → adapters | Submarine / Pop |
| Copilot CLI | `copilot-instructions.md` → `~/AGENTS.md` + `instructions/` | none (instruction-only) | n/a |

Cursor note: disk-based `~/.cursor/rules/` loading is bugged
(confirmed by Cursor staff, 2026-04) and account User Rules are not
source-controllable, so `adapters/cursor-session-context.py` injects
`~/AGENTS.md` as session context via the sessionStart hook instead —
fully git-tracked and identical across accounts/machines.
If Cursor fixes disk-based user rules, that can replace the hook.
Sounds are stop / attention (Cursor's attention sound plays on deny).

Cursor's `.cursor/.gitignore` is Cursor-managed;
user additions live below the managed block
(un-ignore `hooks.json`, re-ignore session state).
Codex requires one-time interactive hook trust (`/hooks` in the TUI)
after any hook definition change.

### Claude Code specifics

`.claude/settings.json`:

- **Plugins enabled**: commit-commands, markdown-linter-fixer,
  security-guidance, code-review
- **Status line**: oh-my-posh integration (`oh-my-posh claude`)
- **Audio notifications**: Morse.aiff on stop, Ping.aiff on notification
- **Topic rules**: `.claude/rules/` (markdown, git workflow,
  VS Code extensions; markdown rule is path-scoped to `**/*.md`)

### Plugin Portability

Marketplaces and plugins are tracked in a portable manifest for cross-machine
setup.
The manifest strips machine-specific paths from Claude's internal JSON files,
keeping only the identifiers needed to restore the configuration.

| File | Purpose |
| ---- | ------- |
| `.claude/plugin-manifest.json` | Portable manifest (git-tracked) |
| `.claude/scripts/claude-plugins-export.sh` | Export config to manifest |
| `.claude/scripts/claude-plugins-restore.sh` | Restore config from manifest |

**Workflow**:

1. After adding/removing marketplaces or plugins, run the export script
2. Commit the updated manifest
3. On a new machine, pull dotfiles and run the restore script

Both scripts require `jq`.
The restore script is idempotent — it skips already-installed items.
Marketplace entries can be GitHub repo shorthand (`owner/name`) or full git
URLs (`https://...`).

## tmux Configuration

`.tmux.conf`:

- **Prefix**: `Ctrl+a` (rebound from `Ctrl+b`)
- **Plugins** (via TPM): `tmux.nvim` (cross-pane nav/resize),
  `tmux-resurrect`, `tmux-continuum`, `tmux-yank`
- Seamless `Ctrl+h/j/k/l` navigation with Neovim via `tmux.nvim`
- Pane resize with `Ctrl+Shift+Arrow` (also crosses Neovim boundary)
- `prefix + C` for 60/40 Claude Code layout split
- 50k scrollback, focus events, clipboard integration, auto-rename

## Neovim/LazyVim Configuration

`.config/nvim/` (LazyVim starter with customizations):

- **Tracked**: `init.lua`, `lua/config/*.lua`, `lua/plugins/*.lua`, `stylua.toml`
- **Ignored**: `lazy-lock.json`, `.neoconf.json`, `lazyvim.json`, `LICENSE`,
  `README.md`, `.gitignore` (auto-generated or starter boilerplate)
- **Extras enabled**: `lang.typescript`, `lang.json`, `lang.markdown`,
  `lang.go`, `lang.python`, `lang.dotnet`, `lang.yaml`, `lang.helm`,
  `lang.docker`, `formatting.prettier`, `linting.eslint`,
  `ui.mini-animate`, `coding.mini-surround`, `coding.yanky`,
  `editor.mini-files`, `editor.mini-move`, `editor.inc-rename`,
  `ai.claudecode`
- **Custom plugins**: `tmux.lua` (tmux.nvim), `snacks.lua` (picker nav fix),
  `claudecode.lua` (Claude Code integration),
  `powershell.lua` (PSES LSP + treesitter)
- **Autocmds**: buffer refresh on focus/enter, file change notification

## Micro Configuration

`.config/micro/` (lightweight terminal editor, VS Code-style keybindings):

- **Tracked**: `settings.json`, `bindings.json`, `README.md`,
  `plug/fzfopen/` (local Ctrl+P fuzzy-open plugin, requires `fzf`)
- **Ignored**: `buffers/`, `backups/`, third-party plugins under `plug/`
- **Third-party plugin** (reinstall on new machines):
  `micro -plugin install filemanager` (Ctrl+B file tree)
- Key overrides: Ctrl+P fuzzy open, Ctrl+B file tree, Ctrl+D multi-cursor,
  Ctrl+/ comment, Ctrl+G go-to-line, F1 help
- Full cheat sheet and rationale in `.config/micro/README.md`

## Helix Configuration

`.config/helix/` (modal terminal editor, Kakoune-style;
VS Code-flavored conveniences on top):

- **Tracked**: `config.toml`, `languages.toml`, `README.md`
- **Ignored**: everything else under `.config/helix/`
  (state lives in `~/.local/state/helix` and `~/.cache/helix` anyway)
- No plugins — pickers, file explorer, LSP, and tree-sitter are built in
- Key overrides: Ctrl+S save, Ctrl+P file picker, Ctrl+B file explorer,
  Ctrl+/ comment; `dark_plus` theme (VS Code Dark+ port);
  per-filetype 2-space indents in `languages.toml` mirror VS Code
- Full cheat sheet and VS Code-to-Helix mapping in `.config/helix/README.md`

## VS Code Settings

`Library/Application Support/Code/User/settings.json`:

- Font: CaskaydiaCove Nerd Font
- Format on save/paste/type enabled
- GPG commit signing
- Language-specific tab sizes (2 spaces for most, 4 for Python)
- AWS CloudFormation YAML schema support
- Rulers at 80, 100, 114, 116, 120

`.vscode/extensions.json`:

- Recommendations for the 12 extensions relevant to this dotfiles repo
  (PowerShell, YAML, Markdown, Prettier, EditorConfig, spell checker,
  GitLens, Git Graph, gitignore syntax, error lens, indent rainbow,
  Claude Code)
- The shell-level `code` function reads this file, disables
  non-recommended extensions automatically, and warns if a recommended
  extension has been manually disabled in VS Code workspace storage

## Zed Settings

Global settings at `.config/zed/settings.json`,
project-level settings at `.zed/settings.json`:

- **Global**: theme, fonts, editor behavior, language overrides
  (mirrors VS Code settings where possible)
- **Project-level**: `project_panel.hide_gitignore` and comprehensive
  `file_scan_exclusions` covering non-dot directories, untracked dotfile
  directories, and untracked dotfiles — uses root-relative paths
  (not recursive `**/*` globs) since exclusions apply to the home folder

## PowerShell Profile Module

`.config/powershell/Modules/Profile/1.0.0/Profile.psm1`:

Custom functions beyond shell aliases:

- `Get-TypeAccelerators` - List PowerShell type accelerators
- `Get-LocalCertificate` - Query local certificate store
- `Use-Pyenv` / `Enter-PyenvDir` / `Exit-PyenvDir` - pyenv integration
- `Get-ParentItem` / `Find-ParentFilePath` - Path traversal utilities
- `Get-ParallelThrottle` - Calculate optimal parallelism
- `Get-MgAccessTokenDelegated` - Microsoft Graph token acquisition
- `Connect-MgGraphWithAccessToken` - Graph SDK connection
- `Get-MgUserDirectReportTransitive` - Recursive org chart traversal

## Development Environment

### Language/Runtime Managers

| Tool | Managed By | Notes |
| ---- | ---------- | ----- |
| **Ruby** | chruby | Default: ruby-3.4.1 |
| **Python** | pyenv + pyenv-virtualenv | Auto-activates via direnv |
| **Node.js** | nvm | Via Homebrew |
| **Rust** | rustup | Cargo env sourced in shells |

### Key Tools

- **Homebrew** at `/opt/homebrew`
- **direnv** for per-directory env
- **fzf** for fuzzy finding
- **uv** for Python package/tool management (`uvx` for one-off runs,
  `uv tool install` for persistent CLI tools)

### Zsh Plugins (via Homebrew)

- zsh-syntax-highlighting
- zsh-autocomplete
- zsh-autosuggestions
