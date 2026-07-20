#!/usr/bin/env python3
"""Sync locally installed packages into dev-machine-setup's macOS vars file.

Collects installed Homebrew taps/casks/formulae (leaf formulae only --
dependencies of other installed formulae are excluded), PowerShell
modules, uv tools, bun global packages, and .NET global tools, then adds
any entries missing from examples/macOS_vars.yaml (alphabetically,
preserving comments). With no flags it creates a branch off origin/main, commits,
pushes, and opens a PR via gh. Additions only -- it never removes entries.

Usage:
  sync_packages.py [--dry-run] [--repo PATH]

  --dry-run   Print what would be added; touch nothing.
  --repo      Path to the dev-machine-setup clone
              (default: ~/git/dev-machine-setup).
"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

VARS_RELPATH = Path("examples") / "macOS_vars.yaml"

ITEM_RE = re.compile(r"^  - (.+?)(?:\s+#.*)?$")
COMMENTED_ITEM_RE = re.compile(r"^  # - (.+?)(?:\s+#.*)?$")
INDENTED_COMMENT_RE = re.compile(r"^  #")


def run(cmd, **kwargs):
    """Run a command, return stdout, raise on failure."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True, **kwargs
    )
    return result.stdout


def try_run(cmd, **kwargs):
    """Run a command, return stdout or None if the tool fails/is missing."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        return run(cmd, **kwargs)
    except subprocess.CalledProcessError:
        return None


# --- Collectors -------------------------------------------------------------
# Each returns a list of installed names, or None if the tool is unavailable.


def brew_info():
    """Single brew call shared by the cask and formula collectors."""
    out = try_run(["brew", "info", "--json=v2", "--installed"])
    return json.loads(out) if out else None


def collect_taps():
    out = try_run(["brew", "tap"])
    if out is None:
        return None
    return [
        line.strip()
        for line in out.splitlines()
        if line.strip() and not line.startswith("homebrew/")
    ]


def collect_casks(info):
    if info is None:
        return None
    return [c["token"] for c in info.get("casks", [])]


def collect_formulae(info):
    if info is None:
        return None
    formulae = info.get("formulae", [])
    # Anything another installed formula depends on will be installed
    # transitively anyway, so only leaves are pinned in the vars file.
    # installed_on_request alone is not enough: setup docs (pyenv,
    # ruby-build) have you brew-install libs directly, setting the flag
    # on what are effectively dependencies.
    dep_names = {d for f in formulae for d in f.get("dependencies", [])}
    names = []
    for f in formulae:
        if not any(i.get("installed_on_request") for i in f.get("installed", [])):
            continue
        if f["name"] in dep_names or f["full_name"] in dep_names:
            continue
        names.append(f["full_name"])
    return names


def collect_pwsh_modules():
    out = try_run(
        [
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-PSResource -ErrorAction SilentlyContinue).Name"
            " | Sort-Object -Unique",
        ]
    )
    if out is None:
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def collect_uv_tools():
    out = try_run(["uv", "tool", "list"])
    if out is None:
        return None
    names = []
    for line in out.splitlines():
        # Tool lines are unindented "name vX.Y.Z"; bin lines start with "- ".
        if line and not line.startswith((" ", "-")):
            names.append(line.split()[0])
    return names


def collect_bun_globals():
    out = try_run(["bun", "pm", "ls", "-g"])
    if out is None:
        return None
    names = []
    for line in out.splitlines():
        m = re.search(r"[├└]── (.+)@[^@]+$", line)
        if m:
            names.append(m.group(1))
    return names


def collect_dotnet_tools():
    out = try_run(["dotnet", "tool", "list", "--global"])
    if out is None:
        return None
    lines = out.splitlines()
    # Skip the "Package Id  Version  Commands" header and the dashed rule.
    return [line.split()[0] for line in lines[2:] if line.strip()]


# --- YAML editing (line-based, comment-preserving) --------------------------


def formula_basename(name):
    return name.rsplit("/", 1)[-1].lower()


def section_bounds(lines, section):
    """Return (header_idx, end_idx) for a top-level list section."""
    header_idx = None
    for i, line in enumerate(lines):
        if line == f"{section}:" or line.startswith(f"{section}:"):
            header_idx = i
            break
    if header_idx is None:
        raise KeyError(f"section not found: {section}")
    end = len(lines)
    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() and not line.startswith(" "):
            end = i
            break
    return header_idx, end


def existing_values(lines, header_idx, end):
    """Active and commented-out item values within a section."""
    active, excluded = [], []
    for line in lines[header_idx + 1 : end]:
        m = ITEM_RE.match(line)
        if m:
            active.append(m.group(1).strip().strip("'\""))
            continue
        m = COMMENTED_ITEM_RE.match(line)
        if m:
            excluded.append(m.group(1).strip().strip("'\""))
    return active, excluded


def format_item(value):
    if value.startswith(("@", "*", "&", "!")):
        return f"  - '{value}'"
    return f"  - {value}"


def insert_items(lines, section, new_values):
    """Insert values alphabetically among a section's items, in place."""
    for value in sorted(new_values, key=str.lower):
        header_idx, end = section_bounds(lines, section)
        insert_at = None
        last_item_idx = None
        for i in range(header_idx + 1, end):
            m = ITEM_RE.match(lines[i])
            if not m:
                continue
            last_item_idx = i
            if m.group(1).strip().strip("'\"").lower() > value.lower():
                insert_at = i
                # Keep any comment block above the displaced item attached
                # to it by inserting above those comments.
                while insert_at - 1 > header_idx and INDENTED_COMMENT_RE.match(
                    lines[insert_at - 1]
                ):
                    insert_at -= 1
                break
        if insert_at is None:
            insert_at = (
                last_item_idx + 1 if last_item_idx is not None else header_idx + 1
            )
        lines.insert(insert_at, format_item(value))


def compute_additions(vars_path):
    """Map of section -> sorted new values, plus notes about skipped tools."""
    lines = vars_path.read_text().splitlines()
    info = brew_info()
    collected = {
        "homebrew_taps": collect_taps(),
        "homebrew_casks": collect_casks(info),
        "homebrew_formulae": collect_formulae(info),
        "powershell_modules": collect_pwsh_modules(),
        "uv_tools": collect_uv_tools(),
        "bun_global_packages": collect_bun_globals(),
        "dotnet_tools": collect_dotnet_tools(),
    }
    additions, skipped = {}, []
    for section, installed in collected.items():
        if installed is None:
            skipped.append(section)
            continue
        header_idx, end = section_bounds(lines, section)
        active, excluded = existing_values(lines, header_idx, end)
        known = {v.lower() for v in active + excluded}
        if section == "homebrew_formulae":
            known |= {formula_basename(v) for v in active + excluded}
            new = [
                v
                for v in installed
                if v.lower() not in known and formula_basename(v) not in known
            ]
        else:
            new = [v for v in installed if v.lower() not in known]
        new = sorted(set(new), key=str.lower)
        if new:
            additions[section] = new
    return additions, skipped


# --- Git / PR ---------------------------------------------------------------


def git(repo, *args):
    return run(["git", "-C", str(repo), *args]).strip()


def make_pr(repo, vars_path, additions, skipped):
    rel = str(VARS_RELPATH)
    if git(repo, "status", "--porcelain", "--", rel):
        sys.exit(f"error: {rel} has uncommitted changes in {repo}; resolve first")

    prev_branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    git(repo, "fetch", "origin")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"chore/sync-installed-packages-{stamp}"
    git(repo, "switch", "-c", branch, "origin/main")

    try:
        # Recompute against origin/main's copy so the diff is exact.
        additions, skipped = compute_additions(vars_path)
        if not additions:
            print("Up to date with origin/main; nothing to do.")
            return None
        lines = vars_path.read_text().splitlines()
        for section, values in additions.items():
            insert_items(lines, section, values)
        vars_path.write_text("\n".join(lines) + "\n")

        git(repo, "add", rel)
        git(
            repo,
            "commit",
            "-m",
            "feat(macOS): add newly installed packages to vars",
        )
        git(repo, "push", "-u", "origin", branch)

        body_lines = [
            "Adds locally installed packages missing from"
            " `examples/macOS_vars.yaml`,",
            "collected by `sync-dev-machine-packages`.",
            "",
        ]
        for section, values in additions.items():
            body_lines.append(f"## {section}")
            body_lines.append("")
            body_lines.extend(f"- `{v}`" for v in values)
            body_lines.append("")
        if "powershell_modules" in additions:
            body_lines.append(
                "> Review PowerShell modules for transitive dependencies"
                " pulled in by other modules."
            )
            body_lines.append("")
        if skipped:
            body_lines.append(
                "Skipped (tool not available): " + ", ".join(skipped)
            )
        pr_url = run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                "ryanspletzer/dev-machine-setup",
                "--head",
                branch,
                "--title",
                "feat(macOS): add newly installed packages to vars",
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
    parser.add_argument(
        "--repo", default=str(Path.home() / "git" / "dev-machine-setup")
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser()
    vars_path = repo / VARS_RELPATH
    if not vars_path.is_file():
        sys.exit(f"error: {vars_path} not found")

    additions, skipped = compute_additions(vars_path)
    for section in skipped:
        print(f"skipped {section}: tool not available")
    if not additions:
        print("All installed packages are already in macOS_vars.yaml.")
        return
    for section, values in additions.items():
        print(f"{section}:")
        for v in values:
            print(f"  + {v}")

    if args.dry_run:
        print("\n(dry run: no changes made)")
        return

    pr_url = make_pr(repo, vars_path, additions, skipped)
    if pr_url:
        print(f"\nPR created: {pr_url}")


if __name__ == "__main__":
    main()
