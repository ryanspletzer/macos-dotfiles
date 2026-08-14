#!/usr/bin/env python3
"""Update pinned uv and setup-uv versions in GitHub Actions workflows.

Scans repos under ~/git for workflow files that pin astral-sh/setup-uv
(the action's sha pin and/or its `version:` input) or set a UV_VERSION
env var, resolves the latest uv and setup-uv releases via `gh api`, and
rewrites any stale pins in place. With no flags it opens one PR per
changed repo.

Usage:
  update_uv_pins.py [--dry-run] [--git-root PATH]

  --dry-run    Print the would-be changes per repo/file; touch nothing.
  --git-root   Root directory containing repo clones (default: ~/git).
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ACTION_USES_RE = re.compile(
    r"^(\s*(?:-\s+)?uses:\s*astral-sh/setup-uv@)(\S+)(\s*#.*)?$"
)
UV_VERSION_RE = re.compile(
    r'^(\s*UV_VERSION:\s*["\']?)(\d+\.\d+\.\d+)(["\']?\s*(?:#.*)?)$'
)
WITH_VERSION_RE = re.compile(
    r'^(\s*version:\s*["\']?)(\d+\.\d+\.\d+)(["\']?\s*(?:#.*)?)$'
)


def run(cmd, **kwargs):
    """Run a command, return stdout, raise on failure."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True, **kwargs
    )
    return result.stdout


def git(repo, *args):
    return run(["git", "-C", str(repo), *args]).strip()


# --- Rewriting (line-based, comment/format-preserving) ----------------------


def _old_tag(comment):
    """Pull the trailing '# vX.Y.Z' tag out of an old uses-line comment."""
    if not comment:
        return "?"
    m = re.search(r"#\s*(\S+)", comment)
    return m.group(1) if m else "?"


def _clears_setup_uv(line):
    """True if this (non-uses) line ends a setup-uv step block."""
    if re.match(r"^\s*-\s", line):
        return True
    if line == line.lstrip():
        return True
    if "uses:" in line:
        return True
    return False


def rewrite(text, uv_version, action_sha, action_tag):
    """Rewrite uv/setup-uv pins in workflow text.

    Returns (new_text, changes) where changes is a list of human-readable
    strings describing what changed.
    """
    trailing_newline = text.endswith("\n")
    lines = text.splitlines()
    new_lines = []
    changes = []
    in_setup_uv = False

    for line in lines:
        m = ACTION_USES_RE.match(line)
        if m:
            prefix, ref, comment = m.group(1), m.group(2), m.group(3)
            new_line = f"{prefix}{action_sha} # {action_tag}"
            if new_line != line:
                changes.append(
                    f"setup-uv {ref[:8]} ({_old_tag(comment)})"
                    f" -> {action_sha[:8]} ({action_tag})"
                )
                line = new_line
            in_setup_uv = True
            new_lines.append(line)
            continue

        if in_setup_uv and line.strip() and _clears_setup_uv(line):
            in_setup_uv = False

        m = UV_VERSION_RE.match(line)
        if m:
            prefix, ver, suffix = m.group(1), m.group(2), m.group(3)
            if ver != uv_version:
                changes.append(f"uv {ver} -> {uv_version}")
                line = f"{prefix}{uv_version}{suffix}"
            new_lines.append(line)
            continue

        if in_setup_uv:
            m = WITH_VERSION_RE.match(line)
            if m:
                prefix, ver, suffix = m.group(1), m.group(2), m.group(3)
                if ver != uv_version:
                    changes.append(f"uv {ver} -> {uv_version}")
                    line = f"{prefix}{uv_version}{suffix}"
                new_lines.append(line)
                continue

        new_lines.append(line)

    new_text = "\n".join(new_lines)
    if trailing_newline:
        new_text += "\n"
    return new_text, list(dict.fromkeys(changes))


# --- Discovering target files ------------------------------------------------


def discover_files(git_root):
    """List (repo, [workflow files]) for repos with uv/setup-uv pins."""
    results = []
    for repo in sorted(p for p in git_root.iterdir() if p.is_dir()):
        wf_dir = repo / ".github" / "workflows"
        if not wf_dir.is_dir():
            continue
        files = sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")))
        matched = [
            f
            for f in files
            if "astral-sh/setup-uv" in f.read_text() or "UV_VERSION" in f.read_text()
        ]
        if matched:
            results.append((repo, matched))
    return results


# --- Resolving latest versions -----------------------------------------------


def resolve_latest():
    """Return (uv_version, setup_uv_tag, setup_uv_sha) for the latest releases."""
    uv_tag = run(
        ["gh", "api", "repos/astral-sh/uv/releases/latest", "--jq", ".tag_name"]
    ).strip()
    uv_version = uv_tag[1:] if uv_tag.startswith("v") else uv_tag

    setup_uv_tag = run(
        [
            "gh",
            "api",
            "repos/astral-sh/setup-uv/releases/latest",
            "--jq",
            ".tag_name",
        ]
    ).strip()
    ref_out = run(
        [
            "gh",
            "api",
            f"repos/astral-sh/setup-uv/git/ref/tags/{setup_uv_tag}",
            "--jq",
            '.object.type + " " + .object.sha',
        ]
    ).strip()
    obj_type, sha = ref_out.split(" ", 1)
    if obj_type == "tag":
        sha = run(
            [
                "gh",
                "api",
                f"repos/astral-sh/setup-uv/git/tags/{sha}",
                "--jq",
                ".object.sha",
            ]
        ).strip()
    return uv_version, setup_uv_tag, sha


# --- Git / PR -----------------------------------------------------------------


def make_pr(repo, files, uv_version, action_sha, action_tag):
    rel_paths = [str(f.relative_to(repo)) for f in files]
    if git(repo, "status", "--porcelain", "--", *rel_paths):
        print(
            f"skipping {repo.name}: uncommitted changes in {', '.join(rel_paths)}"
        )
        return None

    prev_branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    git(repo, "fetch", "origin")
    try:
        base_ref = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    except subprocess.CalledProcessError:
        base_ref = "origin/main"
    base = base_ref.split("/", 1)[1] if base_ref.startswith("origin/") else base_ref

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"chore/update-uv-pins-{stamp}"
    git(repo, "switch", "-c", branch, f"origin/{base}")

    try:
        changed = {}
        for f in files:
            new_text, changes = rewrite(
                f.read_text(), uv_version, action_sha, action_tag
            )
            if changes:
                changed[f] = (new_text, changes)

        if not changed:
            print(f"  {repo.name}: already up to date with origin/{base}")
            git(repo, "switch", prev_branch)
            git(repo, "branch", "-D", branch)
            return None

        for f, (new_text, _) in changed.items():
            f.write_text(new_text)

        git(repo, "add", *[str(f.relative_to(repo)) for f in changed])

        all_changes = [c for _, cs in changed.values() for c in cs]
        parts = []
        if any(c.startswith("uv ") for c in all_changes):
            parts.append(f"uv to {uv_version}")
        if any(c.startswith("setup-uv ") for c in all_changes):
            parts.append(f"setup-uv to {action_tag}")
        msg = "ci: update " + " and ".join(parts)

        git(repo, "commit", "-m", msg)
        git(repo, "push", "-u", "origin", branch)

        body_lines = ["Pins updated by the `update-uv-pins` skill.", ""]
        for f, (_, cs) in changed.items():
            body_lines.append(f"- `{f.relative_to(repo)}`: " + "; ".join(cs))

        pr_url = run(
            [
                "gh",
                "pr",
                "create",
                "--head",
                branch,
                "--title",
                msg,
                "--body",
                "\n".join(body_lines),
            ],
            cwd=str(repo),
        ).strip()
        return pr_url
    finally:
        git(repo, "switch", prev_branch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--git-root", default=str(Path.home() / "git"))
    args = parser.parse_args()

    git_root = Path(args.git_root).expanduser()
    if not git_root.is_dir():
        sys.exit(f"error: {git_root} not found")

    uv_version, action_tag, action_sha = resolve_latest()
    print(f"Latest: uv {uv_version}, setup-uv {action_tag} ({action_sha[:8]}...)")

    repos = discover_files(git_root)
    if not repos:
        print("No repos with uv pins found.")
        return

    pr_urls = []
    for repo, files in repos:
        print(f"\n{repo.name}:")
        changed = {}
        for f in files:
            new_text, changes = rewrite(
                f.read_text(), uv_version, action_sha, action_tag
            )
            if changes:
                changed[f] = changes

        if not changed:
            print("  already up to date")
            continue

        for f, changes in changed.items():
            print(f"  {f.relative_to(repo)}:")
            for c in changes:
                print(f"    {c}")

        if args.dry_run:
            print("  (dry run: no changes made)")
            continue

        pr_url = make_pr(repo, list(changed), uv_version, action_sha, action_tag)
        if pr_url:
            pr_urls.append(pr_url)

    if pr_urls:
        print("\nPRs created:")
        for url in pr_urls:
            print(f"  {url}")


if __name__ == "__main__":
    main()
