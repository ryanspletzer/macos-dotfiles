#!/usr/bin/env bash
# Antigravity CLI custom statusline (~/.gemini/antigravity-cli/settings.json
# "statuslineCommand", or set interactively via /statusline <command>).
# agy pipes a Claude Code-compatible JSON payload on stdin; render it with
# oh-my-posh's claude statusline. oh-my-posh parses used_percentage as an
# integer and some tools emit floats, so coerce percentages before rendering
# (same guard as the Cursor adapter).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Debug capture: when the sentinel exists, tee the raw stdin payload to a file
# so agy's statusline JSON schema can be inspected.
#   Enable:  touch ~/.gemini/.capture-payload
#   Inspect: cat  ~/.gemini/statusline-payload.json
#   Disable: rm   ~/.gemini/.capture-payload
capture() {
  if [[ -e "$HOME/.gemini/.capture-payload" ]]; then
    tee "$HOME/.gemini/statusline-payload.json"
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
" | oh-my-posh claude --config "$HOME/.oh-my-posh/themes/antigravity-statusline.yaml"
