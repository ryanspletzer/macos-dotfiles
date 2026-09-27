#!/usr/bin/env python3
"""Merge every open Dependabot pull request that is READY to merge.

Reuses the deterministic triage from the sibling ``check-dependabot-prs``
skill so both skills agree on what READY means, then merges each READY PR
via the ``gh`` CLI using the first merge method the repository allows
(merge commit, then squash, then rebase). Every other verdict is skipped
and reported. Each merge is verified afterwards by re-reading the PR
state from GitHub.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CHECK_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "check-dependabot-prs"
    / "scripts"
)
sys.path.insert(0, str(CHECK_SCRIPTS_DIR))

import check_dependabot_prs as check  # noqa: E402

METHOD_PREFERENCE = ["merge", "squash", "rebase"]
REPO_METHOD_FIELDS = {
    "merge": "allow_merge_commit",
    "squash": "allow_squash_merge",
    "rebase": "allow_rebase_merge",
}


def run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a ``gh`` command and return the completed process."""
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def allowed_merge_methods(repo: str) -> list[str]:
    """Return the merge methods a repository's settings allow, in preference order."""
    result = run_gh(["api", f"repos/{repo}"])
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        sys.exit(1)
    settings = json.loads(result.stdout)
    return [
        method
        for method in METHOD_PREFERENCE
        if settings.get(REPO_METHOD_FIELDS[method], False)
    ]


def choose_method(repo: str, requested: str, cache: dict[str, list[str]]) -> str | None:
    """Pick the merge method for a repo, honouring an explicit request."""
    if repo not in cache:
        cache[repo] = allowed_merge_methods(repo)
    allowed = cache[repo]
    if requested != "auto":
        return requested if requested in allowed else None
    return allowed[0] if allowed else None


def merge_pr(url: str, method: str) -> tuple[bool, str]:
    """Merge a PR with the given method; return (ok, stderr)."""
    result = run_gh(["pr", "merge", url, f"--{method}"])
    return result.returncode == 0, result.stderr.strip()


def verify_merged(url: str) -> tuple[str, str | None]:
    """Re-read a PR and return (state, short merge commit oid)."""
    result = run_gh(["pr", "view", url, "--json", "state,mergeCommit"])
    if result.returncode != 0:
        return "UNVERIFIED", None
    data = json.loads(result.stdout)
    commit = data.get("mergeCommit") or {}
    oid = commit.get("oid")
    return data.get("state", "UNVERIFIED"), oid[:7] if oid else None


def process(
    reports: list[dict[str, Any]], requested_method: str, dry_run: bool
) -> list[dict[str, Any]]:
    """Merge READY PRs and annotate every report with an outcome."""
    method_cache: dict[str, list[str]] = {}
    outcomes: list[dict[str, Any]] = []
    for report in sorted(reports, key=lambda r: (r["repo"], r["number"])):
        outcome = dict(report)
        outcome.update({"method": None, "outcome": None, "merge_commit": None, "error": None})

        if report["verdict"] != "READY":
            outcome["outcome"] = "SKIPPED"
            outcomes.append(outcome)
            continue

        method = choose_method(report["repo"], requested_method, method_cache)
        if method is None:
            outcome["outcome"] = "FAILED"
            outcome["error"] = (
                f"no usable merge method (requested={requested_method}, "
                f"allowed={method_cache[report['repo']] or 'none'})"
            )
            outcomes.append(outcome)
            continue
        outcome["method"] = method

        if dry_run:
            outcome["outcome"] = "WOULD_MERGE"
            outcomes.append(outcome)
            continue

        ok, stderr = merge_pr(report["url"], method)
        if not ok:
            outcome["outcome"] = "FAILED"
            outcome["error"] = stderr or "gh pr merge failed"
            outcomes.append(outcome)
            continue

        state, oid = verify_merged(report["url"])
        if state == "MERGED":
            outcome["outcome"] = "MERGED"
            outcome["merge_commit"] = oid
        else:
            outcome["outcome"] = "FAILED"
            outcome["error"] = f"post-merge state is {state}, expected MERGED"
        outcomes.append(outcome)
    return outcomes


def print_human_report(outcomes: list[dict[str, Any]], owner: str, dry_run: bool) -> None:
    """Print the per-PR outcomes and a summary."""
    if not outcomes:
        print(f"No open Dependabot PRs found for {owner}.")
        return

    current_repo = None
    for outcome in outcomes:
        if outcome["repo"] != current_repo:
            if current_repo is not None:
                print()
            current_repo = outcome["repo"]
            print(current_repo)
        line = f"  #{outcome['number']}  {outcome['outcome']}"
        if outcome["method"]:
            line += f" ({outcome['method']})"
        if outcome["merge_commit"]:
            line += f" {outcome['merge_commit']}"
        line += f"  {outcome['title']}"
        print(line)
        print(f"    {outcome['url']}")
        if outcome["outcome"] == "SKIPPED":
            reason = outcome["verdict"]
            if outcome["failing_checks"]:
                reason += f": {', '.join(outcome['failing_checks'])}"
            print(f"    skipped: {reason}")
        if outcome["error"]:
            print(f"    error: {outcome['error']}")
    print()

    counts = Counter(outcome["outcome"] for outcome in outcomes)
    label = "Dry run" if dry_run else "Done"
    print(f"{label}: {len(outcomes)} open Dependabot PR(s)")
    for name in ["MERGED", "WOULD_MERGE", "FAILED", "SKIPPED"]:
        if counts[name]:
            print(f"  {name}: {counts[name]}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Merge open Dependabot PRs whose verdict is READY."
    )
    parser.add_argument(
        "--owner",
        default="ryanspletzer",
        help="GitHub owner/org to search (default: ryanspletzer).",
    )
    parser.add_argument(
        "--repo",
        action="append",
        metavar="OWNER/NAME",
        help="Limit to this repo. Repeatable.",
    )
    parser.add_argument(
        "--method",
        choices=["auto", *METHOD_PREFERENCE],
        default="auto",
        help=(
            "Merge method. 'auto' (default) picks the first the repo allows: "
            "merge, then squash, then rebase."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be merged without merging anything.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON array instead of a human-readable report.",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point: triage Dependabot PRs, merge the READY ones, report."""
    args = parse_args()

    prs = check.search_dependabot_prs(args.owner)
    if args.repo:
        allowed_repos = set(args.repo)
        prs = [pr for pr in prs if pr["repository"]["nameWithOwner"] in allowed_repos]
    check.refresh_unknown_mergeability(prs)
    reports = [check.build_report(pr) for pr in prs]

    outcomes = process(reports, args.method, args.dry_run)

    if args.json:
        print(json.dumps(outcomes, indent=2))
    else:
        print_human_report(outcomes, args.owner, args.dry_run)

    if any(outcome["outcome"] == "FAILED" for outcome in outcomes):
        sys.exit(1)


if __name__ == "__main__":
    main()
