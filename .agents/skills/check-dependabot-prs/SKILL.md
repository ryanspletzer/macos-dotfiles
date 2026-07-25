---
name: check-dependabot-prs
description: >-
  Query all github.com/ryanspletzer repos for open Dependabot PRs and
  deterministically analyze each for mergeability (merge conflicts, CI check
  status, review requirements, behind-base). Use when asked to check,
  analyze, or triage open Dependabot PRs.
---

# Check Dependabot PRs

This skill is fully scripted, deterministic, and read-only.
The model must not query GitHub itself.
Instead, run the script below and report its output.
The script never merges anything — it only inspects and reports.

## Steps

Run the script and report the results table and summary to the user:

```bash
python3 ~/.agents/skills/check-dependabot-prs/scripts/check_dependabot_prs.py
```

## Options

The script accepts the following flags:

- `--owner` — GitHub owner/org to search.
  Defaults to `ryanspletzer`.
- `--repo OWNER/NAME` — limit results to a specific repo.
  Repeatable to include several repos.
- `--json` — emit machine-readable JSON instead of the human-readable
  report.

## Verdicts

Each pull request is assigned exactly one verdict:

- `READY` — no conflicts, checks green (or none), no outstanding review
  requirement.
- `NEEDS_APPROVAL` — mergeable and green but branch protection requires a
  review.
- `CHANGES_REQUESTED` — a reviewer requested changes.
- `CHECKS_PENDING` — CI is still running.
- `CHECKS_FAILING` — one or more checks failed (failing check names are
  listed).
- `BEHIND_BASE` — branch protection requires the branch to be up to date
  with base.
- `CONFLICTS` — merge conflicts with base.
- `DRAFT` — the PR is a draft.
- `UNKNOWN` — GitHub had not finished computing mergeability after
  retries.

## Note

This skill requires an authenticated `gh` CLI.
Verify with `gh auth status` if the script reports authentication errors.
