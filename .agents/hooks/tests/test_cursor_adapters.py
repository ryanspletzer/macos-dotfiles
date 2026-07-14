"""Tests for the Cursor CLI adapters in adapters/.

The adapters bridge Cursor's hook dialect to the shared Claude/Codex
schema scripts, so these tests exercise the translation in both
directions: Cursor-shaped stdin in, Cursor-shaped decisions out.

The shell gate plays a deny sound via afplay; tests pass an empty
PATH so the lookup fails silently (the adapter catches it) while the
inner hook subprocesses still run via the absolute sys.executable.
"""

import json

import pytest
from _harness import run_hook

GATE = "adapters/cursor-shell-gate.py"
FILTER = "adapters/cursor-filter-tests.py"
CONTEXT = "adapters/cursor-session-context.py"

MUTED = {"PATH": ""}


def output(proc):
    assert proc.returncode == 0
    return json.loads(proc.stdout)


# --- cursor-shell-gate: beforeShellExecution -------------------------------

DENIED = [
    ("pip install requests", "uv pip install"),
    ("pipx run black .", "uvx"),
    ("python -m venv .venv", "uv venv"),
    ("timeout 30 pytest -x", "uv run pytest"),
    # a blocker fires on the chain even though approve-variants would
    # also reject it; deny wins over defer
    ("pip install requests && git status", "uv pip install"),
]

ALLOWED = [
    "git status",
    "ls -la && pwd",
    "command -v shellcheck",
]

DEFERRED = [
    "rm -rf /tmp/x",
    "sudo ls",
    "echo $(whoami)",
]


@pytest.mark.parametrize("command,hint", DENIED)
def test_gate_denies_blocked_commands(command, hint):
    out = output(run_hook(GATE, {"command": command}, env=MUTED))
    assert out["permission"] == "deny"
    assert hint in out["user_message"]
    assert hint in out["agent_message"]


@pytest.mark.parametrize("command", ALLOWED)
def test_gate_allows_safe_commands(command):
    out = output(run_hook(GATE, {"command": command}, env=MUTED))
    assert out["permission"] == "allow"
    assert out["agent_message"]


@pytest.mark.parametrize("command", DEFERRED)
def test_gate_defers_everything_else(command):
    out = output(run_hook(GATE, {"command": command}, env=MUTED))
    assert out == {}


def test_gate_defers_on_empty_command():
    assert output(run_hook(GATE, {"command": ""}, env=MUTED)) == {}


def test_gate_defers_on_malformed_json():
    assert output(run_hook(GATE, "not json", env=MUTED)) == {}


# --- cursor-filter-tests: preToolUse (Shell) --------------------------------


def test_filter_rewrites_simple_test_run():
    payload = {
        "tool_name": "Shell",
        "tool_input": {"command": "uv run pytest -q", "cwd": "/tmp"},
    }
    out = output(run_hook(FILTER, payload))
    assert out["permission"] == "allow"
    new_cmd = out["updated_input"]["command"]
    assert "( uv run pytest -q )" in new_cmd
    assert "exit $__rc" in new_cmd
    # other tool_input keys survive the rewrite
    assert out["updated_input"]["cwd"] == "/tmp"


@pytest.mark.parametrize(
    "payload",
    [
        {"tool_name": "Shell", "tool_input": {"command": "ls -la"}},
        {"tool_name": "Shell", "tool_input": {"command": "uv run pytest && echo done"}},
        {"tool_name": "Bash", "tool_input": {"command": "uv run pytest -q"}},
        {"tool_name": "Shell", "tool_input": {}},
    ],
    ids=["non-test-command", "chained", "wrong-tool-name", "no-command"],
)
def test_filter_passes_through(payload):
    assert output(run_hook(FILTER, payload)) == {}


def test_filter_passes_through_on_malformed_json():
    assert output(run_hook(FILTER, "not json")) == {}


# --- cursor-session-context: sessionStart -----------------------------------


def test_context_injects_agents_md(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Test Instructions\n\nBe excellent.\n")
    out = output(run_hook(CONTEXT, {}, env={"HOME": str(tmp_path)}))
    assert out["additional_context"] == "# Test Instructions\n\nBe excellent."


def test_context_empty_when_agents_md_missing(tmp_path):
    out = output(run_hook(CONTEXT, {}, env={"HOME": str(tmp_path)}))
    assert out == {}
