#!/usr/bin/env python3
"""Cursor CLI preToolUse (Shell) adapter for filter-test-output.py.

Bridges Cursor's preToolUse dialect to the shared test-output filter:
when the shell command is a simple known test-runner invocation, the
command is rewritten to log full output and surface only failures.

Stdin (Cursor preToolUse): {"tool_name": "Shell",
                            "tool_input": {"command": "...", ...}, ...}
Stdout: {"permission": "allow", "updated_input": {...}} on rewrite,
        {} otherwise.

Registered in ~/.cursor/hooks.json with matcher "Shell".
"""

import json
import os
import subprocess
import sys

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    data = json.load(sys.stdin)
except Exception:
    print("{}")
    sys.exit(0)

tool_input = data.get("tool_input") or {}
cmd = tool_input.get("command", "")
if data.get("tool_name") != "Shell" or not cmd:
    print("{}")
    sys.exit(0)

payload = json.dumps(
    {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": cmd},
    }
)

proc = subprocess.run(
    [sys.executable, os.path.join(HOOKS_DIR, "filter-test-output.py")],
    input=payload,
    capture_output=True,
    text=True,
)

if proc.returncode == 0 and proc.stdout.strip():
    try:
        out = json.loads(proc.stdout)
        new_cmd = out.get("hookSpecificOutput", {}).get("updatedInput", {}).get("command")
        if new_cmd:
            updated = dict(tool_input)
            updated["command"] = new_cmd
            print(json.dumps({"permission": "allow", "updated_input": updated}))
            sys.exit(0)
    except Exception:
        pass

print("{}")
