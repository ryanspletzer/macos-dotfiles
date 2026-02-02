#!/usr/bin/env python3
"""Enforce using 'uv venv' instead of 'python -m venv' or 'virtualenv'."""
import json
import re
import sys

data = json.load(sys.stdin)
if data.get("tool_name") != "Bash":
    sys.exit(0)

command = data.get("tool_input", {}).get("command", "")

# Patterns for non-uv venv creation
patterns = [
    r'\bpython3?(?:\.\d+)?\s+-m\s+venv\b',  # python -m venv, python3 -m venv, python3.12 -m venv
    r'\bvirtualenv\b',                        # virtualenv command
]

for pattern in patterns:
    if re.search(pattern, command):
        print("Use 'uv venv' instead of 'python -m venv' or 'virtualenv'", file=sys.stderr)
        sys.exit(2)
