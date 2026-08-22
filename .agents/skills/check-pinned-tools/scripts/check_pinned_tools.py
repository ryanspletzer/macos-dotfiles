#!/usr/bin/env python3
"""Find pinned tool versions in local repo clones and check them for staleness.

Scans every repo under a git root (plus the user's home-folder repo) for
GitHub Actions workflow files, `.pre-commit-config.yaml`, and
`pyproject.toml`/`uv.toml`, extracts pinned versions that Dependabot doesn't
manage or lags on (action SHA/tag pins, the uv version pin, the
`UV_EXCLUDE_NEWER` freshness date, and pre-commit hook revs), resolves the
latest upstream release for each via `gh api`, and prints a deterministic
report. This script is read-only: it never writes files, runs git, or
mutates anything.

Usage:
  check_pinned_tools.py [--git-root PATH] [--repo NAME ...] [--no-home]
                         [--owner NAME] [--all-repos]
                         [--all] [--json] [--stale-days N]

  --git-root    Root directory containing repo clones (default: ~/git).
  --repo        Limit the scan to this repo (by directory name; "home"
                selects the home repo). Repeatable, and overrides the
                owner filter.
  --no-home     Skip scanning the home-folder repo.
  --owner       Only scan repos whose origin remote belongs to this
                GitHub owner (default: ryanspletzer). Clones of other
                people's repos are skipped.
  --all-repos   Scan every repo regardless of origin owner.
  --all         Include CURRENT findings in the human report (JSON always
                includes everything).
  --json        Emit the full findings list as a JSON array instead of a
                human-readable report.
  --stale-days  Days after which an UV_EXCLUDE_NEWER/exclude-newer date is
                considered stale (default: 30).
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# --- Regexes -----------------------------------------------------------------

ACTION_USES_RE = re.compile(
    r"^\s*(?:-\s+)?uses:\s*([^@\s]+)@(\S+)(\s*#.*)?\s*$"
)
VERSION_COMMENT_RE = re.compile(r"^([vV]?\d+(?:\.\d+)*)\b")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")

SETUP_UV_USES_RE = re.compile(
    r"^(\s*(?:-\s+)?uses:\s*astral-sh/setup-uv@)(\S+)(\s*#.*)?$"
)
UV_VERSION_RE = re.compile(r'^\s*UV_VERSION:\s*["\']?(\d+\.\d+\.\d+)')
WITH_VERSION_RE = re.compile(r'^\s*version:\s*["\']?(\d+\.\d+\.\d+)')

WORKFLOW_EXCLUDE_NEWER_RE = re.compile(
    r'^\s*UV_EXCLUDE_NEWER:\s*["\']?(\d{4}-\d{2}-\d{2})'
)
TOML_EXCLUDE_NEWER_RE = re.compile(
    r'^\s*exclude-newer\s*=\s*["\'](\d{4}-\d{2}-\d{2})'
)

PRECOMMIT_REPO_RE = re.compile(r"^\s*-?\s*repo:\s*(\S+)\s*$")
PRECOMMIT_REV_RE = re.compile(r"^\s*rev:\s*(\S+)\s*$")
GITHUB_REPO_URL_RE = re.compile(
    r"^https://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?$"
)

DEPENDABOT_ACTIONS_RE = re.compile(
    r'package-ecosystem:\s*["\']?github-actions'
)

VERDICT_PRECEDENCE = ["OUTDATED", "SHA_MISMATCH", "STALE", "UNKNOWN", "CURRENT"]

# Set on the first `gh` call's failure so later calls know auth was already
# confirmed working (or the process already exited).
_FIRST_GH_CALL_DONE = False


# --- gh invocation -------------------------------------------------------


def run_gh(args: list[str]) -> str | None:
    """Run `gh` with the given args, returning stripped stdout or None.

    The very first `gh` call of the run is special-cased: if it fails and
    the failure looks like an auth problem (or `gh` is missing entirely),
    print the error and exit immediately so auth issues are obvious. Every
    later call just yields None on failure, since a single unresolved
    version shouldn't stop the whole scan.
    """
    global _FIRST_GH_CALL_DONE
    is_first_call = not _FIRST_GH_CALL_DONE
    try:
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True
        )
    except FileNotFoundError:
        if is_first_call:
            print("error: `gh` CLI not found on PATH", file=sys.stderr)
            sys.exit(1)
        return None
    finally:
        _FIRST_GH_CALL_DONE = True

    if result.returncode != 0:
        if is_first_call and _looks_like_auth_error(result.stderr):
            print(result.stderr, file=sys.stderr, end="")
            sys.exit(1)
        return None
    return result.stdout.strip()


def _looks_like_auth_error(stderr: str) -> bool:
    """True if gh's stderr suggests an authentication problem."""
    lowered = stderr.lower()
    return any(
        needle in lowered
        for needle in ("auth", "not logged in", "authentication", "credentials")
    )


# --- Version parsing and comparison ---------------------------------------


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


def compare_versions(
    pinned: tuple[int, ...], latest: tuple[int, ...], major_only: bool = False
) -> tuple[str, str]:
    """Compare a pinned version tuple against latest; return (verdict, note)."""
    if major_only:
        pinned_major = pinned[0] if pinned else None
        latest_major = latest[0] if latest else None
        if pinned_major == latest_major:
            return "CURRENT", ""
        if pinned_major is not None and latest_major is not None:
            if pinned_major < latest_major:
                return "OUTDATED", ""
            return "CURRENT", "ahead of latest release"
        return "UNKNOWN", ""

    if pinned < latest:
        return "OUTDATED", ""
    if pinned == latest:
        return "CURRENT", ""
    return "CURRENT", "ahead of latest release"


# --- Shared owner/repo release & tag resolver -------------------------------


class ReleaseResolver:
    """Caches latest-release/tag lookups for owner/repo pairs across kinds."""

    def __init__(self) -> None:
        self._latest_tag: dict[tuple[str, str], str | None] = {}
        self._latest_tag_sha: dict[tuple[str, str], str | None] = {}

    def latest_tag(self, owner: str, repo: str) -> str | None:
        """Return the latest release tag_name for owner/repo, or None."""
        key = (owner, repo)
        if key in self._latest_tag:
            return self._latest_tag[key]

        tag = run_gh(
            ["api", f"repos/{owner}/{repo}/releases/latest", "--jq", ".tag_name"]
        )
        # Fall back to the tag list when there is no latest release, or when
        # the latest release's tag isn't a plain version (e.g. codeql-action's
        # codeql-bundle-vX.Y.Z releases, which don't match the vN action tags).
        if not tag or not re.match(r"^[vV]?\d+(\.\d+)*$", tag):
            tags_out = run_gh(
                ["api", f"repos/{owner}/{repo}/tags", "--jq", ".[].name"]
            )
            fallback = self._pick_highest_tag(tags_out) if tags_out else None
            tag = fallback or tag or None

        self._latest_tag[key] = tag
        return tag

    @staticmethod
    def _pick_highest_tag(tags_out: str) -> str | None:
        """Pick the highest version among tags matching ^[vV]?\\d+(\\.\\d+)*$."""
        candidates: list[tuple[tuple[int, ...], str]] = []
        for line in tags_out.splitlines():
            line = line.strip()
            if not line:
                continue
            if not re.match(r"^[vV]?\d+(\.\d+)*$", line):
                continue
            version = parse_version(line)
            if version is not None:
                candidates.append((version, line))
        if not candidates:
            return None
        candidates.sort(key=lambda pair: pair[0])
        return candidates[-1][1]

    def latest_tag_sha(self, owner: str, repo: str) -> str | None:
        """Return the commit SHA the latest release tag points at, or None."""
        key = (owner, repo)
        if key in self._latest_tag_sha:
            return self._latest_tag_sha[key]

        sha: str | None = None
        tag = self.latest_tag(owner, repo)
        if tag:
            ref_out = run_gh(
                [
                    "api",
                    f"repos/{owner}/{repo}/git/ref/tags/{tag}",
                    "--jq",
                    '.object.type + " " + .object.sha',
                ]
            )
            if ref_out and " " in ref_out:
                obj_type, obj_sha = ref_out.split(" ", 1)
                if obj_type == "tag":
                    obj_sha = run_gh(
                        [
                            "api",
                            f"repos/{owner}/{repo}/git/tags/{obj_sha}",
                            "--jq",
                            ".object.sha",
                        ]
                    )
                sha = obj_sha or None

        self._latest_tag_sha[key] = sha
        return sha


# --- Repo discovery ----------------------------------------------------------

GITHUB_REMOTE_OWNER_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)([^/\s]+)/"
)


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


def workflow_files(repo_path: Path) -> list[Path]:
    """Return sorted workflow YAML files under .github/workflows."""
    wf_dir = repo_path / ".github" / "workflows"
    if not wf_dir.is_dir():
        return []
    files = list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))
    return sorted(files)


def is_dependabot_covered(repo_path: Path) -> bool:
    """True if the repo's dependabot config covers the github-actions ecosystem."""
    for name in ("dependabot.yml", "dependabot.yaml"):
        path = repo_path / ".github" / name
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            if DEPENDABOT_ACTIONS_RE.search(line):
                return True
    return False


# --- action-pin check --------------------------------------------------------


def _parse_version_comment(comment: str | None) -> str | None:
    """Extract the first '#'-delimited token if it looks like a version."""
    if not comment:
        return None
    # Split into '#'-delimited segments; the first non-empty one is the
    # version comment candidate (trailing comments like a zizmor ignore
    # directive come after it, in a later '#' segment).
    segments = comment.split("#")
    for segment in segments:
        token = segment.strip().split()[0] if segment.strip() else ""
        if not token:
            continue
        if VERSION_COMMENT_RE.match(token):
            return token
        return None
    return None


def check_action_pins(
    repo_label: str,
    repo_path: Path,
    file_path: Path,
    lines: list[str],
    resolver: ReleaseResolver,
    dependabot_covered: bool,
) -> list[dict[str, Any]]:
    """Find and evaluate `uses: owner/repo[/subpath]@ref` pins in a workflow."""
    findings: list[dict[str, Any]] = []
    rel_file = str(file_path.relative_to(repo_path))

    for lineno, line in enumerate(lines, start=1):
        m = ACTION_USES_RE.match(line)
        if not m:
            continue
        target, ref, comment = m.group(1), m.group(2), m.group(3)

        if target.startswith("./") or target.startswith("docker://"):
            continue

        parts = target.split("/")
        if len(parts) < 2:
            continue
        owner, repo_name = parts[0], parts[1]
        name = f"{owner}/{repo_name}"

        version_comment = _parse_version_comment(comment)
        latest_tag = resolver.latest_tag(owner, repo_name)
        latest_version = parse_version(latest_tag) if latest_tag else None

        if SHA_RE.match(ref):
            verdict, latest, note = _evaluate_sha_pin(
                owner, repo_name, ref, version_comment, latest_tag,
                latest_version, resolver,
            )
            current = ref if not version_comment else f"{ref} # {version_comment}"
        else:
            verdict, latest, note = _evaluate_tag_pin(
                ref, latest_tag, latest_version
            )
            current = ref

        findings.append(
            {
                "repo": repo_label,
                "file": rel_file,
                "line": lineno,
                "kind": "action-pin",
                "name": name,
                "current": current,
                "latest": latest if latest is not None else "unknown",
                "verdict": verdict,
                "note": note,
                "dependabot_covered": dependabot_covered,
            }
        )

    return findings


def _evaluate_sha_pin(
    owner: str,
    repo_name: str,
    sha: str,
    version_comment: str | None,
    latest_tag: str | None,
    latest_version: tuple[int, ...] | None,
    resolver: ReleaseResolver,
) -> tuple[str, str | None, str]:
    """Evaluate a 40-hex-SHA action pin; returns (verdict, latest, note)."""
    if latest_tag is None:
        return "UNKNOWN", None, "could not resolve latest release"

    latest_sha = resolver.latest_tag_sha(owner, repo_name)

    if latest_sha and sha.lower() == latest_sha.lower():
        return "CURRENT", latest_tag, ""

    comment_version = parse_version(version_comment) if version_comment else None
    if comment_version is not None and latest_version is not None:
        if comment_version < latest_version:
            return "OUTDATED", latest_tag, ""
        if comment_version > latest_version:
            return "CURRENT", latest_tag, "ahead of latest release"
        if latest_sha is None:
            return "UNKNOWN", latest_tag, "could not resolve latest tag commit"
        return (
            "SHA_MISMATCH",
            latest_tag,
            "version comment matches latest tag but SHA does not",
        )

    if version_comment is None:
        return "UNKNOWN", latest_tag, "sha pin without version comment"

    return "UNKNOWN", latest_tag, ""


def _evaluate_tag_pin(
    ref: str, latest_tag: str | None, latest_version: tuple[int, ...] | None
) -> tuple[str, str | None, str]:
    """Evaluate a tag/branch action pin; returns (verdict, latest, note)."""
    if ref in ("main", "master") or not VERSION_COMMENT_RE.match(ref):
        return "UNKNOWN", latest_tag, "unpinned branch ref"

    if latest_tag is None or latest_version is None:
        return "UNKNOWN", None, "could not resolve latest release"

    pinned_version = parse_version(ref)
    if pinned_version is None:
        return "UNKNOWN", latest_tag, ""

    major_only = ref.lstrip("vV").count(".") == 0
    verdict, note = compare_versions(pinned_version, latest_version, major_only)
    return verdict, latest_tag, note


# --- uv-version check ---------------------------------------------------


def check_uv_versions(
    repo_label: str,
    repo_path: Path,
    file_path: Path,
    lines: list[str],
    latest_uv_version: str | None,
) -> list[dict[str, Any]]:
    """Find UV_VERSION env pins and setup-uv `version:` inputs."""
    findings: list[dict[str, Any]] = []
    rel_file = str(file_path.relative_to(repo_path))
    latest_tuple = parse_version(latest_uv_version) if latest_uv_version else None

    in_setup_uv = False
    for lineno, line in enumerate(lines, start=1):
        if SETUP_UV_USES_RE.match(line):
            in_setup_uv = True
            continue

        if in_setup_uv and line.strip() and _clears_setup_uv_block(line):
            in_setup_uv = False

        pinned: str | None = None
        m = UV_VERSION_RE.match(line)
        if m:
            pinned = m.group(1)
        elif in_setup_uv:
            m = WITH_VERSION_RE.match(line)
            if m:
                pinned = m.group(1)

        if pinned is None:
            continue

        if latest_tuple is None:
            verdict, note = "UNKNOWN", "could not resolve latest uv release"
        else:
            pinned_tuple = parse_version(pinned)
            if pinned_tuple is None:
                verdict, note = "UNKNOWN", ""
            else:
                verdict, note = compare_versions(pinned_tuple, latest_tuple)

        findings.append(
            {
                "repo": repo_label,
                "file": rel_file,
                "line": lineno,
                "kind": "uv-version",
                "name": "uv",
                "current": pinned,
                "latest": latest_uv_version if latest_uv_version else "unknown",
                "verdict": verdict,
                "note": note,
                "dependabot_covered": False,
            }
        )

    return findings


def _clears_setup_uv_block(line: str) -> bool:
    """True if this (non-uses) line ends a setup-uv step block."""
    if re.match(r"^\s*-\s", line):
        return True
    if line == line.lstrip():
        return True
    if "uses:" in line:
        return True
    return False


# --- exclude-newer check -------------------------------------------------


def check_exclude_newer(
    repo_label: str,
    repo_path: Path,
    file_path: Path,
    lines: list[str],
    pattern: re.Pattern[str],
    name: str,
    stale_days: int,
    today: datetime.date,
) -> list[dict[str, Any]]:
    """Find UV_EXCLUDE_NEWER / exclude-newer date pins and check staleness."""
    findings: list[dict[str, Any]] = []
    rel_file = str(file_path.relative_to(repo_path))
    today_iso = today.isoformat()

    for lineno, line in enumerate(lines, start=1):
        m = pattern.match(line)
        if not m:
            continue
        date_str = m.group(1)
        try:
            pinned_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            continue

        age_days = (today - pinned_date).days
        if age_days > stale_days:
            verdict = "STALE"
        else:
            verdict = "CURRENT"
        note = f"{age_days} day(s) old"

        findings.append(
            {
                "repo": repo_label,
                "file": rel_file,
                "line": lineno,
                "kind": "exclude-newer",
                "name": name,
                "current": date_str,
                "latest": today_iso,
                "verdict": verdict,
                "note": note,
                "dependabot_covered": False,
            }
        )

    return findings


# --- precommit-rev check -------------------------------------------------


def check_precommit(
    repo_label: str,
    repo_path: Path,
    resolver: ReleaseResolver,
) -> list[dict[str, Any]]:
    """Parse .pre-commit-config.yaml and check each hook's rev for staleness."""
    file_path = repo_path / ".pre-commit-config.yaml"
    if not file_path.is_file():
        return []

    try:
        lines = file_path.read_text().splitlines()
    except OSError:
        return []

    findings: list[dict[str, Any]] = []
    rel_file = str(file_path.relative_to(repo_path))
    current_repo_url: str | None = None

    for lineno, line in enumerate(lines, start=1):
        repo_m = PRECOMMIT_REPO_RE.match(line)
        if repo_m:
            value = repo_m.group(1)
            if value in ("local", "meta"):
                current_repo_url = None
            else:
                current_repo_url = value
            continue

        rev_m = PRECOMMIT_REV_RE.match(line)
        if not rev_m or current_repo_url is None:
            continue

        rev = rev_m.group(1)
        url_m = GITHUB_REPO_URL_RE.match(current_repo_url)
        if not url_m:
            continue
        owner, repo_name = url_m.group(1), url_m.group(2)
        name = f"{owner}/{repo_name}"

        latest_tag = resolver.latest_tag(owner, repo_name)
        verdict, latest, note = _evaluate_precommit_rev(rev, latest_tag)

        findings.append(
            {
                "repo": repo_label,
                "file": rel_file,
                "line": lineno,
                "kind": "precommit-rev",
                "name": name,
                "current": rev,
                "latest": latest if latest is not None else "unknown",
                "verdict": verdict,
                "note": note,
                "dependabot_covered": False,
            }
        )

    return findings


def _evaluate_precommit_rev(
    rev: str, latest_tag: str | None
) -> tuple[str, str | None, str]:
    """Evaluate a pre-commit hook rev; returns (verdict, latest, note)."""
    if latest_tag is None:
        return "UNKNOWN", None, "could not resolve latest release"

    rev_version = parse_version(rev)
    latest_version = parse_version(latest_tag)

    if rev_version is None or latest_version is None:
        if rev == latest_tag:
            return "CURRENT", latest_tag, ""
        return "UNKNOWN", latest_tag, ""

    verdict, note = compare_versions(rev_version, latest_version)
    return verdict, latest_tag, note


# --- Report ----------------------------------------------------------------


def print_human_report(
    findings: list[dict[str, Any]], show_all: bool, stale_days: int
) -> None:
    """Print the grouped, human-readable report to stdout."""
    by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        by_repo[finding["repo"]].append(finding)

    def repo_sort_key(name: str) -> tuple[int, str]:
        return (0, "") if name == "home" else (1, name)

    for repo in sorted(by_repo, key=repo_sort_key):
        repo_findings = sorted(
            by_repo[repo], key=lambda f: (f["file"], f["line"])
        )
        visible = [
            f for f in repo_findings if show_all or f["verdict"] != "CURRENT"
        ]
        if not visible:
            continue
        print(repo)
        for finding in visible:
            suffix = (
                " [dependabot-covered]" if finding["dependabot_covered"] else ""
            )
            print(
                f"  {finding['file']}:{finding['line']}"
                f"  {finding['kind'].upper()}  {finding['name']}"
                f"  {finding['current']} -> {finding['latest']}"
                f"  {finding['verdict']}{suffix}"
            )
            if finding["note"]:
                print(f"    {finding['note']}")
        print()

    counts = Counter(f["verdict"] for f in findings)
    print(f"Total: {len(findings)} pin(s) checked")
    for verdict_name in VERDICT_PRECEDENCE:
        if counts[verdict_name]:
            print(f"  {verdict_name}: {counts[verdict_name]}")

    problems = sum(
        counts[v] for v in ("OUTDATED", "SHA_MISMATCH", "STALE")
    )
    if problems == 0:
        print()
        print("Everything is current.")


# --- Main scan ---------------------------------------------------------------


def scan_repo(
    repo_label: str,
    repo_path: Path,
    resolver: ReleaseResolver,
    uv_resolver_cache: dict[str, str | None],
    stale_days: int,
    today: datetime.date,
) -> list[dict[str, Any]]:
    """Scan a single repo for all pinned-tool findings."""
    findings: list[dict[str, Any]] = []
    dependabot_covered = is_dependabot_covered(repo_path)

    if "uv" not in uv_resolver_cache:
        uv_resolver_cache["uv"] = resolver.latest_tag("astral-sh", "uv")
    latest_uv_tag = uv_resolver_cache["uv"]
    latest_uv_version = (
        latest_uv_tag[1:] if latest_uv_tag and latest_uv_tag.startswith("v")
        else latest_uv_tag
    )

    for wf_path in workflow_files(repo_path):
        try:
            lines = wf_path.read_text().splitlines()
        except OSError:
            continue

        findings.extend(
            check_action_pins(
                repo_label, repo_path, wf_path, lines, resolver,
                dependabot_covered,
            )
        )
        findings.extend(
            check_uv_versions(
                repo_label, repo_path, wf_path, lines, latest_uv_version
            )
        )
        findings.extend(
            check_exclude_newer(
                repo_label, repo_path, wf_path, lines,
                WORKFLOW_EXCLUDE_NEWER_RE, "UV_EXCLUDE_NEWER", stale_days, today,
            )
        )

    for toml_name in ("pyproject.toml", "uv.toml"):
        toml_path = repo_path / toml_name
        if not toml_path.is_file():
            continue
        try:
            lines = toml_path.read_text().splitlines()
        except OSError:
            continue
        findings.extend(
            check_exclude_newer(
                repo_label, repo_path, toml_path, lines,
                TOML_EXCLUDE_NEWER_RE, "exclude-newer", stale_days, today,
            )
        )

    findings.extend(check_precommit(repo_label, repo_path, resolver))

    return findings


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
        "--all",
        action="store_true",
        help="Include CURRENT findings in the human report.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full findings list as a JSON array.",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=30,
        help="Days after which an exclude-newer date is stale (default: 30).",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point: scan repos for pinned tool versions and print the report."""
    args = parse_args()

    git_root = Path(args.git_root).expanduser()
    repo_filter = set(args.repo) if args.repo else None
    include_home = not args.no_home and (
        repo_filter is None or "home" in repo_filter
    )

    owner = None if args.all_repos else args.owner
    repos = discover_repos(git_root, include_home, repo_filter, owner)

    resolver = ReleaseResolver()
    uv_resolver_cache: dict[str, str | None] = {}
    today = datetime.date.today()

    findings: list[dict[str, Any]] = []
    for repo_label, repo_path in repos:
        findings.extend(
            scan_repo(
                repo_label, repo_path, resolver, uv_resolver_cache,
                args.stale_days, today,
            )
        )

    if args.json:
        findings_sorted = sorted(
            findings, key=lambda f: (f["repo"], f["file"], f["line"])
        )
        print(json.dumps(findings_sorted, indent=2))
        return

    print_human_report(findings, args.all, args.stale_days)


if __name__ == "__main__":
    main()
