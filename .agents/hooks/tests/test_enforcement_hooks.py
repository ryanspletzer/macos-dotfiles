"""Exit-code contract for the uv/pip/pipx/venv enforcement hooks.

Exit 2 + a stderr hint blocks the tool call; exit 0 lets it through.
"""

import pytest
from _harness import bash, run_hook

BLOCKED = [
    ("check-pip-install.py", "pip install requests", "uv pip install"),
    ("check-pip-install.py", "pip3 install requests", "uv pip install"),
    ("check-pip-install.py", "pip3.12 install requests", "uv pip install"),
    ("check-pipx.py", "pipx run black .", "uvx"),
    ("check-pipx.py", "pipx install poetry", "uv tool install"),
    ("check-pipx.py", "pipx list", "pipx"),
    ("check-uv-venv.py", "python -m venv .venv", "uv venv"),
    ("check-uv-venv.py", "python3 -m venv .venv", "uv venv"),
    ("check-uv-venv.py", "python3.12 -m venv env", "uv venv"),
    ("check-uv-venv.py", "virtualenv env", "uv venv"),
    ("check-uv-pytest.py", "pytest tests/", "uv run pytest"),
    ("check-uv-pytest.py", "timeout 30 pytest -x", "uv run pytest"),
    ("check-uv-pytest.py", "python -m pytest", "uv run pytest"),
]

ALLOWED = [
    ("check-pip-install.py", "uv pip install requests"),
    ("check-pip-install.py", "uv add requests"),
    ("check-pip-install.py", "echo 'pip install requests'"),
    ("check-pip-install.py", "ls -la"),
    ("check-pipx.py", "uvx black ."),
    ("check-pipx.py", "uv tool install ruff"),
    ("check-pipx.py", "cat check-pipx.py"),
    ("check-uv-venv.py", "uv venv"),
    ("check-uv-venv.py", "python -m json.tool x.json"),
    ("check-uv-pytest.py", "uv run pytest tests/ -q"),
    # regression: mentioning the hook's own filename must not block
    ("check-uv-pytest.py", "cat ~/.agents/hooks/check-uv-pytest.py"),
    ("check-uv-pytest.py", "echo 'pytest is great'"),
]

HOOKS = sorted({hook for hook, *_ in BLOCKED})


@pytest.mark.parametrize("hook,command,hint", BLOCKED)
def test_blocks_with_hint(hook, command, hint):
    proc = run_hook(hook, bash(command))
    assert proc.returncode == 2
    assert hint in proc.stderr


@pytest.mark.parametrize("hook,command", ALLOWED)
def test_allows(hook, command):
    proc = run_hook(hook, bash(command))
    assert proc.returncode == 0
    assert proc.stderr == ""


@pytest.mark.parametrize("hook", HOOKS)
def test_ignores_non_bash_tools(hook):
    payload = {"tool_name": "Read", "tool_input": {"file_path": "/x"}}
    proc = run_hook(hook, payload)
    assert proc.returncode == 0
