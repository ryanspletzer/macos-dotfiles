"""Shared helpers for hook tests: run a hook script as a real subprocess.

The hooks execute top-to-bottom on import (no main() guard), so subprocess
invocation with JSON on stdin exercises the exact contract Claude Code,
Codex, and Cursor use.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent


def bash(command):
    """Build the PreToolUse stdin payload for a Bash tool call."""
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def run_hook(hook_name, payload, env=None):
    """Run a hook script with the given payload on stdin.

    payload may be a dict (JSON-encoded) or a raw string (sent as-is,
    for malformed-input tests). env, when given, fully replaces the
    inherited environment (hooks only need sys.executable, which is
    absolute). Returns the CompletedProcess.
    """
    if not isinstance(payload, str):
        payload = json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / hook_name)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
