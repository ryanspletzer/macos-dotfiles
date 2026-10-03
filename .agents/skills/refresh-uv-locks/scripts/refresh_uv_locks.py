#!/usr/bin/env python3
"""Refresh stale uv.lock files in local repo clones and open one PR per repo.

Reuses the deterministic discovery and classification from the sibling
``check-stale-locks`` skill so both skills agree on what "stale" means.
For every project whose ``uv lock --upgrade --dry-run`` plan would move at
least one package, this script branches off the repo's default branch,
runs ``uv lock --upgrade`` for real in each such project directory,
commits the regenerated ``uv.lock`` files with a conventional-commit
message, pushes, and opens a pull request via ``gh`` whose body lists
every moved package, split into direct and transitive dependencies.

Only ``uv.lock`` files are ever staged. The script never edits
``pyproject.toml``, never touches a project whose lockfile has
uncommitted changes, and never merges anything.

Usage:
  refresh_uv_locks.py [--dry-run] [--git-root PATH] [--repo NAME ...]
                      [--no-home] [--owner NAME] [--all-repos]
                      [--stale-only] [--timeout N] [--json]

  --dry-run     Print the would-be refreshes per repo/project; touch
                nothing (no branch, no lock write, no PR).
  --git-root    Root directory containing repo clones (default: ~/git).
  --repo        Limit to this repo (by directory name; "home" selects the
                home repo). Repeatable, and overrides the owner filter.
  --no-home     Skip the home-folder repo (~).
  --owner       Only act on repos whose origin remote belongs to this
                GitHub owner (default: ryanspletzer).
  --all-repos   Act on every repo regardless of origin owner.
  --stale-only  Refresh only projects whose verdict is STALE (transitive
                drift); skip DIRECT_ONLY projects, which Dependabot
                already handles when it covers them.
  --timeout     Per-project `uv` timeout in seconds (default: 120).
  --json        Emit one JSON object per repo instead of a human-readable
                report.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if sys.version_info < (3, 11):
    sys.exit(
        "error: refresh_uv_locks.py needs Python 3.11+ (for tomllib); "
        f"running under {sys.version.split()[0]}"
    )

CHECK_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "check-stale-locks" / "scripts"
)
sys.path.insert(0, str(CHECK_SCRIPTS_DIR))

import check_stale_locks as check  # noqa: E402

REFRESH_VERDICTS = {"STALE", "DIRECT_ONLY"}
BRANCH_PREFIX = "chore/refresh-uv-locks-"
COMMIT_TITLE = "chore(deps): refresh uv.lock files"
OUTCOME_ORDER = ["REFRESHED", "WOULD_REFRESH", "SKIPPED", "FAILED"]


# --- Subprocess helpers --------------------------------------------------


def run(cmd: list[str], **kwargs: Any) -> str:
    """Run a command, return stdout, raise CalledProcessError on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, **kwargs)
    return result.stdout


def git(repo: Path, *args: str) -> str:
    """Run a git command inside ``repo`` and return stripped stdout."""
    return run(["git", "-C", str(repo), *args]).strip()


def _tail(text: str, n: int = 5) -> str:
    """Return the last n non-blank lines of text, joined for a compact note."""
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return " | ".join(lines[-n:]) if lines else "(no output)"


def run_uv_upgrade(project_dir: Path, timeout: int) -> str | None:
    """Run ``uv lock --upgrade`` for real in project_dir; return an error note."""
    env = dict(os.environ)
    env["UV_NO_PROGRESS"] = "1"
    env["NO_COLOR"] = "1"
    try:
        result = subprocess.run(
            ["uv", "lock", "--upgrade", "--no-progress", "--color", "never"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return f"uv timed out after {timeout}s: {_tail(exc.stderr or '')}"
    except OSError as exc:
        return f"failed to run uv: {exc}"
    if result.returncode != 0:
        return f"uv exited {result.returncode}: {_tail(result.stderr)}"
    return None


# --- Preflight -----------------------------------------------------------


def git_config(key: str) -> str | None:
    """Return a global git config value, or None when unset."""
    result = subprocess.run(
        ["git", "config", "--global", "--get", key],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def preflight_signing(timeout: int) -> str | None:
    """Make sure commit signing can succeed before any lock is touched.

    When ``commit.gpgsign`` is on with the OpenPGP format, sign a throwaway
    message with the configured key. This raises the pinentry / hardware
    token prompt once, up front, so a cancelled or unavailable key fails
    fast instead of after every lock has been regenerated. Returns an
    error note, or None when signing works or is not configured.
    """
    if (git_config("commit.gpgsign") or "").lower() != "true":
        return None
    if (git_config("gpg.format") or "openpgp").lower() != "openpgp":
        return None
    gpg = git_config("gpg.program") or "gpg"
    key = git_config("user.signingkey")
    cmd = [gpg, "--detach-sign", "--output", os.devnull, "-"]
    if key:
        cmd[1:1] = ["--local-user", key]
    try:
        result = subprocess.run(
            cmd,
            input="",
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"signing prompt not answered within {timeout}s"
    except OSError as exc:
        return f"failed to run {gpg}: {exc}"
    if result.returncode != 0:
        return _tail(result.stderr)
    return None


# --- Planning ------------------------------------------------------------


def plan_repo(
    repo_label: str, repo_path: Path, timeout: int, stale_only: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (projects to refresh, projects skipped) for one repo.

    Each entry is the ``check-stale-locks`` project record, augmented with
    a ``reason`` on skipped entries.
    """
    projects = check.scan_repo(repo_label, repo_path, timeout)
    to_refresh: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for project in projects:
        verdict = project["verdict"]
        if verdict == "STALE" or (verdict == "DIRECT_ONLY" and not stale_only):
            to_refresh.append(project)
        else:
            reason = verdict
            if verdict == "UNKNOWN" and project.get("note"):
                reason = f"UNKNOWN ({project['note']})"
            elif verdict == "DIRECT_ONLY":
                reason = "DIRECT_ONLY (--stale-only)"
            skipped.append({**project, "reason": reason})
    return to_refresh, skipped


# --- Git / PR ------------------------------------------------------------


def default_base_branch(repo: Path) -> str:
    """Return the repo's default branch name as seen from origin."""
    try:
        base_ref = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    except subprocess.CalledProcessError:
        base_ref = "origin/main"
    return base_ref.split("/", 1)[1] if base_ref.startswith("origin/") else base_ref


def lock_rel_path(repo_path: Path, project: dict[str, Any]) -> str:
    """Return the repo-relative path of a project's uv.lock."""
    return str(Path(project["project"]) / "uv.lock").removeprefix("./")


def format_pr_body(refreshed: list[dict[str, Any]]) -> str:
    """Build the PR body listing moved packages per project."""
    lines = [
        "Lockfiles refreshed by the `refresh-uv-locks` skill (`uv lock --upgrade`).",
        "",
    ]
    for project in refreshed:
        lines.append(f"## `{project['project']}`")
        lines.append("")
        for kind in ("direct", "transitive", "unknown"):
            pkgs = sorted(
                (p for p in project["packages"] if p["kind"] == kind),
                key=lambda p: p["name"],
            )
            if not pkgs:
                continue
            lines.append(f"**{kind}**")
            lines.append("")
            for pkg in pkgs:
                if pkg["verdict"] == "ADDED":
                    lines.append(f"- {pkg['name']}: added {pkg['new']}")
                elif pkg["verdict"] == "REMOVED":
                    lines.append(f"- {pkg['name']}: removed {pkg['old']}")
                else:
                    bump = f" ({pkg['bump']})" if pkg.get("bump") else ""
                    lines.append(f"- {pkg['name']}: {pkg['old']} -> {pkg['new']}{bump}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def refresh_repo(
    repo_label: str,
    repo_path: Path,
    to_refresh: list[dict[str, Any]],
    timeout: int,
) -> dict[str, Any]:
    """Refresh every planned project in one repo and open a PR.

    Returns a repo-level result dict with an ``outcome`` of REFRESHED,
    SKIPPED, or FAILED plus per-project ``results``.
    """
    rel_locks = [lock_rel_path(repo_path, p) for p in to_refresh]
    dirty = git(repo_path, "status", "--porcelain", "--", *rel_locks)
    if dirty:
        return {
            "repo": repo_label,
            "outcome": "SKIPPED",
            "reason": f"uncommitted changes in {', '.join(rel_locks)}",
            "pr_url": None,
            "results": [],
        }

    prev_branch = git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    git(repo_path, "fetch", "origin")
    base = default_base_branch(repo_path)
    stamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
    branch = f"{BRANCH_PREFIX}{stamp}"
    git(repo_path, "switch", "-c", branch, f"origin/{base}")

    results: list[dict[str, Any]] = []
    refreshed: list[dict[str, Any]] = []
    discard_branch = False
    try:
        for project in to_refresh:
            project_dir = repo_path / project["project"]
            rel_lock = lock_rel_path(repo_path, project)
            note = run_uv_upgrade(project_dir, timeout)
            if note is not None:
                git(repo_path, "checkout", "--", rel_lock)
                results.append(
                    {"project": project["project"], "outcome": "FAILED", "note": note}
                )
                continue
            if not git(repo_path, "status", "--porcelain", "--", rel_lock):
                results.append(
                    {
                        "project": project["project"],
                        "outcome": "SKIPPED",
                        "note": f"lock unchanged against origin/{base}",
                    }
                )
                continue
            git(repo_path, "add", "--", rel_lock)
            refreshed.append(project)
            results.append(
                {"project": project["project"], "outcome": "REFRESHED", "note": None}
            )

        if not refreshed:
            git(repo_path, "switch", prev_branch)
            git(repo_path, "branch", "-D", branch)
            outcome = (
                "FAILED"
                if any(r["outcome"] == "FAILED" for r in results)
                else "SKIPPED"
            )
            return {
                "repo": repo_label,
                "outcome": outcome,
                "reason": f"no lock changed against origin/{base}",
                "pr_url": None,
                "results": results,
            }

        body = format_pr_body(refreshed)
        try:
            git(repo_path, "commit", "-m", COMMIT_TITLE, "-m", body)
            git(repo_path, "push", "-u", "origin", branch)
            pr_url = run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--head",
                    branch,
                    "--base",
                    base,
                    "--title",
                    COMMIT_TITLE,
                    "--body",
                    body,
                ],
                cwd=str(repo_path),
            ).strip()
        except subprocess.CalledProcessError as exc:
            ahead = git(repo_path, "rev-list", "--count", f"origin/{base}..HEAD")
            if ahead == "0":
                # The commit itself failed (e.g. signing was cancelled):
                # drop the regenerated locks so nothing leaks onto the
                # previous branch, and remove the empty branch below.
                git(repo_path, "restore", "--staged", "--worktree", "--", *rel_locks)
                discard_branch = True
            return {
                "repo": repo_label,
                "outcome": "FAILED",
                "reason": f"branch {branch}: {_tail(exc.stderr or exc.stdout or '')}",
                "pr_url": None,
                "results": results,
            }
    finally:
        current = git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        if current != prev_branch:
            git(repo_path, "switch", prev_branch)
        if discard_branch:
            git(repo_path, "branch", "-D", branch)

    outcome = (
        "FAILED" if any(r["outcome"] == "FAILED" for r in results) else "REFRESHED"
    )
    return {
        "repo": repo_label,
        "outcome": outcome,
        "reason": None,
        "pr_url": pr_url,
        "results": results,
    }


# --- Report --------------------------------------------------------------


def print_plan(
    repo_label: str, to_refresh: list[dict[str, Any]], skipped: list[dict[str, Any]]
) -> None:
    """Print the per-repo plan: what will be refreshed and why the rest is not."""
    print(repo_label)
    for project in to_refresh:
        counts = []
        if project["transitive_outdated"]:
            counts.append(f"{project['transitive_outdated']} transitive")
        if project["direct_outdated"]:
            counts.append(f"{project['direct_outdated']} direct")
        unknown = sum(1 for p in project["packages"] if p["kind"] == "unknown")
        if unknown:
            counts.append(f"{unknown} unknown")
        print(f"  {project['project']}  {project['verdict']}  ({', '.join(counts)})")
    for project in skipped:
        if project["verdict"] != "CURRENT":
            print(f"  {project['project']}  skip: {project['reason']}")


def main() -> None:
    """Entry point: plan, refresh, and report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--git-root", default=str(Path.home() / "git"))
    parser.add_argument("--repo", action="append", metavar="NAME")
    parser.add_argument("--no-home", action="store_true")
    parser.add_argument("--owner", default="ryanspletzer")
    parser.add_argument("--all-repos", action="store_true")
    parser.add_argument("--stale-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    for tool in ("uv", "git", "gh"):
        if shutil.which(tool) is None:
            sys.exit(f"error: `{tool}` CLI not found on PATH")

    if not args.dry_run:
        note = preflight_signing(args.timeout)
        if note is not None:
            sys.exit(
                "error: commit signing is configured but failed; unlock the "
                f"signing key (answer the pinentry / touch the token) and rerun: {note}"
            )

    git_root = Path(args.git_root).expanduser()
    repo_filter = set(args.repo) if args.repo else None
    include_home = not args.no_home and (repo_filter is None or "home" in repo_filter)
    owner = None if args.all_repos else args.owner
    repos = check.discover_repos(git_root, include_home, repo_filter, owner)

    repo_results: list[dict[str, Any]] = []
    pr_urls: list[str] = []
    for repo_label, repo_path in repos:
        to_refresh, skipped = plan_repo(
            repo_label, repo_path, args.timeout, args.stale_only
        )
        if not to_refresh and all(p["verdict"] == "CURRENT" for p in skipped):
            continue

        if not args.json:
            print_plan(repo_label, to_refresh, skipped)

        if not to_refresh:
            repo_results.append(
                {
                    "repo": repo_label,
                    "outcome": "SKIPPED",
                    "reason": "nothing to refresh",
                    "pr_url": None,
                    "results": [],
                }
            )
            if not args.json:
                print()
            continue

        if args.dry_run:
            repo_results.append(
                {
                    "repo": repo_label,
                    "outcome": "WOULD_REFRESH",
                    "reason": None,
                    "pr_url": None,
                    "results": [
                        {
                            "project": p["project"],
                            "outcome": "WOULD_REFRESH",
                            "note": None,
                        }
                        for p in to_refresh
                    ],
                }
            )
            if not args.json:
                print("  (dry run: no changes made)")
                print()
            continue

        result = refresh_repo(repo_label, repo_path, to_refresh, args.timeout)
        repo_results.append(result)
        if not args.json:
            for r in result["results"]:
                suffix = f"  {r['note']}" if r["note"] else ""
                print(f"  {r['project']}  {r['outcome']}{suffix}")
            if result["pr_url"]:
                print(f"  PR: {result['pr_url']}")
                pr_urls.append(result["pr_url"])
            elif result["reason"]:
                print(f"  {result['outcome']}: {result['reason']}")
            print()

    if args.json:
        print(json.dumps(repo_results, indent=2))
    else:
        if not repo_results:
            print("All uv.lock files are current.")
        else:
            counts = {o: 0 for o in OUTCOME_ORDER}
            for r in repo_results:
                counts[r["outcome"]] += 1
            print(f"Done: {len(repo_results)} repo(s) with movement")
            for o in OUTCOME_ORDER:
                if counts[o]:
                    print(f"  {o}: {counts[o]}")
            if pr_urls:
                print()
                print("PRs created:")
                for url in pr_urls:
                    print(f"  {url}")

    if any(r["outcome"] == "FAILED" for r in repo_results):
        sys.exit(1)


if __name__ == "__main__":
    main()
