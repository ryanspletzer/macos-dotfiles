#!/usr/bin/env python3
"""Advisory alias and env-var drift report across bash, zsh, and fish.

Aliases: launches each shell interactively and compares runtime
aliases. Env vars: launches each shell as a login+interactive shell
from a scrubbed minimal environment (so the configs must build their
world from scratch, matching a real terminal) and compares what each
shell contributed.

SECRETS: env-var values whose NAMES look secret-bearing (token, key,
auth, ...) are never printed -- they are compared and displayed as
sha256 digests only. A dedicated section lists which secret-bearing
vars are present in which shells.

ADVISORY ONLY: this script always exits 0 and is not part of the
pytest suite. Divergence is sometimes deliberate (features are wired
per shell intentionally); record those in INTENTIONAL /
INTENTIONAL_ENV below to silence them. pwsh is excluded entirely --
its alias and environment model is a different universe.

Run: python3 .checks/shell_drift_report.py
"""

import hashlib
import os
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


# --- env-var comparison ------------------------------------------------------

# Scrubbed parent environment for the env comparison: each shell's
# login+interactive startup must construct everything else itself.
MINIMAL_ENV = {
    "HOME": os.environ["HOME"],
    "USER": os.environ["USER"],
    "LOGNAME": os.environ.get("LOGNAME", os.environ["USER"]),
    "TERM": "xterm-256color",
    "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
}

# Values for these names are never printed; equality is shown by digest.
SENSITIVE_NAME = re.compile(
    r"TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|AUTH|CREDENTIAL|PRIVATE", re.IGNORECASE
)

# Per-session or shell-identity noise, not config drift.
VOLATILE_ENV = {
    "GPG_TTY": "tty-dependent",
    "PWD": "session state",
    "OLDPWD": "session state",
    "SHLVL": "session state",
    "_": "session state",
    "OSTYPE": "shell-reported platform string",
    "POSH_SESSION_ID": "random per session",
    "POSH_SHELL": "shell identity by design",
    "POSH_SHELL_VERSION": "shell identity by design",
    "PYENV_SHELL": "shell identity by design",
}

# env-var name -> why the divergence is intentional (not reported)
INTENTIONAL_ENV = {
    "FPATH": "zsh-only function search path",
    "ZLE_RPROMPT_INDENT": "zsh-only line-editor setting (oh-my-posh)",
    "INFOPATH": "brew shellenv emits a trailing colon in POSIX shells but not fish",
    "NVM_CD_FLAGS": "nvm.sh internal, value differs by shell",
    "NVM_DIR": "bash/zsh use nvm.sh; fish deliberately uses the nvm.fish plugin",
}


def runtime_env(shell):
    proc = subprocess.run(
        [shell, "-lic", "/usr/bin/env -0"],
        capture_output=True,
        text=True,
        timeout=60,
        env=MINIMAL_ENV,
    )
    contributed = {}
    for entry in proc.stdout.split("\0"):
        name, sep, value = entry.partition("=")
        if sep and MINIMAL_ENV.get(name) != value:
            contributed[name] = value
    return contributed


def display(name, value):
    if value is None:
        return "(not set)"
    if SENSITIVE_NAME.search(name):
        digest = hashlib.sha256(value.encode()).hexdigest()[:8]
        return f"<masked sha256:{digest}>"
    if len(value) > 72:
        return value[:69] + "..."
    return value


def path_segment_report(table):
    """Compare PATH additions (beyond the scrubbed baseline) as sets."""
    base = set(MINIMAL_ENV["PATH"].split(":"))
    segments = {
        shell: {s for s in table[shell].get("PATH", "").split(":") if s and s not in base}
        for shell in SHELLS
    }
    everywhere = set.intersection(*segments.values())
    drifted = []
    for segment in sorted(set.union(*segments.values()) - everywhere):
        holders = [shell for shell in SHELLS if segment in segments[shell]]
        drifted.append((segment, holders))
    return drifted


def report_env_drift():
    table = {shell: runtime_env(shell) for shell in SHELLS}
    skip = set(VOLATILE_ENV) | set(INTENTIONAL_ENV) | {"PATH"}
    names = sorted(set().union(*table.values()) - skip)

    drifted = []
    for name in names:
        values = {shell: table[shell].get(name) for shell in SHELLS}
        if len(set(values.values())) > 1:
            drifted.append((name, values))

    path_drift = path_segment_report(table)

    secretish = sorted(
        name
        for name in set().union(*table.values())
        if SENSITIVE_NAME.search(name)
    )
    if secretish:
        print("secret-bearing env vars (values never printed, compared by digest):")
        for name in secretish:
            holders = [shell for shell in SHELLS if name in table[shell]]
            print(f"  {name} ({', '.join(holders)})")
        print()

    if not drifted and not path_drift:
        print(
            f"env vars in sync across {', '.join(SHELLS)} "
            f"({len(names)} compared, {len(INTENTIONAL_ENV)} intentional, "
            f"{len(VOLATILE_ENV)} volatile skipped)"
        )
        return

    if drifted:
        print(f"{len(drifted)} env var(s) drift across shells (advisory only):\n")
        for name, values in drifted:
            print(f"  {name}")
            for shell in SHELLS:
                print(f"    {shell:<5} {display(name, values[shell])}")
            print()
    if path_drift:
        print("PATH segments not present in all shells (advisory only):\n")
        for segment, holders in path_drift:
            print(f"  {segment}  (only: {', '.join(holders)})")
        print()
    print("If a divergence is deliberate, add it to INTENTIONAL_ENV in this script.")


def report_alias_drift():
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


def main():
    report_alias_drift()
    print()
    report_env_drift()


if __name__ == "__main__":
    main()
