#!/usr/bin/env python3
"""Cursor CLI sessionStart adapter: inject ~/AGENTS.md as session context.

Cursor's account-synced User Rules are not source-controllable, and the
disk-based ~/.cursor/rules/ loading is bugged (per Cursor staff, 2026-04).
This hook makes the shared instruction core portable anyway: on session
start it returns the contents of ~/AGENTS.md as additional_context.

Stdin (Cursor sessionStart): session metadata (unused).
Stdout: {"additional_context": "<~/AGENTS.md contents>"}.

Registered in ~/.cursor/hooks.json under sessionStart.
"""

import json
import os
import sys

sys.stdin.read()

path = os.path.expanduser("~/AGENTS.md")
try:
    with open(path, encoding="utf-8") as f:
        content = f.read().strip()
except OSError:
    print("{}")
    sys.exit(0)

print(json.dumps({"additional_context": content}))
