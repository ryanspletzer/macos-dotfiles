"""Canary tests for the ignore-everything-then-unignore .gitignore.

This home-folder repo ignores everything by default, selectively
un-ignores tracked configs, and pushes to a public GitHub repo. One
wrong negation could start tracking secrets. These tests pin down both
directions:

- sensitive paths (which need not exist) must match an ignore rule
- core tracked configs must stay un-ignored and tracked

check-ignore runs with --no-index so the assertions test pattern
semantics even for paths that are tracked or nonexistent.

Deliberate policy (decided 2026-07-14): .config/powershell/ and
.config/fish/ stay un-ignored wholesale so that NEW config in them
surfaces as visible untracked files rather than being silently
ignored -- neither shell writes history or credentials into .config
(both use ~/.local/share). The fisher-managed fish paths, which are
regenerated from fish_plugins and would only add noise, are the
targeted exception and are pinned ignored below.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


MUST_STAY_IGNORED = [
    # keys and cloud credentials
    ".ssh/id_ed25519",
    ".ssh/config",
    ".aws/credentials",
    ".gnupg/private-keys-v1.d/key.key",
    ".gnupg/pubring.kbx",
    ".gnupg/trustdb.gpg",
    ".kube/config",
    ".docker/config.json",
    ".config/gh/hosts.yml",
    "Library/Keychains/login.keychain-db",
    # shell and REPL histories
    ".zsh_history",
    ".bash_history",
    ".python_history",
    ".lesshst",
    # secrets-bearing dotfiles
    ".netrc",
    ".env",
    ".envrc",
    ".pgpass",
    # per-machine Git identity/credentials: gitignored so work email and
    # enterprise hosts never enter the public tree
    ".gitconfig.local",
    ".gitconfig.personal",
    ".gitconfig.work",
    # agent-CLI state: sessions, auth, machine-local overrides
    ".claude/.credentials.json",
    ".claude/history.jsonl",
    ".claude/projects/x/session.jsonl",
    ".claude/settings.local.json",
    ".codex/auth.json",
    ".cursor/auth.json",
    ".copilot/auth.json",
    # fisher-managed fish files: regenerated from fish_plugins, never tracked
    ".config/fish/functions/anything.fish",
    ".config/fish/completions/anything.fish",
    ".config/fish/conf.d/nvm.fish",
    # everything else in $HOME stays out by default
    "Documents/private.txt",
]

MUST_STAY_TRACKED = [
    ".zshrc",
    ".bashrc",
    ".bash_profile",
    ".zshenv",
    ".profile",
    ".gitconfig",
    ".gitconfig.local.example",
    ".gitignore",
    ".tmux.conf",
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/hooks/approve-variants.py",
    ".agents/hooks/tests/_harness.py",
    ".checks/test_gitignore_canaries.py",
    ".claude/settings.json",
    ".claude/CLAUDE.md",
    ".codex/config.toml",
    ".cursor/hooks.json",
    ".copilot/settings.json",
    ".config/fish/config.fish",
    ".config/fish/fish_plugins",
    ".config/powershell/Microsoft.PowerShell_profile.ps1",
    ".config/powershell/PSScriptAnalyzerSettings.psd1",
    ".config/powershell/Modules/Profile/1.0.0/Profile.Tests.ps1",
    ".gnupg/gpg.conf",
    ".oh-my-posh/themes/claude-statusline.yaml",
    "Library/Application Support/Code/User/settings.json",
]


@pytest.mark.parametrize("path", MUST_STAY_IGNORED)
def test_sensitive_path_is_ignored(path):
    proc = git("check-ignore", "--no-index", "-q", "--", path)
    assert proc.returncode == 0, (
        f"{path} does not match any ignore rule — a file there would be trackable"
    )


@pytest.mark.parametrize("path", MUST_STAY_TRACKED)
def test_config_stays_unignored(path):
    proc = git("check-ignore", "--no-index", "-q", "--", path)
    assert proc.returncode == 1, (
        f"{path} matches an ignore rule — a fresh copy would be dropped from the repo"
    )


@pytest.mark.parametrize("path", MUST_STAY_TRACKED)
def test_config_is_tracked(path):
    proc = git("ls-files", "--error-unmatch", "--", path)
    assert proc.returncode == 0, f"{path} is not tracked"


SUSPICIOUS_NAME = re.compile(
    r"(id_rsa|id_ed25519|id_ecdsa|\.pem$|\.p12$|\.key$"
    r"|credential|secret|token|_history|\.env$)",
    re.IGNORECASE,
)


def test_no_suspicious_tracked_filenames():
    tracked = git("ls-files").stdout.splitlines()
    flagged = [f for f in tracked if SUSPICIOUS_NAME.search(f)]
    assert flagged == [], f"suspiciously named tracked files: {flagged}"
