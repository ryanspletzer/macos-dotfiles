#!/usr/bin/env python3
"""Enforce using 'uv pip install' / 'uv add' or 'uv tool install' instead of bare 'pip install'."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _utils import strip_quoted_content

data = json.load(sys.stdin)
if data.get("tool_name") != "Bash":
    sys.exit(0)

command = data.get("tool_input", {}).get("command", "")
command = strip_quoted_content(command)

# Allow uv-wrapped pip commands (uv pip install, uv pip compile, etc.)
if re.search(r'\buv\s+pip\b', command):
    sys.exit(0)

# Block bare pip/pip3/pip3.x install
if re.search(r'\bpip3?(?:\.\d+)?\s+install\b', command):
    print(
        "Use 'uv pip install' (in a venv), 'uv add' (for project deps), "
        "or 'uv tool install' (for CLI tools) instead of bare 'pip install'",
        file=sys.stderr,
    )
    sys.exit(2)
