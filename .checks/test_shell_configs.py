"""Syntax, lint, and startup smoke tests for the shell configs.

Three layers:

- syntax: dialect parse checks (bash -n, zsh -n, fish --no-execute)
  over the tracked shell files
- lint: shellcheck over the bash-dialect files (policy in ~/.shellcheckrc)
- startup: launch each shell interactively the way a new terminal
  would, and assert exit 0 with no unexpected stderr

The startup tests source the real profiles on the live machine, so
they catch a broken edit before it breaks every new terminal. Known
benign no-tty artifacts are filtered from stderr before asserting.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

BASH_FILES = [".bashrc", ".bash_profile", ".profile"]
ZSH_FILES = [".zshrc", ".zshenv", ".zprofile", ".zshenv.personal", ".zshenv.work"]


def tracked(pattern):
    proc = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", pattern],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.splitlines()


FISH_FILES = tracked("*.fish")
SH_SCRIPTS = tracked("*.sh")


def run(cmd, timeout=60):
    return subprocess.run(
        cmd,
        cwd=REPO,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.mark.parametrize("path", BASH_FILES + SH_SCRIPTS)
def test_bash_dialect_syntax(path):
    proc = run(["bash", "-n", path])
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("path", ZSH_FILES)
def test_zsh_syntax(path):
    proc = run(["zsh", "-n", path])
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("path", FISH_FILES)
def test_fish_syntax(path):
    proc = run(["fish", "--no-execute", path])
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("path", BASH_FILES)
def test_shellcheck_dotfiles(path):
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck not installed")
    proc = run(["shellcheck", "--shell=bash", path])
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize("path", SH_SCRIPTS)
def test_shellcheck_scripts(path):
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck not installed")
    proc = run(["shellcheck", path])  # dialect from each script's shebang
    assert proc.returncode == 0, proc.stdout


# Interactive startup without a tty produces some unavoidable noise;
# anything on stderr beyond these patterns fails the test.
BENIGN_STARTUP_NOISE = {
    "bash": re.compile(
        r"cannot set terminal process group"
        r"|no job control in this shell"
        r"|^exit$"
    ),
    "zsh": re.compile(r"can't change option: zle"),
}

STARTUP_COMMANDS = [
    ("bash", ["bash", "-ic", "exit 0"]),
    ("zsh", ["zsh", "-ic", "exit 0"]),
    ("fish", ["fish", "-ic", "exit 0"]),
    ("pwsh", ["pwsh", "-NoLogo", "-Command", "exit 0"]),
]


@pytest.mark.parametrize(
    "shell,cmd", STARTUP_COMMANDS, ids=[shell for shell, _ in STARTUP_COMMANDS]
)
@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="startup sources ~ profiles, which target this machine's toolchain",
)
def test_interactive_startup(shell, cmd):
    if shutil.which(cmd[0]) is None:
        pytest.skip(f"{cmd[0]} not installed")
    proc = run(cmd)
    assert proc.returncode == 0, (
        f"{shell} startup exited {proc.returncode}; stderr:\n{proc.stderr}"
    )
    noise = BENIGN_STARTUP_NOISE.get(shell)
    unexpected = [
        line
        for line in proc.stderr.splitlines()
        if line.strip() and not (noise and noise.search(line))
    ]
    assert unexpected == [], (
        f"unexpected stderr during {shell} startup: {unexpected}"
    )
