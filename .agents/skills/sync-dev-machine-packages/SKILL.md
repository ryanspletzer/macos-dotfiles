---
name: sync-dev-machine-packages
description: >-
  Pick up newly installed Homebrew packages, bun/dotnet/uv global tools,
  and PowerShell modules, add them to examples/macOS_vars.yaml in
  ~/git/dev-machine-setup, and open a PR on a new branch.
  Use when asked to sync installed packages into dev-machine-setup.
---

# Sync Dev Machine Packages

The entire flow is scripted and deterministic — do not enumerate packages,
edit the YAML, or drive git yourself.
Just run the script and report its output.

## Steps

1. Run the script:

   ```sh
   python3 ~/.agents/skills/sync-dev-machine-packages/scripts/sync_packages.py
   ```

2. Report the result to the user:
   the per-section additions it printed and the PR URL,
   or "already up to date" if there was nothing to add.

That's it. The script handles everything:
collecting installed packages
(Homebrew taps/casks/formulae via `brew` —
leaf formulae only, never transitive dependencies of other formulae,
PowerShell modules via `Get-PSResource`,
`uv tool list`, `bun pm ls -g`, `dotnet tool list --global`),
diffing against `examples/macOS_vars.yaml`,
inserting missing entries alphabetically while preserving comments
(commented-out entries like `# - parallels` count as deliberate exclusions
and are never re-added),
branching off `origin/main`,
committing with a conventional-commit message,
pushing,
and opening the PR with `gh`.
It is additions-only and never removes entries.

## Options

- `--dry-run` — print what would be added without touching anything.
  Use this if the user only wants to see what's out of sync.
- `--repo PATH` — override the clone location
  (default `~/git/dev-machine-setup`).

## Failure notes

- "uncommitted changes" error: `examples/macOS_vars.yaml` is dirty in the
  clone; ask the user how to resolve rather than stashing yourself.
- `gh` auth errors: have the user run `! gh auth login`.
- Sections whose collector tool is missing (e.g. no `dotnet` on PATH)
  are skipped and reported, not treated as errors.
