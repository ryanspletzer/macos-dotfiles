#!/usr/bin/env python3
"""Git clean filter for .codex/config.toml: strip Codex-written machine state.

Codex mixes portable user settings (model, [tui] status_line) with
machine-specific state it writes itself (absolute-path project trust
entries, hook trust hashes, notice/nux counters) into the same file,
and offers no way to separate them. This filter keeps the committed
blob portable while the working file keeps its local state.

Wired up via .gitattributes (filter=codex-config) plus a one-time
per-machine: git config filter.codex-config.clean '~/.agents/bin/codex-config-clean.py'
"""
import sys

# Top-level TOML tables Codex writes as machine state. A header matches
# if it equals the entry or extends it as a dotted/quoted sub-table.
STATE_TABLES = (
    "projects",
    "hooks.state",
    "notice",
    "tui.model_availability_nux",
)


def is_state_header(header):
    return any(
        header == table or header.startswith(table + ".")
        for table in STATE_TABLES
    )


def clean(text):
    kept = []
    dropping = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            header = stripped.lstrip("[").rstrip("]").strip()
            dropping = is_state_header(header)
        if not dropping:
            kept.append(line)

    # Tidy blank lines left behind by removed sections.
    out = []
    for line in kept:
        if line.strip() == "" and (not out or out[-1] == ""):
            continue
        out.append(line.rstrip() if line.strip() == "" else line)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n" if out else ""


if __name__ == "__main__":
    sys.stdout.write(clean(sys.stdin.read()))
