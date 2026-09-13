---
name: check-stale-locks
description: >-
  Scan local repo clones (~ and ~/git) for uv.lock files and report which
  locked packages would move on `uv lock --upgrade`, separating
  transitive dependencies (which Dependabot version updates never touch)
  from direct dependencies (which Dependabot handles when the repo has a
  matching dependabot.yml uv entry). uv only for now. Use when asked to
  check, audit, or find stale/outdated uv lockfiles across repos.
---

# Check Stale Locks

This skill is fully scripted, deterministic, and read-only.
The model must not run `uv lock --upgrade` for real or hand-edit any lock.
Instead, run the script below and report its output.
The script never writes files or mutates a lock —
it only runs `uv lock --upgrade --dry-run` and parses uv's plan.
No refresh skill exists yet;
refreshing a lock afterwards is a manual `uv lock --upgrade` plus a PR.

## Steps

Run the script and report the findings and summary to the user:

```bash
python3 ~/.agents/skills/check-stale-locks/scripts/check_stale_locks.py
```

## What it checks

The script scans the home repo (`~`) and every git repo under `~/git`
whose `origin` remote belongs to the owner
(clones of other people's repos are skipped),
finds every `uv.lock` file in each repo,
and runs `uv lock --upgrade --dry-run` in that lockfile's directory.
It parses uv's plan (`Update`, `Add`, `Remove` lines) to see which
packages would move, then classifies each one against the project's own
`pyproject.toml`:

- `direct` — the package is a declared dependency
  (`[project.dependencies]`, `[project.optional-dependencies]`,
  `[dependency-groups]`, `[tool.uv].dev-dependencies`,
  or a `[tool.uv.workspace]` member's own dependencies).
- `transitive` — everything else a refresh would move.
  Dependabot version updates never touch these.
- `unknown` — the project's `pyproject.toml` is missing or unparseable,
  so direct/transitive can't be determined.

A project's direct-dependency movement is still reported even when
Dependabot covers it
(the repo's `.github/dependabot.yml` has a `uv`/`pip` entry whose
`directory`/`directories` matches the project),
but marked `[dependabot-covered]` so the real gap — transitive drift —
stands out.

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
- `--transitive-only` — omit direct-dependency entries from the
  human-readable report (JSON always includes everything).
- `--all` — include CURRENT projects in the human-readable report.
- `--timeout N` — per-project `uv` timeout in seconds. Defaults to 120.
- `--json` — emit one JSON object per project instead of a
  human-readable report.

## Verdicts

Each project is assigned exactly one verdict:

- `STALE` — a refresh would move at least one transitive
  (or unknown-kind) package.
- `DIRECT_ONLY` — a refresh would move only direct dependencies.
- `UNKNOWN` — `uv lock --upgrade --dry-run` failed or timed out
  (details in the note).
- `CURRENT` — nothing would move.

## Note

This script needs `uv` on `PATH` and network access to the package index
to compute what a refresh would resolve to.
It changes nothing: `uv lock --upgrade --dry-run` never writes a lock.
To actually refresh a lock,
run `uv lock --upgrade` in the project directory and open a PR —
no refresh skill exists yet.
