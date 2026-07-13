#!/usr/bin/env python3
"""Cursor CLI beforeShellExecution adapter for the shared enforcement hooks.

Bridges Cursor's hook dialect to the Claude/Codex-schema scripts in
~/.agents/hooks/: runs the four uv/pip blockers and approve-variants
against the incoming shell command.

Stdin (Cursor beforeShellExecution): {"command": "...", ...}
Stdout: {"permission": "deny", ...} when a blocker fires,
        {"permission": "allow", ...} when approve-variants approves,
        {} to defer to Cursor's normal permission flow.

Registered in ~/.cursor/hooks.json (user hooks run from ~/.cursor/):

    {"beforeShellExecution": [
        {"command": "python3 ../.agents/hooks/adapters/cursor-shell-gate.py"}
    ]}
"""

import json
import os
import subprocess
import sys

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKERS = [
    "check-uv-pytest.py",
    "check-uv-venv.py",
    "check-pip-install.py",
    "check-pipx.py",
]
DENY_SOUND = "/System/Library/Sounds/Pop.aiff"

try:
    data = json.load(sys.stdin)
except Exception:
    print("{}")
    sys.exit(0)

cmd = data.get("command", "")
if not cmd:
    print("{}")
    sys.exit(0)

payload = json.dumps(
    {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": cmd},
    }
)


def run_hook(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, script)],
        input=payload,
        capture_output=True,
        text=True,
    )


for name in BLOCKERS:
    proc = run_hook(name)
    if proc.returncode == 2:
        msg = proc.stderr.strip()
        try:
            subprocess.Popen(
                ["afplay", "-v", "0.35", DENY_SOUND],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        print(json.dumps({"permission": "deny", "user_message": msg, "agent_message": msg}))
        sys.exit(0)

proc = run_hook("approve-variants.py")
if proc.returncode == 0 and proc.stdout.strip():
    try:
        out = json.loads(proc.stdout)
        hso = out.get("hookSpecificOutput", {})
        if hso.get("permissionDecision") == "allow":
            reason = hso.get("permissionDecisionReason", "auto-approved safe command")
            print(json.dumps({"permission": "allow", "agent_message": reason}))
            sys.exit(0)
    except Exception:
        pass

print("{}")
