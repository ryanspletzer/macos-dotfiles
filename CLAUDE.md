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

**Oh My Posh** with custom theme at `.oh-my-posh/themes/mytheme.json`:

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

## Candidates for Future Source Control

Consider tracking these if not already covered:

### High Value

- `~/.ssh/config` - SSH host configurations (not keys!)
- `~/.aws/config` - AWS CLI profiles (not credentials!)
- `~/.azure/` - Azure CLI config
- `~/.docker/config.json` - Docker settings (sanitize auth)
- `~/.gnupg/gpg.conf` - GPG preferences
- `~/.npmrc` - npm configuration (without tokens)
- `~/.cargo/config.toml` - Cargo/Rust settings
- `~/.pypirc` - PyPI configuration (without passwords)

### Editor/Tool Configs

- `~/.vimrc` or `~/.config/nvim/` - if using Vim/Neovim
- `~/.tmux.conf` - if using tmux
- `~/.editorconfig` - cross-editor formatting
- `~/.prettierrc` - Prettier defaults
- `~/.eslintrc` - ESLint defaults

### macOS Specific

- `~/Library/Application Support/Code/User/keybindings.json` - VS Code keybindings
- `~/Library/Application Support/Code/User/snippets/` - VS Code snippets
- `~/.Brewfile` - Homebrew bundle manifest

---

## Notes for Claude

- This is a **home folder repo** - be careful with file operations
- Use the existing `.gitignore` pattern when adding new tracked files
- Shell configs are duplicated across bash/zsh/fish/pwsh - keep them in sync
- The `syncremote` function is for fork workflows (origin = fork, upstream = parent)
- pyenv auto-activation depends on `.python-version` files in project directories
