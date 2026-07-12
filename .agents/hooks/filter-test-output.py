#!/usr/bin/env python3
"""Filter verbose test-runner output down to failures + summary.

PreToolUse (Bash) hook. When a command is a *simple* invocation of a known
test runner (no shell operators), it is rewritten to capture full output to a
temp log, print only failure lines (+ context) and the trailing summary, and
exit with the test runner's REAL exit code. This keeps tens of thousands of
log tokens out of the main context while preserving correctness.

Design notes:
- Only single, unchained commands are touched. If the command already contains
  a pipe/redirect/chain/substitution, it is left untouched (avoids clobbering
  intent and prevents re-wrapping our own output).
- The real exit code is preserved via $__rc, so passing runs are NOT misread as
  failures (the naive `... | grep FAIL` approach gets this wrong).
- The full log is left on disk (path printed) so the unfiltered output is
  recoverable if the filtered view is insufficient.
- Returns permissionDecision "allow" so the rewritten (necessarily multi-
  statement) command does not trigger a permission prompt. Wire this hook LAST
  in the PreToolUse Bash array so the uv/pip enforcement hooks evaluate the
  original command first.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _utils import strip_quoted_content

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
stripped = strip_quoted_content(cmd)

# Bail on anything that isn't a single, simple command: chains, pipes,
# redirects, and substitutions are left untouched (also stops re-wrapping the
# rewritten command, which itself contains operators).
if re.search(r"[|<>;`]|&&|\|\||\$\(", stripped):
    print("{}")
    sys.exit(0)

# Known test runners (matched against quote-stripped command tokens).
TEST_RUNNERS = [
    r"\buv run pytest\b",
    r"\bdotnet test\b",
    r"\bgo test\b",
    r"\bnpm (run )?test\b",
    r"\b(npx )?(jest|vitest)\b",
    r"\b(npx )?playwright test\b",
    r"\bbundle exec rspec\b",
]

if not any(re.search(p, stripped) for p in TEST_RUNNERS):
    print("{}")
    sys.exit(0)

# Lines worth surfacing: failures, errors, tracebacks, and summary counts.
FAIL_PATTERN = (
    r"(FAIL|FAILED|Failed!|--- FAIL|ERROR|Error:|error:|✕|✗|✘|"
    r"AssertionError|Traceback|[0-9]+ (failed|errored)|Failed: +[1-9]|"
    r"=+ .*(failed|error))"
)

log = "/tmp/agent-test-$$.log"
new_command = (
    f'( {cmd} ) > "{log}" 2>&1; __rc=$?; '
    f"grep -nE -A3 '{FAIL_PATTERN}' \"{log}\" | head -200; "
    f"echo '---- summary (last 15 lines) ----'; tail -15 \"{log}\"; "
    f'echo "[test output filtered to failures; full log: {log}; exit=$__rc]"; '
    f"exit $__rc"
)

output = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "updatedInput": {"command": new_command},
    }
}
print(json.dumps(output))
