#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")

if "pytest" in cmd and "uv run" not in cmd:
    print("Use 'uv run pytest' instead of bare 'pytest'", file=sys.stderr)
    sys.exit(2)
