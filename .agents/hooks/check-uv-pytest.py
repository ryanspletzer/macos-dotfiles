#!/usr/bin/env python3
"""Enforce using 'uv run pytest' instead of bare 'pytest'."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _utils import strip_quoted_content

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
cmd = strip_quoted_content(cmd)

if re.search(r'\bpytest\b', cmd) and "uv run" not in cmd:
    print("Use 'uv run pytest' instead of bare 'pytest'", file=sys.stderr)
    sys.exit(2)
