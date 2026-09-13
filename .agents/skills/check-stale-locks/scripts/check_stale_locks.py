#!/usr/bin/env python3
"""Find uv.lock files in local repo clones and report what an upgrade would move.

Scans every repo under a git root (plus the user's home-folder repo) for
`uv.lock` files, runs `uv lock --upgrade --dry-run` in each project
directory, and parses uv's plan to see which packages would update, be
added, or be removed if the lock were refreshed. Each moved package is
classified as a direct dependency (declared in the project's own
`pyproject.toml`, and covered by Dependabot when the repo's
`dependabot.yml` has a matching `uv`/`pip` entry) or a transitive one
(never touched by Dependabot version updates). This script is read-only:
it never writes files, edits locks, or mutates anything other than
spawning `uv lock --upgrade --dry-run`, which itself changes nothing on
disk.

Usage:
  check_stale_locks.py [--git-root PATH] [--repo NAME ...] [--no-home]
                        [--owner NAME] [--all-repos]
                        [--transitive-only] [--all] [--timeout N] [--json]

  --git-root         Root directory containing repo clones (default: ~/git).
  --repo             Limit the scan to this repo (by directory name; "home"
                     selects the home repo). Repeatable, and overrides the
                     owner filter.
  --no-home          Skip scanning the home-folder repo.
  --owner            Only scan repos whose origin remote belongs to this
                     GitHub owner (default: ryanspletzer). Clones of other
                     people's repos are skipped.
  --all-repos        Scan every repo regardless of origin owner.
  --transitive-only  Omit direct-dependency entries from the human report
                     (JSON always includes everything).
  --all              Include CURRENT projects in the human report.
  --timeout          Per-project `uv` timeout in seconds (default: 120).
  --json             Emit one JSON object per project instead of a
                     human-readable report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if sys.version_info < (3, 11):
    sys.exit(
        "error: check_stale_locks.py needs Python 3.11+ (for tomllib); "
        f"running under {sys.version.split()[0]}"
    )

import tomllib

# --- Regexes -----------------------------------------------------------------

UPDATE_RE = re.compile(r"^Update\s+(\S+)\s+v(\S+)\s+->\s+v(\S+)$")
ADD_RE = re.compile(r"^Add\s+(\S+)\s+v(\S+)$")
REMOVE_RE = re.compile(r"^Remove\s+(\S+)\s+v(\S+)$")
RESOLVED_RE = re.compile(r"^Resolved\s+\d+\s+packages?\s+in\b")

REQ_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+")
NAME_NORMALIZE_RE = re.compile(r"[-_.]+")

GITHUB_REMOTE_OWNER_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)([^/\s]+)/"
)

DEPENDABOT_ENTRY_RE = re.compile(
    r'^\s*-\s*package-ecosystem:\s*["\']?([\w.-]+)["\']?\s*$'
)
DEPENDABOT_DIRECTORY_RE = re.compile(r'^\s*directory:\s*["\']?([^"\'\s]+)["\']?\s*$')
DEPENDABOT_DIRECTORIES_HEADER_RE = re.compile(r"^\s*directories:\s*$")
DEPENDABOT_LIST_ITEM_RE = re.compile(r'^\s*-\s*["\']?([^"\'\s]+)["\']?\s*$')

PRUNE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".tox",
    ".nox",
    "site-packages",
}

UV_ECOSYSTEMS = {"uv", "pip"}

VERDICT_PRECEDENCE = ["STALE", "DIRECT_ONLY", "UNKNOWN", "CURRENT"]


# --- Version parsing and comparison ------------------------------------------


def parse_version(text: str) -> tuple[int, ...] | None:
    """Parse a version string into a tuple of ints, or None if unparseable.

    Strips a leading v/V, splits on '.', and for each component takes the
    leading digit run; stops at the first component with no leading digits.
    """
    stripped = text[1:] if text[:1] in ("v", "V") else text
    parts: list[int] = []
    for part in stripped.split("."):
        m = re.match(r"\d+", part)
        if not m:
            break
        parts.append(int(m.group(0)))
    return tuple(parts) if parts else None


def classify_bump(old: str, new: str) -> str:
    """Classify an Update as major/minor/patch/other by first 3 components."""
    old_v = parse_version(old)
    new_v = parse_version(new)
    if old_v is None or new_v is None:
        return "other"
    old3 = (old_v + (0, 0, 0))[:3]
    new3 = (new_v + (0, 0, 0))[:3]
    if old3[0] != new3[0]:
        return "major"
    if old3[1] != new3[1]:
        return "minor"
    if old3[2] != new3[2]:
        return "patch"
    return "other"


# --- Repo discovery (mirrors check-pinned-tools; kept self-contained) -------


def origin_owner(repo_path: Path) -> str | None:
    """Return the GitHub owner of the repo's origin remote, or None."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    m = GITHUB_REMOTE_OWNER_RE.match(result.stdout.strip())
    return m.group(1) if m else None


def discover_repos(
    git_root: Path,
    include_home: bool,
    repo_filter: set[str] | None,
    owner: str | None,
) -> list[tuple[str, Path]]:
    """Return sorted (label, path) pairs for repos to scan.

    `label` is the directory name (or "home" for the home repo) and doubles
    as the value matched against --repo. When `owner` is set and no explicit
    --repo filter is given, repos under the git root whose origin remote
    belongs to a different GitHub owner (clones of other people's repos)
    are skipped; the home repo is always the user's own.
    """
    repos: list[tuple[str, Path]] = []

    if git_root.is_dir():
        for entry in sorted(git_root.iterdir()):
            if not entry.is_dir():
                continue
            if not (entry / ".git").exists():
                continue
            if (
                owner is not None
                and repo_filter is None
                and (origin_owner(entry) or "").lower() != owner.lower()
            ):
                continue
            repos.append((entry.name, entry))

    if include_home:
        repos.append(("home", Path.home()))

    if repo_filter is not None:
        repos = [(name, path) for name, path in repos if name in repo_filter]

    repos.sort(key=lambda pair: pair[0])
    return repos


# --- Lock discovery -----------------------------------------------------


def find_uv_locks(repo_label: str, repo_path: Path) -> list[Path]:
    """Return sorted uv.lock paths within a repo.

    Ordinary repo clones are walked directly, pruning directories that
    never hold a project (`.git`, virtualenvs, caches, hidden dirs). The
    home-folder repo (`~`) is a deliberate exception: per its own CLAUDE.md
    it uses an ignore-everything-then-unignore strategy, and the raw
    filesystem underneath it also holds tens of gigabytes of unrelated
    content (an OS Library folder, VM disk images, package-manager caches)
    that a plain walk would traverse slowly and riskily. For "home" we
    instead ask git which `uv.lock` files it actually tracks, which is
    fast, safe, and correct for a repo where anything relevant must have
    been explicitly un-ignored to be committed in the first place.
    """
    if repo_label == "home":
        return _find_tracked_uv_locks(repo_path)
    return _walk_for_uv_locks(repo_path)


def _walk_for_uv_locks(repo_path: Path) -> list[Path]:
    """Walk repo_path for uv.lock files, pruning noise directories."""
    locks: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d for d in dirnames if d not in PRUNE_DIRS and not d.startswith(".")
        ]
        if "uv.lock" in filenames:
            locks.append(Path(dirpath) / "uv.lock")
    return sorted(locks)


def _find_tracked_uv_locks(repo_path: Path) -> list[Path]:
    """Return git-tracked uv.lock files under repo_path."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), "ls-files", "-z", "--", "uv.lock", "*/uv.lock"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    paths = [p for p in result.stdout.split("\0") if p]
    locks = [repo_path / p for p in paths if (repo_path / p).is_file()]
    return sorted(locks)


# --- Dependabot coverage ------------------------------------------------


def normalize_project_path(path: str) -> str:
    """Normalize a dependabot `directory` value or project rel-path for comparison."""
    normalized = path.strip().strip("/")
    return normalized if normalized else "."


def dependabot_covered_dirs(repo_path: Path) -> set[str]:
    """Return normalized directories covered by a uv/pip dependabot entry."""
    covered: set[str] = set()
    for name in ("dependabot.yml", "dependabot.yaml"):
        path = repo_path / ".github" / name
        if not path.is_file():
            continue
        try:
            lines = path.read_text().splitlines()
        except OSError:
            continue

        current_ecosystem: str | None = None
        in_directories_list = False
        for line in lines:
            entry_m = DEPENDABOT_ENTRY_RE.match(line)
            if entry_m:
                current_ecosystem = entry_m.group(1).lower()
                in_directories_list = False
                continue

            if current_ecosystem not in UV_ECOSYSTEMS:
                in_directories_list = False
                continue

            dir_m = DEPENDABOT_DIRECTORY_RE.match(line)
            if dir_m:
                covered.add(normalize_project_path(dir_m.group(1)))
                in_directories_list = False
                continue

            if DEPENDABOT_DIRECTORIES_HEADER_RE.match(line):
                in_directories_list = True
                continue

            if in_directories_list:
                item_m = DEPENDABOT_LIST_ITEM_RE.match(line)
                if item_m:
                    covered.add(normalize_project_path(item_m.group(1)))
                    continue
                in_directories_list = False

    return covered


# --- pyproject.toml parsing: direct dependency names ------------------------


def extract_requirement_name(requirement: str) -> str:
    """Extract the leading distribution-name run from a requirement string."""
    m = REQ_NAME_RE.match(requirement.strip())
    return m.group(0) if m else requirement.strip()


def normalize_name(name: str) -> str:
    """PEP 503 normalize: lowercase, collapse -/_/. runs to a single '-'."""
    return NAME_NORMALIZE_RE.sub("-", name).lower()


def load_toml(path: Path) -> dict[str, Any] | None:
    """Load a TOML file, returning None if missing or unparseable."""
    if not path.is_file():
        return None
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def direct_dep_names_from_pyproject(data: dict[str, Any]) -> set[str]:
    """Collect normalized direct dependency names from a parsed pyproject.toml."""
    names: set[str] = set()

    project = data.get("project")
    if isinstance(project, dict):
        for req in project.get("dependencies") or []:
            if isinstance(req, str):
                names.add(normalize_name(extract_requirement_name(req)))
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group in optional.values():
                if isinstance(group, list):
                    for req in group:
                        if isinstance(req, str):
                            names.add(normalize_name(extract_requirement_name(req)))

    dep_groups = data.get("dependency-groups")
    if isinstance(dep_groups, dict):
        for group in dep_groups.values():
            if isinstance(group, list):
                for item in group:
                    # Skip {include-group = "..."} entries; only plain
                    # requirement strings are direct dependencies here.
                    if isinstance(item, str):
                        names.add(normalize_name(extract_requirement_name(item)))

    tool = data.get("tool")
    tool_uv = tool.get("uv") if isinstance(tool, dict) else None
    if isinstance(tool_uv, dict):
        for req in tool_uv.get("dev-dependencies") or []:
            if isinstance(req, str):
                names.add(normalize_name(extract_requirement_name(req)))

    return names


def _resolve_workspace_members(
    project_dir: Path, members: list[Any], excludes: list[Any]
) -> list[Path]:
    """Glob workspace member directories relative to project_dir, honoring exclude."""
    matched: set[Path] = set()
    for pattern in members:
        if not isinstance(pattern, str):
            continue
        for path in project_dir.glob(pattern):
            if path.is_dir():
                matched.add(path)

    excluded: set[Path] = set()
    for pattern in excludes:
        if not isinstance(pattern, str):
            continue
        for path in project_dir.glob(pattern):
            excluded.add(path)

    return sorted(p for p in matched if p not in excluded)


def collect_direct_dep_names(project_dir: Path) -> tuple[set[str] | None, str | None]:
    """Return (normalized direct dep names, note); names is None if unresolvable."""
    data = load_toml(project_dir / "pyproject.toml")
    if data is None:
        return None, "pyproject.toml missing or unparseable"

    names = direct_dep_names_from_pyproject(data)

    tool = data.get("tool")
    tool_uv = tool.get("uv") if isinstance(tool, dict) else None
    workspace = tool_uv.get("workspace") if isinstance(tool_uv, dict) else None
    if isinstance(workspace, dict):
        members = workspace.get("members") or []
        excludes = workspace.get("exclude") or []
        for member_dir in _resolve_workspace_members(project_dir, members, excludes):
            member_data = load_toml(member_dir / "pyproject.toml")
            if member_data is not None:
                names |= direct_dep_names_from_pyproject(member_data)

    return names, None


def find_exclude_newer(project_dir: Path) -> str | None:
    """Return the exclude-newer date set beside a project's lockfile, if any."""
    pyproject = load_toml(project_dir / "pyproject.toml")
    if isinstance(pyproject, dict):
        tool = pyproject.get("tool")
        tool_uv = tool.get("uv") if isinstance(tool, dict) else None
        if isinstance(tool_uv, dict):
            value = tool_uv.get("exclude-newer")
            if value is not None:
                return value.isoformat() if hasattr(value, "isoformat") else str(value)

    uv_toml = load_toml(project_dir / "uv.toml")
    if isinstance(uv_toml, dict):
        value = uv_toml.get("exclude-newer")
        if value is not None:
            return value.isoformat() if hasattr(value, "isoformat") else str(value)

    return None


# --- Running uv and parsing its plan -----------------------------------------


def _tail(text: str, n: int = 5) -> str:
    """Return the last n non-blank lines of text, joined for a compact note."""
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return " | ".join(lines[-n:]) if lines else "(no output)"


def run_uv_dry_run(project_dir: Path, timeout: int) -> tuple[list[str], str | None]:
    """Run `uv lock --upgrade --dry-run` in project_dir.

    Returns (stderr_lines, note). note is set on timeout, invocation
    failure, or a non-zero exit, in which case the caller should treat the
    project as UNKNOWN.
    """
    env = dict(os.environ)
    env["UV_NO_PROGRESS"] = "1"
    env["NO_COLOR"] = "1"

    try:
        result = subprocess.run(
            [
                "uv",
                "lock",
                "--upgrade",
                "--dry-run",
                "--no-progress",
                "--color",
                "never",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr or ""
        return stderr.splitlines(), f"uv timed out after {timeout}s: {_tail(stderr)}"
    except OSError as exc:
        return [], f"failed to run uv: {exc}"

    if result.returncode != 0:
        note = f"uv exited {result.returncode}: {_tail(result.stderr)}"
        return result.stderr.splitlines(), note

    return result.stderr.splitlines(), None


def parse_uv_output(lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse uv dry-run stderr lines into package movements and leftover notes."""
    packages: list[dict[str, Any]] = []
    notes: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line or RESOLVED_RE.match(line):
            continue

        m = UPDATE_RE.match(line)
        if m:
            name, old, new = m.groups()
            packages.append(
                {"name": name, "verdict": "OUTDATED", "old": old, "new": new}
            )
            continue

        m = ADD_RE.match(line)
        if m:
            name, new = m.groups()
            packages.append({"name": name, "verdict": "ADDED", "old": None, "new": new})
            continue

        m = REMOVE_RE.match(line)
        if m:
            name, old = m.groups()
            packages.append(
                {"name": name, "verdict": "REMOVED", "old": old, "new": None}
            )
            continue

        notes.append(line)

    return packages, notes


# --- Per-project check --------------------------------------------------


def check_project(
    repo_label: str,
    repo_path: Path,
    project_dir: Path,
    timeout: int,
    covered_dirs: set[str],
) -> dict[str, Any]:
    """Check a single project's uv.lock for staleness."""
    project_rel = str(project_dir.relative_to(repo_path))
    dependabot_covered = normalize_project_path(project_rel) in covered_dirs
    exclude_newer = find_exclude_newer(project_dir)

    stderr_lines, run_note = run_uv_dry_run(project_dir, timeout)
    if run_note is not None:
        return {
            "repo": repo_label,
            "repo_path": str(repo_path),
            "project": project_rel,
            "verdict": "UNKNOWN",
            "dependabot_covered": dependabot_covered,
            "exclude_newer": exclude_newer,
            "note": run_note,
            "packages": [],
            "direct_outdated": 0,
            "transitive_outdated": 0,
        }

    packages, leftover_notes = parse_uv_output(stderr_lines)
    direct_names, dep_note = collect_direct_dep_names(project_dir)

    for pkg in packages:
        if pkg["verdict"] == "OUTDATED":
            pkg["bump"] = classify_bump(pkg["old"], pkg["new"])
        else:
            pkg["bump"] = None
        if direct_names is None:
            pkg["kind"] = "unknown"
        else:
            pkg["kind"] = (
                "direct"
                if normalize_name(pkg["name"]) in direct_names
                else "transitive"
            )

    note_parts = [p for p in (dep_note, *leftover_notes) if p]
    note = "; ".join(note_parts) if note_parts else None

    kinds_present = {pkg["kind"] for pkg in packages}
    if "transitive" in kinds_present or "unknown" in kinds_present:
        verdict = "STALE"
    elif "direct" in kinds_present:
        verdict = "DIRECT_ONLY"
    else:
        verdict = "CURRENT"

    direct_outdated = sum(1 for pkg in packages if pkg["kind"] == "direct")
    transitive_outdated = sum(1 for pkg in packages if pkg["kind"] == "transitive")

    return {
        "repo": repo_label,
        "repo_path": str(repo_path),
        "project": project_rel,
        "verdict": verdict,
        "dependabot_covered": dependabot_covered,
        "exclude_newer": exclude_newer,
        "note": note,
        "packages": [
            {
                "name": pkg["name"],
                "kind": pkg["kind"],
                "verdict": pkg["verdict"],
                "old": pkg["old"],
                "new": pkg["new"],
                "bump": pkg["bump"],
            }
            for pkg in packages
        ],
        "direct_outdated": direct_outdated,
        "transitive_outdated": transitive_outdated,
    }


def scan_repo(repo_label: str, repo_path: Path, timeout: int) -> list[dict[str, Any]]:
    """Scan a single repo for all uv.lock staleness findings."""
    lock_paths = find_uv_locks(repo_label, repo_path)
    if not lock_paths:
        return []

    covered_dirs = dependabot_covered_dirs(repo_path)
    return [
        check_project(repo_label, repo_path, lock_path.parent, timeout, covered_dirs)
        for lock_path in lock_paths
    ]


# --- Report ----------------------------------------------------------------


def _row_cells(pkg: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return (old, arrow, new, bump) display cells for one package row."""
    if pkg["verdict"] == "ADDED":
        return "(added)", "", pkg["new"] or "", ""
    if pkg["verdict"] == "REMOVED":
        return "(removed)", "", pkg["old"] or "", ""
    return pkg["old"] or "", "->", pkg["new"] or "", pkg["bump"] or ""


def format_package_rows(
    packages: list[dict[str, Any]], dependabot_covered: bool
) -> list[str]:
    """Format package rows for one project, column-aligned within the group."""
    if not packages:
        return []

    kind_w = max(len(pkg["kind"]) for pkg in packages)
    name_w = max(len(pkg["name"]) for pkg in packages)
    cells = [_row_cells(pkg) for pkg in packages]
    old_w = max(len(c[0]) for c in cells)
    new_w = max(len(c[2]) for c in cells)

    lines: list[str] = []
    for pkg, (old, arrow, new, bump) in zip(packages, cells):
        suffix = (
            "  [dependabot-covered]"
            if pkg["kind"] == "direct" and dependabot_covered
            else ""
        )
        lines.append(
            f"    {pkg['kind']:<{kind_w}}  {pkg['name']:<{name_w}}  "
            f"{old:<{old_w}}  {arrow:<2}  {new:<{new_w}}  {bump}".rstrip()
            + suffix
        )
    return lines


def print_human_report(
    projects: list[dict[str, Any]], show_all: bool, transitive_only: bool
) -> None:
    """Print the grouped, human-readable report to stdout."""
    if not projects:
        print("No uv.lock files found.")
        return

    by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for project in projects:
        by_repo[project["repo"]].append(project)

    def repo_sort_key(name: str) -> tuple[int, str]:
        return (0, "") if name == "home" else (1, name)

    for repo in sorted(by_repo, key=repo_sort_key):
        repo_projects = sorted(by_repo[repo], key=lambda p: p["project"])
        visible = [p for p in repo_projects if show_all or p["verdict"] != "CURRENT"]
        if not visible:
            continue

        print(repo)
        for project in visible:
            packages = project["packages"]
            transitive = sorted(
                (p for p in packages if p["kind"] == "transitive"),
                key=lambda p: p["name"],
            )
            unknown = sorted(
                (p for p in packages if p["kind"] == "unknown"), key=lambda p: p["name"]
            )
            direct = sorted(
                (p for p in packages if p["kind"] == "direct"), key=lambda p: p["name"]
            )

            counts = []
            if transitive:
                counts.append(f"{len(transitive)} transitive")
            if unknown:
                counts.append(f"{len(unknown)} unknown")
            if direct:
                counts.append(f"{len(direct)} direct")
            count_str = f"  ({', '.join(counts)})" if counts else ""

            tags = []
            if project["dependabot_covered"]:
                tags.append("[dependabot-covered]")
            if project["exclude_newer"]:
                tags.append(f"(exclude-newer {project['exclude_newer']})")
            tag_str = "  " + "  ".join(tags) if tags else ""

            print(f"  {project['project']}  {project['verdict']}{count_str}{tag_str}")
            if project["note"]:
                print(f"    note: {project['note']}")

            ordered = (
                transitive + unknown
                if transitive_only
                else transitive + unknown + direct
            )
            for line in format_package_rows(ordered, project["dependabot_covered"]):
                print(line)
        print()

    total_projects = len(projects)
    verdict_counts: dict[str, int] = defaultdict(int)
    total_transitive = 0
    total_direct = 0
    for project in projects:
        verdict_counts[project["verdict"]] += 1
        total_transitive += project["transitive_outdated"]
        total_direct += project["direct_outdated"]

    print(f"Total: {total_projects} project(s) scanned")
    for verdict_name in VERDICT_PRECEDENCE:
        if verdict_counts[verdict_name]:
            print(f"  {verdict_name}: {verdict_counts[verdict_name]}")
    print(f"  transitive outdated: {total_transitive}")
    print(f"  direct outdated: {total_direct}")
    print()
    print(
        "This script changes nothing. To refresh a lock, run "
        "`uv lock --upgrade` in the project directory."
    )


# --- Main scan ---------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--git-root",
        default=str(Path.home() / "git"),
        help="Root directory containing repo clones (default: ~/git).",
    )
    parser.add_argument(
        "--repo",
        action="append",
        metavar="NAME",
        help="Limit the scan to this repo by directory name "
        '("home" selects the home repo). Repeatable.',
    )
    parser.add_argument(
        "--no-home",
        action="store_true",
        help="Skip scanning the home-folder repo.",
    )
    parser.add_argument(
        "--owner",
        default="ryanspletzer",
        help="Only scan repos whose origin remote belongs to this GitHub "
        "owner (default: ryanspletzer).",
    )
    parser.add_argument(
        "--all-repos",
        action="store_true",
        help="Scan every repo regardless of origin owner.",
    )
    parser.add_argument(
        "--transitive-only",
        action="store_true",
        help="Omit direct-dependency entries from the human report.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include CURRENT projects in the human report.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Per-project uv timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON object per project instead of a human-readable report.",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point: scan repos for stale uv.lock files and print the report."""
    args = parse_args()

    if shutil.which("uv") is None:
        print("error: `uv` CLI not found on PATH", file=sys.stderr)
        sys.exit(1)

    git_root = Path(args.git_root).expanduser()
    repo_filter = set(args.repo) if args.repo else None
    include_home = not args.no_home and (repo_filter is None or "home" in repo_filter)

    owner = None if args.all_repos else args.owner
    repos = discover_repos(git_root, include_home, repo_filter, owner)

    projects: list[dict[str, Any]] = []
    for repo_label, repo_path in repos:
        projects.extend(scan_repo(repo_label, repo_path, args.timeout))

    if args.json:
        projects_sorted = sorted(projects, key=lambda p: (p["repo"], p["project"]))
        print(json.dumps(projects_sorted, indent=2))
        return

    print_human_report(projects, args.all, args.transitive_only)


if __name__ == "__main__":
    main()
