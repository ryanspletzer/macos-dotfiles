---
name: check-pinned-tools
description: >-
  Scan local repo clones (~ and ~/git) for pinned tool versions that
  Dependabot doesn't manage — UV_VERSION env vars, setup-uv version inputs,
  UV_EXCLUDE_NEWER snapshot dates, SHA-pinned GitHub Actions, and
  pre-commit hook revs — and deterministically report which pins are
  outdated against the latest upstream releases. Use when asked to check,
  audit, or find outdated pinned tools or version pins across repos.
---

# Check Pinned Tools

This skill is fully scripted, deterministic, and read-only.
The model must not resolve versions or query GitHub itself.
Instead, run the script below and report its output.
The script never edits files or drives git — it only inspects and reports.
To actually update uv pins afterwards, use the `update-uv-pins` skill.

## Steps

Run the script and report the findings and summary to the user:

```bash
python3 ~/.agents/skills/check-pinned-tools/scripts/check_pinned_tools.py
```

## What it checks

The script scans the home repo (`~`) and every git repo under `~/git`
whose `origin` remote belongs to the owner
(clones of other people's repos are skipped),
looking at `.github/workflows/*.yml`/`*.yaml`, `.pre-commit-config.yaml`,
`pyproject.toml`, and `uv.toml`, and compares each pin against the latest
upstream release resolved via `gh api`:

- `action-pin` — `uses: owner/repo@<sha-or-tag>` pins in workflows,
  including verifying that a SHA pin actually matches its
  `# vX.Y.Z` version comment.
- `uv-version` — `UV_VERSION` env vars and `version:` inputs inside
  `astral-sh/setup-uv` steps, against the latest uv release.
- `exclude-newer` — `UV_EXCLUDE_NEWER` env vars and `exclude-newer`
  settings, flagged stale once older than the threshold.
- `precommit-rev` — `rev:` pins in `.pre-commit-config.yaml`,
  against each hook repo's latest release or tag.

Action pins in repos whose `.github/dependabot.yml` covers the
`github-actions` ecosystem are still reported,
but marked `[dependabot-covered]` so the true gaps stand out.

## Options

The script accepts the following flags:

- `--git-root PATH` — root directory containing repo clones.
  Defaults to `~/git`.
- `--repo NAME` — limit to a repo by directory name
  (`home` selects the home repo). Repeatable,
  and overrides the owner filter.
- `--no-home` — skip the home repo.
- `--owner NAME` — GitHub owner whose repos are scanned
  (matched against each clone's `origin` remote).
  Defaults to `ryanspletzer`.
- `--all-repos` — scan every repo regardless of origin owner.
- `--stale-days N` — age threshold for `exclude-newer` dates.
  Defaults to 30.
- `--all` — include CURRENT pins in the human-readable report.
- `--json` — emit machine-readable JSON instead of the human-readable
  report.

## Verdicts

Each pin is assigned exactly one verdict:

- `OUTDATED` — pinned version is behind the latest upstream release.
- `SHA_MISMATCH` — a SHA pin's version comment claims the latest tag,
  but the SHA does not match that tag's commit.
- `STALE` — an `exclude-newer` date is older than the threshold.
- `UNKNOWN` — the latest version could not be resolved,
  or the pin could not be interpreted (details in the note).
- `CURRENT` — the pin matches the latest upstream release.

## Note

This skill requires an authenticated `gh` CLI.
Verify with `gh auth status` if the script reports authentication errors.
