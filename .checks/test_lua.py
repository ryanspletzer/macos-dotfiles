"""stylua format check over the nvim Lua config.

Runs from .config/nvim so stylua discovers the tracked stylua.toml.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

NVIM_DIR = Path(__file__).resolve().parent.parent / ".config/nvim"


def test_stylua_clean():
    if shutil.which("stylua") is None:
        pytest.skip("stylua not installed")
    proc = subprocess.run(
        ["stylua", "--check", "."],
        cwd=NVIM_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
