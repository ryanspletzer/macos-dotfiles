"""Repo-wide markdownlint check over tracked Markdown files.

Runs from the repo root so markdownlint-cli2 discovers the tracked
.markdownlint.yaml configs (root and .claude/) correctly -- invoked
from a subdirectory it would silently fall back to defaults.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_markdownlint_clean():
    if shutil.which("markdownlint-cli2") is None:
        pytest.skip("markdownlint-cli2 not installed")
    files = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", "*.md"],
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.splitlines()
    proc = subprocess.run(
        ["markdownlint-cli2", *files],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
