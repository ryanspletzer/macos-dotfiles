#!/usr/bin/env python3
"""Enforce using 'uv pip install' / 'uv add' or 'pipx install' instead of bare 'pip install'."""
import json
import re
import sys

data = json.load(sys.stdin)
if data.get("tool_name") != "Bash":
    sys.exit(0)

command = data.get("tool_input", {}).get("command", "")

# Allow uv-wrapped pip commands (uv pip install, uv pip compile, etc.)
if re.search(r'\buv\s+pip\b', command):
    sys.exit(0)

# Block bare pip/pip3/pip3.x install
if re.search(r'\bpip3?(?:\.\d+)?\s+install\b', command):
    print(
        "Use 'uv pip install' (in a venv), 'uv add' (for project deps), "
        "or 'pipx install' (for CLI tools) instead of bare 'pip install'",
        file=sys.stderr,
    )
    sys.exit(2)
