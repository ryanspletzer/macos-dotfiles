#!/usr/bin/env python3
"""Advisory alias-drift report across bash, zsh, and fish.

Launches each shell interactively, collects its runtime aliases, and
reports aliases that are missing from some shells or defined with
different values.

ADVISORY ONLY: this script always exits 0 and is not part of the
pytest suite. Divergence is sometimes deliberate (features are wired
per shell intentionally); record those in INTENTIONAL below to
silence them. pwsh is excluded entirely -- its alias system and
builtin aliases are a different universe.

Run: python3 .checks/shell_drift_report.py
"""

import re
import subprocess

# alias name -> why the divergence is intentional (not reported)
INTENTIONAL = {
    "run-help": "zsh built-in default alias, not user config",
    "which-command": "zsh built-in default alias, not user config",
    "z": "zoxide wires an alias in fish but a function in zsh/bash",
    "zi": "zoxide wires an alias in fish but a function in zsh/bash",
}

SHELLS = ["bash", "zsh", "fish"]

ALIAS_LINE = {
    "bash": re.compile(r"^alias (\S+?)=(.*)$"),
    "zsh": re.compile(r"^(\S+?)=(.*)$"),
    "fish": re.compile(r"^alias (\S+) (.*)$"),
}


def runtime_aliases(shell):
    proc = subprocess.run(
        [shell, "-ic", "alias"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    aliases = {}
    for line in proc.stdout.splitlines():
        match = ALIAS_LINE[shell].match(line)
        if match:
            name, value = match.groups()
            aliases[name] = unquote(value)
    return aliases


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


def main():
    table = {shell: runtime_aliases(shell) for shell in SHELLS}
    names = sorted(set().union(*table.values()) - set(INTENTIONAL))

    drifted = []
    for name in names:
        values = {shell: table[shell].get(name) for shell in SHELLS}
        if len(set(values.values())) > 1:
            drifted.append((name, values))

    if not drifted:
        print(
            f"aliases in sync across {', '.join(SHELLS)} "
            f"({len(names)} compared, "
            f"{len(INTENTIONAL)} intentional divergences skipped)"
        )
        return

    print(f"{len(drifted)} alias(es) drift across shells (advisory only):\n")
    for name, values in drifted:
        print(f"  {name}")
        for shell in SHELLS:
            value = values[shell]
            print(f"    {shell:<5} {value if value is not None else '(not defined)'}")
        print()
    print("If a divergence is deliberate, add it to INTENTIONAL in this script.")


if __name__ == "__main__":
    main()
