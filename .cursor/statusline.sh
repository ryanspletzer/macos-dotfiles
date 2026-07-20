#!/usr/bin/env bash
# Cursor CLI custom statusline (~/.cursor/cli-config.json "statusLine").
# Cursor pipes a Claude Code-compatible JSON payload on stdin; render it with
# oh-my-posh's claude statusline. oh-my-posh parses used_percentage as an
# integer and Cursor can emit floats, so coerce percentages before rendering.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Debug capture: when the sentinel exists, tee the raw stdin payload to a file
# so Cursor's (undocumented) statusLine JSON schema can be inspected.
#   Enable:  touch ~/.cursor/.capture-payload
#   Inspect: cat  ~/.cursor/statusline-payload.json
#   Disable: rm   ~/.cursor/.capture-payload
capture() {
  if [[ -e "$HOME/.cursor/.capture-payload" ]]; then
    tee "$HOME/.cursor/statusline-payload.json"
  else
    cat
  fi
}

capture | python3 -c "
import json, sys
data = json.load(sys.stdin)
cw = data.get('context_window') or {}
for key in ('used_percentage', 'remaining_percentage'):
    value = cw.get(key)
    if isinstance(value, float):
        cw[key] = int(value)
json.dump(data, sys.stdout)
" | oh-my-posh claude --config "$HOME/.oh-my-posh/themes/cursor-statusline.yaml"
