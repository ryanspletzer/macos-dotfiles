#!/usr/bin/env python3
"""Deterministically triage open Dependabot pull requests for mergeability.

Queries the GitHub GraphQL API (via the `gh` CLI) for every open Dependabot
PR across an owner's repositories, classifies each PR's mergeability using a
pure, precedence-ordered rule set, and prints a human-readable or JSON
report. This script is read-only: it never merges, approves, or otherwise
mutates anything on GitHub.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from typing import Any

SEARCH_QUERY = """
query($searchQuery: String!, $first: Int!, $after: String) {
  search(query: $searchQuery, type: ISSUE, first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        url
        isDraft
        createdAt
        headRefName
        baseRefName
        repository {
          nameWithOwner
        }
        mergeable
        mergeStateStatus
        reviewDecision
        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                state
                contexts(first: 100) {
                  nodes {
                    __typename
                    ... on CheckRun {
                      name
                      conclusion
                    }
                    ... on StatusContext {
                      context
                      state
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

PR_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number
      title
      url
      isDraft
      createdAt
      headRefName
      baseRefName
      repository {
        nameWithOwner
      }
      mergeable
      mergeStateStatus
      reviewDecision
      commits(last: 1) {
        nodes {
          commit {
            statusCheckRollup {
              state
              contexts(first: 100) {
                nodes {
                  __typename
                  ... on CheckRun {
                    name
                    conclusion
                  }
                  ... on StatusContext {
                    context
                    state
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

FAILING_CHECK_RUN_CONCLUSIONS = {
    "FAILURE",
    "TIMED_OUT",
    "CANCELLED",
    "ACTION_REQUIRED",
    "STARTUP_FAILURE",
}
FAILING_STATUS_CONTEXT_STATES = {"FAILURE", "ERROR"}
FAILING_ROLLUP_STATES = {"FAILURE", "ERROR"}
PENDING_ROLLUP_STATES = {"PENDING", "EXPECTED"}

# Verdicts in first-match-wins precedence order.
VERDICT_PRECEDENCE = [
    "DRAFT",
    "CONFLICTS",
    "CHECKS_FAILING",
    "CHECKS_PENDING",
    "CHANGES_REQUESTED",
    "NEEDS_APPROVAL",
    "BEHIND_BASE",
    "UNKNOWN",
    "READY",
]

MAX_UNKNOWN_RETRY_ROUNDS = 3
UNKNOWN_RETRY_DELAY_SECONDS = 3


def run_gh_graphql(extra_args: list[str]) -> dict[str, Any]:
    """Run `gh api graphql` with the given extra args and return parsed JSON."""
    command = ["gh", "api", "graphql", *extra_args]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        sys.exit(1)
    return json.loads(result.stdout)


def search_dependabot_prs(owner: str) -> list[dict[str, Any]]:
    """Search GitHub for every open Dependabot PR across an owner's repos."""
    search_query = (
        f"is:pr is:open author:app/dependabot user:{owner} archived:false"
    )
    nodes: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        extra_args = [
            "-f",
            f"query={SEARCH_QUERY}",
            "-f",
            f"searchQuery={search_query}",
            "-F",
            "first=100",
        ]
        if after is not None:
            extra_args += ["-f", f"after={after}"]
        data = run_gh_graphql(extra_args)
        search = data["data"]["search"]
        nodes.extend(search["nodes"])
        page_info = search["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]
    return nodes


def fetch_pr(owner: str, name: str, number: int) -> dict[str, Any] | None:
    """Re-fetch a single pull request by repository owner, name, and number."""
    extra_args = [
        "-f",
        f"query={PR_QUERY}",
        "-f",
        f"owner={owner}",
        "-f",
        f"name={name}",
        "-F",
        f"number={number}",
    ]
    data = run_gh_graphql(extra_args)
    repository = data["data"]["repository"]
    if repository is None:
        return None
    return repository["pullRequest"]


def refresh_unknown_mergeability(prs: list[dict[str, Any]]) -> None:
    """Retry PRs stuck at UNKNOWN mergeability in place, up to a few rounds."""
    for _round in range(MAX_UNKNOWN_RETRY_ROUNDS):
        unknown = [pr for pr in prs if pr["mergeable"] == "UNKNOWN"]
        if not unknown:
            return
        time.sleep(UNKNOWN_RETRY_DELAY_SECONDS)
        for pr in unknown:
            owner, name = pr["repository"]["nameWithOwner"].split("/", 1)
            refreshed = fetch_pr(owner, name, pr["number"])
            if refreshed is not None:
                pr.update(refreshed)


def _status_check_rollup(pr: dict[str, Any]) -> dict[str, Any] | None:
    """Return the status-check rollup for a PR's most recent commit, if any."""
    commit_nodes = pr["commits"]["nodes"]
    if not commit_nodes:
        return None
    return commit_nodes[0]["commit"]["statusCheckRollup"]


def rollup_state(pr: dict[str, Any]) -> str | None:
    """Return the overall status-check rollup state for a PR, if any."""
    rollup = _status_check_rollup(pr)
    if rollup is None:
        return None
    return rollup["state"]


def failing_checks(pr: dict[str, Any]) -> list[str]:
    """Return the names of failing checks/statuses on a PR's latest commit."""
    rollup = _status_check_rollup(pr)
    if rollup is None:
        return []
    names: list[str] = []
    for context in rollup["contexts"]["nodes"]:
        typename = context["__typename"]
        if typename == "CheckRun":
            if context["conclusion"] in FAILING_CHECK_RUN_CONCLUSIONS:
                names.append(context["name"])
        elif typename == "StatusContext":
            if context["state"] in FAILING_STATUS_CONTEXT_STATES:
                names.append(context["context"])
    return names


def verdict(pr: dict[str, Any]) -> tuple[str, list[str]]:
    """Deterministically classify a pull request's mergeability.

    Returns (verdict, failing_check_names), evaluating rules in precedence
    order and returning on the first match.
    """
    if pr["isDraft"]:
        return "DRAFT", []

    if pr["mergeable"] == "CONFLICTING" or pr["mergeStateStatus"] == "DIRTY":
        return "CONFLICTS", []

    state = rollup_state(pr)
    checks = failing_checks(pr)
    if state in FAILING_ROLLUP_STATES or checks:
        return "CHECKS_FAILING", checks

    if state in PENDING_ROLLUP_STATES:
        return "CHECKS_PENDING", []

    if pr["reviewDecision"] == "CHANGES_REQUESTED":
        return "CHANGES_REQUESTED", []

    if pr["reviewDecision"] == "REVIEW_REQUIRED":
        return "NEEDS_APPROVAL", []

    if pr["mergeStateStatus"] == "BEHIND":
        return "BEHIND_BASE", []

    if pr["mergeable"] == "UNKNOWN":
        return "UNKNOWN", []

    return "READY", []


def build_report(pr: dict[str, Any]) -> dict[str, Any]:
    """Build the flattened, verdict-annotated record used for both outputs."""
    verdict_name, checks = verdict(pr)
    return {
        "repo": pr["repository"]["nameWithOwner"],
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["url"],
        "verdict": verdict_name,
        "failing_checks": checks,
        "mergeable": pr["mergeable"],
        "merge_state_status": pr["mergeStateStatus"],
        "review_decision": pr["reviewDecision"],
        "is_draft": pr["isDraft"],
        "base": pr["baseRefName"],
        "head": pr["headRefName"],
        "created_at": pr["createdAt"],
    }


def print_human_report(reports: list[dict[str, Any]], owner: str) -> None:
    """Print the grouped, human-readable report to stdout."""
    if not reports:
        print(f"No open Dependabot PRs found for {owner}.")
        return

    by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        by_repo[report["repo"]].append(report)

    for repo in sorted(by_repo):
        print(repo)
        for report in sorted(by_repo[repo], key=lambda r: r["number"]):
            print(
                f"  #{report['number']}  {report['verdict']}  {report['title']}"
            )
            print(f"    {report['url']}")
            if report["verdict"] == "CHECKS_FAILING" and report["failing_checks"]:
                print(f"    failing: {', '.join(report['failing_checks'])}")
        print()

    counts = Counter(report["verdict"] for report in reports)
    print(f"Total: {len(reports)} open Dependabot PR(s)")
    for verdict_name in VERDICT_PRECEDENCE:
        if counts[verdict_name]:
            print(f"  {verdict_name}: {counts[verdict_name]}")

    ready = [report for report in reports if report["verdict"] == "READY"]
    if ready:
        print()
        print("Ready to merge:")
        for report in sorted(ready, key=lambda r: (r["repo"], r["number"])):
            print(f"  gh pr merge {report['url']} --squash")
        print()
        print("Note: this script merges nothing; the commands above are hints only.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Check open Dependabot PRs for mergeability."
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
        help="Limit results to this repo. Repeatable.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON array instead of a human-readable report.",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point: gather Dependabot PRs and print the requested report."""
    args = parse_args()

    prs = search_dependabot_prs(args.owner)
    if args.repo:
        allowed_repos = set(args.repo)
        prs = [pr for pr in prs if pr["repository"]["nameWithOwner"] in allowed_repos]

    refresh_unknown_mergeability(prs)

    reports = [build_report(pr) for pr in prs]

    if args.json:
        reports_sorted = sorted(reports, key=lambda r: (r["repo"], r["number"]))
        print(json.dumps(reports_sorted, indent=2))
        return

    print_human_report(reports, args.owner)


if __name__ == "__main__":
    main()
