"""actionlint over the GitHub Actions workflows."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_actionlint_clean():
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint not installed")
    proc = subprocess.run(
        ["actionlint"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
