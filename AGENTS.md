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
