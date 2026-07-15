#!/usr/bin/env bash
# Cursor CLI custom statusline (~/.cursor/cli-config.json "statusLine").
# Cursor pipes a Claude Code-compatible JSON payload on stdin; render it with
# oh-my-posh's claude statusline. oh-my-posh parses used_percentage as an
# integer and Cursor can emit floats, so coerce percentages before rendering.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

python3 -c "
import json, sys
data = json.load(sys.stdin)
cw = data.get('context_window') or {}
for key in ('used_percentage', 'remaining_percentage'):
    value = cw.get(key)
    if isinstance(value, float):
        cw[key] = int(value)
json.dump(data, sys.stdout)
" | oh-my-posh claude --config "$HOME/.oh-my-posh/themes/cursor-statusline.yaml"
