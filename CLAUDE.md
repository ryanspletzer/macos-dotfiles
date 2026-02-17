# Home Folder Configuration

This is Ryan Spletzer's source-controlled home folder on macOS. The repository
uses an **ignore-everything-then-selectively-un-ignore** strategy via
`.gitignore`.

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

---

## What's Being Tracked

### Shell Configurations

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

### Prompt Theme

**Oh My Posh** with custom theme at `.oh-my-posh/themes/mytheme.yaml`:

- Powerline-style segments
- Shows: user, path, git status, language versions, Azure/AWS context
- Right-aligned: shell name, execution time, clock
- Color-coded git status (yellow for changes, purple for ahead/behind)

### Git Configuration

| File | Purpose |
| ---- | ------- |
| `.gitconfig` | Main config: GPG signing, push defaults, LFS, credentials |
| `.gitconfig.personal` | Personal email (conditional include for `~/`) |
| `.gitconfig.work` | Work email (conditional include for `/Users/spletzr/`) |
| `.gitattributes` | LFS patterns, line ending rules |
| `.gnupg/gpg.conf` | GPG preferences (`no-tty` for non-interactive signing) |

Key settings:

- GPG commit signing enabled (`signingKey = 787AEF0BAE232359`)
- `push.autoSetupRemote = true` (auto-track remote branches)
- Git Credential Manager for auth
- Git LFS enabled

### Claude Code Configuration

`.claude/settings.json`:

- **Plugins enabled**: commit-commands, github, pyright-lsp, typescript-lsp,
  gopls-lsp, pr-review-toolkit
- **Status line**: oh-my-posh integration (`oh-my-posh claude`)
- **Audio notifications**: Morse.aiff on stop, Ping.aiff on notification
- **Hooks**:
  - `approve-variants.py` - Auto-approves safe Bash command variants
    (handles wrappers like `timeout`, env vars, `.venv/bin/`)
  - `check-uv-pytest.py` - Enforces `uv run pytest` instead of bare `pytest`

### tmux Configuration

`.tmux.conf`:

- **Prefix**: `Ctrl+a` (rebound from `Ctrl+b`)
- **Plugins** (via TPM): `tmux.nvim` (cross-pane nav/resize),
  `tmux-resurrect`, `tmux-continuum`, `tmux-yank`
- Seamless `Ctrl+h/j/k/l` navigation with Neovim via `tmux.nvim`
- Pane resize with `Ctrl+Shift+Arrow` (also crosses Neovim boundary)
- `prefix + C` for 60/40 Claude Code layout split
- 50k scrollback, focus events, clipboard integration, auto-rename

### Neovim/LazyVim Configuration

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
  `claudecode.lua` (Claude Code integration)
- **Autocmds**: buffer refresh on focus/enter, file change notification

### VS Code Settings

`Library/Application Support/Code/User/settings.json`:

- Font: CaskaydiaCove Nerd Font
- Format on save/paste/type enabled
- GPG commit signing
- Language-specific tab sizes (2 spaces for most, 4 for Python)
- AWS CloudFormation YAML schema support
- Rulers at 80, 100, 114, 116, 120

### PowerShell Profile Module

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

---

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
- **pipx** for isolated Python CLI tools (`~/.local/bin`)

### Zsh Plugins (via Homebrew)

- zsh-syntax-highlighting
- zsh-autocomplete
- zsh-autosuggestions

---

## Dotfiles Audit (Feb 2026)

Review of common config files for source control:

### Added

- `.gnupg/gpg.conf` - `no-tty` setting for non-interactive commit signing

### Skipped (reviewed but not useful)

| File | Reason |
| ---- | ------ |
| `~/.docker/config.json` | Default Docker Desktop config, no customizations |
| `~/.azure/` | Only Azure PowerShell state files, no CLI config |

### Don't Exist (nothing to track)

`~/.ssh/config`, `~/.aws/config`, `~/.npmrc`, `~/.cargo/config.toml`,
`~/.pypirc`, `~/.vimrc`, `~/.editorconfig`, `~/.prettierrc`,
`~/.eslintrc`, `~/.Brewfile`, VS Code `keybindings.json`, VS Code `snippets/`

### Future Candidates

Track these when they exist with meaningful customizations:

- `~/.ssh/config` - when SSH hosts are configured
- `~/.aws/config` - when AWS CLI profiles are set up

---

## Notes for Claude

- This is a **home folder repo** - be careful with file operations
- Use the existing `.gitignore` pattern when adding new tracked files
- Shell configs are duplicated across bash/zsh/fish/pwsh - keep them in sync
- The `syncremote` function is for fork workflows (origin = fork, upstream = parent)
- pyenv auto-activation depends on `.python-version` files in project directories
