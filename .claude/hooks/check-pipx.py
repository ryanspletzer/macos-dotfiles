#!/usr/bin/env python3
"""Enforce using 'uvx' / 'uv tool install' instead of 'pipx'."""
import json
import re
import sys

data = json.load(sys.stdin)
if data.get("tool_name") != "Bash":
    sys.exit(0)

command = data.get("tool_input", {}).get("command", "")

if re.search(r'\bpipx\s+run\b', command):
    print("Use 'uvx' instead of 'pipx run'", file=sys.stderr)
    sys.exit(2)

if re.search(r'\bpipx\s+install\b', command):
    print("Use 'uv tool install' instead of 'pipx install'", file=sys.stderr)
    sys.exit(2)

if re.search(r'\bpipx\s+', command):
    print("Use 'uvx' or 'uv tool' instead of 'pipx'", file=sys.stderr)
    sys.exit(2)
