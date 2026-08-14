---
name: update-uv-pins
description: >-
  Update pinned uv versions across GitHub Actions workflows in ~/git repos:
  the UV_VERSION env var / setup-uv `version:` input to the latest uv
  release, and the astral-sh/setup-uv action SHA pin to its latest release.
  Opens one PR per affected repo.
  Use when asked to update or bump uv pins in workflows.
---

# Update uv Pins

The entire flow is scripted and deterministic — do not edit workflow YAML,
resolve versions, or drive git yourself.
Just run the script and report its output.

## Steps

1. Run the script:

   ```sh
   python3 ~/.agents/skills/update-uv-pins/scripts/update_uv_pins.py
   ```

2. Report the result to the user:
   the per-repo pin changes it printed and the PR URLs,
   or "already up to date" if nothing needed changing.

That's it. The script handles everything:
resolving the latest uv release and the latest setup-uv release
(tag plus dereferenced commit SHA) via `gh api`,
discovering every repo under `~/git` whose workflows reference
`astral-sh/setup-uv` or `UV_VERSION`,
rewriting the pins line-by-line so comments and formatting are preserved
(`UV_VERSION: "X"` env vars,
`version: "X"` inputs inside setup-uv `with:` blocks only,
and `setup-uv@<sha> # vX` action pins),
then per changed repo: branching off the default branch,
committing with a conventional-commit message, pushing,
and opening a PR via `gh`.
Repos already at the latest versions are skipped,
as are repos whose workflow files have uncommitted changes
(reported so the user can resolve them).

Pass `--dry-run` to print the would-be changes without touching git.
