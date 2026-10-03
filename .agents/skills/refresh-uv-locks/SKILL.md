---
name: refresh-uv-locks
description: >-
  Refresh stale uv.lock files across local repos with `uv lock --upgrade`
  and open one PR per affected repo listing every moved package.
  Use when asked to refresh, upgrade, or regenerate uv lockfiles.
---

# Refresh uv Locks

The entire flow is scripted and deterministic.
Do not run `uv lock --upgrade`, hand-edit any lock, or drive git yourself.
Just run the script and report its output.

The script reuses the discovery and classification from the sibling
`check-stale-locks` skill,
so a project is refreshed only when that skill would report it as
`STALE` or `DIRECT_ONLY`.
`CURRENT` and `UNKNOWN` projects are left alone.

## Steps

1. Run the script:

   ```sh
   python3 ~/.agents/skills/refresh-uv-locks/scripts/refresh_uv_locks.py
   ```

2. Report the result to the user:
   the per-repo projects it refreshed, the PR URLs,
   or "all uv.lock files are current" if nothing needed changing.

3. If any project or repo reports `FAILED`, relay the note verbatim.
   Do not retry by hand.

That's it. The script handles everything:
checking up front that commit signing works when `commit.gpgsign` is on
(it signs a throwaway message so the pinentry or hardware-token prompt
appears once, before any lock is touched),
discovering every `uv.lock` in the home repo (`~`, reported as `home`)
and every repo under `~/git` whose `origin` belongs to the owner,
running `uv lock --upgrade --dry-run` to see what would move,
then per repo with movement:
branching off the default branch,
running `uv lock --upgrade` for real in each stale project directory,
staging only the regenerated `uv.lock` files,
committing with a conventional-commit message whose body lists each
moved package (split into direct and transitive),
pushing,
and opening a PR via `gh` with the same body.
Repos whose lockfiles have uncommitted changes are skipped and reported.
The script never edits `pyproject.toml` and never merges anything.

## Options

- `--dry-run` — print the would-be refreshes per repo/project;
  touch nothing (no branch, no lock write, no PR).
- `--git-root PATH` — root directory containing repo clones.
  Defaults to `~/git`.
- `--repo NAME` — limit to a repo by directory name
  (`home` selects the home repo). Repeatable,
  and overrides the owner filter.
- `--no-home` — skip the home repo.
- `--owner NAME` — GitHub owner whose repos are acted on.
  Defaults to `ryanspletzer`.
- `--all-repos` — act on every repo regardless of origin owner.
- `--stale-only` — refresh only `STALE` projects (transitive drift);
  skip `DIRECT_ONLY` projects, which Dependabot already handles
  when it covers them.
- `--timeout N` — per-project `uv` timeout in seconds. Defaults to 120.
- `--json` — emit one JSON object per repo instead of the human-readable
  report.

## Outcomes

Each repo with movement is assigned exactly one outcome:

- `REFRESHED` — at least one lock was regenerated and a PR was opened
  (PR URL shown).
- `WOULD_REFRESH` — dry run; the repo has stale projects and would get a
  PR.
- `SKIPPED` — nothing to refresh after planning, lockfiles had
  uncommitted changes, or no lock actually changed against the base
  branch (reason shown).
- `FAILED` — `uv lock --upgrade` failed in a project, or the commit,
  push, or `gh pr create` step failed (note shown).
  If the commit itself failed, the regenerated locks are discarded and
  the empty branch removed; a pushed branch is left in place for
  inspection.

The script exits non-zero if any repo is `FAILED`.

## Note

If commits are GPG-signed, be ready to answer the pinentry prompt
(or touch the hardware token) when the script starts;
a cancelled prompt aborts the run before anything is changed.

This skill requires `uv` on `PATH`, network access to the package index,
and an authenticated `gh` CLI with permission to push and open PRs.
Verify with `gh auth status` if the script reports authentication errors.
Merging the resulting PRs is a separate step once their checks are green.
