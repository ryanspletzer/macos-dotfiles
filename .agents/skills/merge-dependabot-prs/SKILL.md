---
name: merge-dependabot-prs
description: >-
  Merge every open Dependabot PR across github.com/ryanspletzer repos whose
  deterministic verdict is READY, using the merge method each repo allows,
  and verify each merge. Use when asked to merge ready or green Dependabot
  PRs.
---

# Merge Dependabot PRs

This skill is fully scripted and deterministic.
The model must not query GitHub or run `gh pr merge` itself.
Instead, run the script below and report its output.

The script reuses the verdict logic from `check-dependabot-prs`,
so a PR is merged only when that skill would report it as `READY`.
Every other verdict is skipped and listed with its reason.

## Steps

1. Run the script and report the per-PR outcomes and summary:

   ```bash
   python3 ~/.agents/skills/merge-dependabot-prs/scripts/merge_dependabot_prs.py
   ```

2. If any PR reports `FAILED`, relay the error text verbatim.
   Do not retry the merge by hand.

## Merge method

By default the script asks GitHub which merge methods each repository
allows and uses the first of: merge commit, squash, rebase.
Repos gated by a `protect-main` ruleset only allow merge commits,
so this keeps their linear-history-free policy intact automatically.

## Options

- `--owner` — GitHub owner/org to search.
  Defaults to `ryanspletzer`.
- `--repo OWNER/NAME` — limit to a specific repo.
  Repeatable.
- `--method {auto,merge,squash,rebase}` — force a merge method.
  A forced method the repo does not allow is reported as `FAILED`.
- `--dry-run` — report what would be merged without merging anything.
- `--json` — emit machine-readable JSON instead of the human-readable
  report.

## Outcomes

Each pull request is assigned exactly one outcome:

- `MERGED` — merged and verified as `MERGED` on GitHub
  (short merge commit SHA shown).
- `WOULD_MERGE` — dry run; the PR is `READY` and would be merged.
- `SKIPPED` — verdict was not `READY`; the verdict is shown as the reason.
- `FAILED` — `gh pr merge` failed, no allowed merge method was found,
  or post-merge verification did not return `MERGED`.

The script exits non-zero if any PR is `FAILED`.

## Note

This skill requires an authenticated `gh` CLI with permission to merge.
Verify with `gh auth status` if the script reports authentication errors.
