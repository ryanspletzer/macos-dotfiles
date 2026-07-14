#!/usr/bin/env python3
"""
PreToolUse Hook: Compositional Bash Command Approval

Shared across agent CLIs: consumed natively by Claude Code and Codex CLI
(identical hook schema), and via adapters/cursor-shell-gate.py for Cursor.

PROBLEM
-------
Claude Code's static permission system uses prefix matching:
    "Bash(git diff:*)" matches "git diff --staged" but NOT "git -C /path diff"
    "Bash(timeout 30 pytest:*)" matches that exact timeout, not "timeout 20 pytest"

This leads to frequent permission prompts for safe command variations.

SOLUTION
--------
This hook auto-approves Bash commands that are safe combinations of:
    WRAPPERS (timeout, env vars, .venv/bin/) + CORE COMMANDS (git, pytest, etc.)

Example: "timeout 60 RUST_BACKTRACE=1 cargo test" is approved as:
    wrapper(timeout) + wrapper(env vars) + safe_command(cargo)

CHAINED COMMANDS
----------------
Commands with &&, ||, ;, | are split and ALL segments must be safe:
    "ls && pwd"           -> approved (both safe)
    "ls && rm -rf /"      -> rejected (rm not safe)
    "git diff | head"     -> approved (both safe)

Command substitution ($(...) and backticks) is always rejected.

CONFIGURATION
-------------
Registered in ~/.claude/settings.json and ~/.codex/hooks.json:

    "hooks": {
      "PreToolUse": [{
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "python3 ~/.agents/hooks/approve-variants.py"}]
      }]
    }

EXTENDING
---------
To add new safe wrappers: Add to WRAPPER_PATTERNS (regex, name)
To add new safe commands: Add to SAFE_COMMANDS (regex, name)

DEBUG
-----
    echo '{"tool_name": "Bash", "tool_input": {"command": "timeout 30 pytest"}}' | python3 ~/.agents/hooks/approve-variants.py
"""

import json
import sys
import re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name")
tool_input = data.get("tool_input", {})

if tool_name != "Bash":
    sys.exit(0)


def approve(reason):
    """Output approval JSON and exit."""
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(result))
    sys.exit(0)


cmd = tool_input.get("command", "")

# --- Reject dangerous constructs that are hard to parse safely ---
if re.search(r"\$\(|`", cmd):
    sys.exit(0)


def split_command_chain(cmd):
    """Split command into segments on &&, ||, ;, |.

    Note: We don't split on newlines if:
    - Quotes are present (multiline strings like python -c "...")
    - Backslash continuations are present (cmd \\\n  --flag)
    """
    # First, collapse backslash-newline continuations
    cmd = re.sub(r"\\\n\s*", " ", cmd)

    # Protect quoted strings from splitting (replace with placeholders)
    quoted_strings = []

    def save_quoted(m):
        quoted_strings.append(m.group(0))
        return f"__QUOTED_{len(quoted_strings) - 1}__"

    cmd = re.sub(r'"[^"]*"', save_quoted, cmd)
    cmd = re.sub(r"'[^']*'", save_quoted, cmd)

    # Normalize redirections to prevent splitting on & in 2>&1
    cmd = re.sub(r"(\d*)>&(\d*)", r"__REDIR_\1_\2__", cmd)
    cmd = re.sub(r"&>", "__REDIR_AMPGT__", cmd)

    # Split on command separators: &&, ||, ;, |, & (background), and newlines.
    # Quoted strings — including any newlines inside them — were already replaced
    # with placeholders above, so every newline still present here is a real
    # command separator. (Previously newlines were left unsplit whenever the
    # command contained any quote, which let `echo "x"\nrm -rf ~` ride through as
    # a single `echo` segment.)
    segments = re.split(r"\s*(?:&&|\|\||;|\||&)\s*|\n", cmd)

    # Restore quoted strings and redirections
    def restore(s):
        s = re.sub(r"__REDIR_(\d*)_(\d*)__", r"\1>&\2", s)
        s = s.replace("__REDIR_AMPGT__", "&>")
        # Restore highest-index placeholders first: a later (single-quote) mask
        # can contain an earlier (double-quote) placeholder but never vice versa,
        # so descending order guarantees no placeholder leaks into the result.
        # A leak would hide content (e.g. a `> "file"` redirect) from the safety
        # checks that scan the restored segment.
        for i in range(len(quoted_strings) - 1, -1, -1):
            s = s.replace(f"__QUOTED_{i}__", quoted_strings[i])
        return s

    segments = [restore(s) for s in segments]
    return [s.strip() for s in segments if s.strip()]


# --- Safe wrappers that can prefix any safe command ---
WRAPPER_PATTERNS = [
    (r"^timeout\s+\d+\s+", "timeout"),
    (r"^nice\s+(-n\s*\d+\s+)?", "nice"),
    (r"^env\s+", "env"),
    (r"^([A-Z_][A-Z0-9_]*=[^\s]*\s+)+", "env vars"),
    # Virtual env paths: .venv/bin/, ../.venv/bin/, /abs/path/.venv/bin/, venv/bin/
    (r"^(\.\./)*\.?venv/bin/", ".venv"),
    (r"^/[^\s]+/\.?venv/bin/", ".venv"),
    # do (loop body prefix)
    (r"^do\s+", "do"),
    # command (bypass aliases/functions to run actual binary)
    # (?!-) so "command -v foo" falls through to its own SAFE_COMMANDS entry
    (r"^command\s+(?!-)", "command"),
    # Absolute system bin paths: /bin/ls, /usr/bin/grep, /opt/homebrew/bin/jq
    # Only the path prefix is stripped — the binary must still match SAFE_COMMANDS
    (r"^/(usr/(local/)?|opt/homebrew/)?s?bin/", "abs bin path"),
    # time (measure command execution time)
    (r"^time\s+", "time"),
    # xargs: strip xargs and its flags so the command it INVOKES must itself
    # match a SAFE_COMMANDS entry. `xargs grep` stays approved; `xargs rm`,
    # `xargs sh -c ...` fall through to a prompt. Safe by construction: whatever
    # remains is re-checked against the same allowlist.
    (
        r"^xargs(?:\s+(?:-[nPLsIJRE]\s*\S+|-[0-9oprtIx]+|--[a-z][a-z-]*(?:=\S+)?))*\s+",
        "xargs",
    ),
]

# --- Safe core command patterns ---
SAFE_COMMANDS = [
    # ── Git ───────────────────────────────────────────────────────────────
    # read operations (with optional -C flag)
    (
        r"^git\s+(-C\s+\S+\s+)?"
        r"(diff|log|status|show|branch|stash\s+list|bisect|worktree\s+list|fetch"
        r"|remote|tag|rev-parse|rev-list|ls-files|ls-tree|describe|shortlog"
        r"|reflog|blame|name-rev|for-each-ref|cherry|count-objects"
        r"|verify-commit|verify-tag|ls-remote)\b",
        "git read op",
    ),
    # git config: read-only forms only. `git config <key> <value>` WRITES, and a
    # poisoned core.pager / alias / core.fsmonitor value executes on the next git
    # invocation — so only --get*/--list/-l (optionally after scope flags) pass.
    (
        r"^git\s+(-C\s+\S+\s+)?config\s+(--\S+\s+)*"
        r"(--get\b|--get-all\b|--get-regexp\b|--get-urlmatch\b|--list\b|-l\b)",
        "git config read",
    ),
    # write operations (local only — no push/commit)
    (
        r"^git\s+(-C\s+\S+\s+)?"
        r"(add|checkout|merge|rebase|stash|switch|restore|cherry-pick"
        r"|worktree\s+(add|remove|prune))\b",
        "git write op",
    ),
    # ── Python ────────────────────────────────────────────────────────────
    (r"^pytest\b", "pytest"),
    (r"^python3?\b", "python"),
    (r"^ruff\b", "ruff"),
    (r"^uv\s+(pip|run|sync|venv|add|remove|lock|tool|init|build|publish|tree|self)\b", "uv"),
    (r"^uvx\b", "uvx"),
    (r"^mypy\b", "mypy"),
    (r"^black\b", "black"),
    (r"^isort\b", "isort"),
    (r"^pyright\b", "pyright"),
    # ── JavaScript / TypeScript ───────────────────────────────────────────
    (r"^npm\s+(install|ci|run|test|build|ls|outdated|info|init|pack|exec|explain)\b", "npm"),
    (r"^npx\b", "npx"),
    (r"^pnpm\s+(install|run|test|build|add|remove|exec|dlx|dev|create|ls|outdated|why)\b", "pnpm"),
    (r"^bun\s+(install|run|test|build|add|remove|x|create|dev|init|pm)\b", "bun"),
    (r"^node\b", "node"),
    (r"^tsc\b", "tsc"),
    (r"^prettier\b", "prettier"),
    (r"^eslint\b", "eslint"),
    # ── Go ────────────────────────────────────────────────────────────────
    (
        r"^go\s+(build|test|run|fmt|vet|mod|generate|get|clean|env|version"
        r"|tool|work|doc|install|list)\b",
        "go",
    ),
    (r"^gofmt\b", "gofmt"),
    (r"^golangci-lint\b", "golangci-lint"),
    (r"^gopls\b", "gopls"),
    # ── Ruby ──────────────────────────────────────────────────────────────
    (r"^ruby\b", "ruby"),
    (r"^irb\b", "irb"),
    (r"^bundle\b", "bundle"),
    (r"^gem\b", "gem"),
    (r"^rake\b", "rake"),
    (r"^rails\b", "rails"),
    (r"^rubocop\b", "rubocop"),
    (r"^chruby\b", "chruby"),
    # ── Rust ──────────────────────────────────────────────────────────────
    (
        r"^cargo\s+(build|test|run|check|clippy|fmt|clean|add|remove|update"
        r"|doc|bench|init|new|publish|search|tree|install)\b",
        "cargo",
    ),
    (r"^maturin\s+(develop|build)\b", "maturin"),
    (r"^rustc\b", "rustc"),
    (r"^rustup\b", "rustup"),
    (r"^rustfmt\b", "rustfmt"),
    # ── .NET ──────────────────────────────────────────────────────────────
    (
        r"^dotnet\s+(build|test|run|restore|clean|add|format|tool|new|list"
        r"|pack|publish|watch|nuget|sln|ef)\b",
        "dotnet",
    ),
    # ── Swift ─────────────────────────────────────────────────────────────
    (r"^swift\s+(build|test|run|package)\b", "swift"),
    (r"^swiftc\b", "swiftc"),
    (r"^swiftformat\b", "swiftformat"),
    (r"^swiftlint\b", "swiftlint"),
    # ── Elixir ────────────────────────────────────────────────────────────
    (r"^elixir\b", "elixir"),
    (r"^iex\b", "iex"),
    (r"^mix\b", "mix"),
    # ── Java ──────────────────────────────────────────────────────────────
    (r"^java\b", "java"),
    (r"^javac\b", "javac"),
    (r"^mvn\b", "mvn"),
    (r"^gradle\b", "gradle"),
    (r"^gradlew\b", "gradlew"),
    # ── Build tools ───────────────────────────────────────────────────────
    (r"^make\b", "make"),
    (r"^cmake\b", "cmake"),
    # ── Linters & formatters ──────────────────────────────────────────────
    (r"^shellcheck\b", "shellcheck"),
    (r"^yamllint\b", "yamllint"),
    (r"^markdownlint\b", "markdownlint"),
    (r"^markdownlint-cli2\b", "markdownlint-cli2"),
    (r"^cfn-lint\b", "cfn-lint"),
    (r"^actionlint\b", "actionlint"),
    # ── GitHub CLI ────────────────────────────────────────────────────────
    (r"^gh\s+", "gh"),
    # ── Docker ────────────────────────────────────────────────────────────
    (
        r"^docker\s+(build|run|exec|ps|images|logs|inspect|pull|tag|version"
        r"|info|network|volume|port|cp|stats|top|diff|history|events"
        r"|compose|buildx)\b",
        "docker",
    ),
    (r"^docker-compose\b", "docker-compose"),
    # ── Infrastructure (conservative — no apply/destroy) ──────────────────
    (
        r"^terraform\s+(init|plan|validate|fmt|show|output|version|providers"
        r"|workspace\s+(list|show|select)|state\s+(list|show|pull)|graph|get)\b",
        "terraform",
    ),
    (
        r"^helm\s+(template|lint|list|status|get|repo|search|version|show"
        r"|dependency|env)\b",
        "helm",
    ),
    (
        r"^kubectl\s+(get|describe|logs|config|explain|api-resources|api-versions"
        r"|version|top|cluster-info|auth)\b",
        "kubectl",
    ),
    (r"^packer\s+(validate|fmt|init|inspect)\b", "packer"),
    (r"^ansible-lint\b", "ansible-lint"),
    (r"^ansible-playbook\b", "ansible-playbook"),
    # ── Homebrew (read-only) ──────────────────────────────────────────────
    (
        r"^brew\s+(list|info|search|doctor|config|deps|leaves|outdated|uses"
        r"|desc|cat|home|log|tap-info|commands|shellenv)\b",
        "brew read",
    ),
    # ── Modern CLI utilities ──────────────────────────────────────────────
    (r"^bat\b", "bat"),
    (r"^eza\b", "eza"),
    (r"^fd\b", "fd"),
    (r"^tree\b", "tree"),
    (r"^jq\b", "jq"),
    (r"^yq\b", "yq"),
    (r"^xh\b", "xh"),
    (r"^delta\b", "delta"),
    (r"^tldr\b", "tldr"),
    (r"^fzf\b", "fzf"),
    (r"^pandoc\b", "pandoc"),
    (r"^sqlite3\b", "sqlite3"),
    # ── File operations ───────────────────────────────────────────────────
    (r"^mkdir\b", "mkdir"),
    (r"^cp\b", "cp"),
    (r"^mv\b", "mv"),
    (r"^ln\b", "ln"),
    (r"^chmod\b", "chmod"),
    (r"^tee\b", "tee"),
    # find: read-only traversals only — reject the action families that run
    # programs or delete files (the -exec/-execdir/-ok/-delete/-fprint group).
    (
        r"^find\b(?!.*\s-(?:exec(?:dir)?|ok(?:dir)?|delete|fprint(?:f)?|fls)\b)",
        "find (read-only)",
    ),
    # awk: text processing only — reject system()/getline/pipes/print-redirects,
    # the constructs that let awk shell out or write files.
    (
        r"^awk\b(?!.*(?:system\s*\(|getline|\|&|\|\s*[\"']|>\s*[\"']))",
        "awk (read-only)",
    ),
    # ── Common read-only / info commands ──────────────────────────────────
    (
        r"^(ls|cat|head|tail|wc|grep|rg|file|which|pwd|du|df"
        r"|curl|wget|sort|uniq|cut|tr|sed"
        r"|readlink|realpath|basename|dirname"
        r"|date|uname|hostname|whoami|id|groups"
        r"|stat|shasum|md5|sha256sum"
        r"|less|more|type|printenv|locale|lsof"
        r"|open|pbcopy|pbpaste"
        r"|comm|join|paste|expand|fold|fmt"
        r"|nproc|sysctl|sw_vers|arch|getconf)\b",
        "read-only",
    ),
    # touch (update timestamps, create empty files)
    (r"^touch\b", "touch"),
    # ── Shell builtins & control flow ─────────────────────────────────────
    (r"^command\s+-v\b", "command -v"),
    (r"^(true|false|exit(\s+\d+)?)$", "shell builtin"),
    (r"^(pkill|kill)\b", "process mgmt"),
    (r"^echo\b", "echo"),
    (r"^printf\b", "printf"),
    (r"^cd\s", "cd"),
    (r"^(source|\.) [^\s]*venv/bin/activate", "venv activate"),
    (r"^sleep\s", "sleep"),
    (r"^[A-Z_][A-Z0-9_]*=\S*$", "var assignment"),
    (r"^for\s+\w+\s+in\s", "for loop"),
    (r"^while\s", "while loop"),
    (r"^done$", "done"),
    (r"^(test|\[)\s", "test"),
    (r"^if\s", "if"),
    (r"^(then|else|elif|fi)$", "conditional"),
    (r"^(case\s|esac$)", "case"),
    (r"^(export|unset|local|declare|typeset|readonly)\s", "shell var"),
    (r"^return(\s+\d+)?$", "return"),
    (r"^shift(\s+\d+)?$", "shift"),
    (r"^(wait|bg|fg|jobs)\b", "job control"),
    (r"^trap\s", "trap"),
]


def strip_wrappers(cmd):
    """Strip safe wrapper prefixes, return (core_cmd, list_of_wrappers)."""
    wrappers = []
    changed = True
    while changed:
        changed = False
        for pattern, name in WRAPPER_PATTERNS:
            m = re.match(pattern, cmd)
            if m:
                wrappers.append(name)
                cmd = cmd[m.end() :]
                changed = True
                break
    return cmd.strip(), wrappers


def check_safe(cmd):
    """Check if command matches a safe pattern. Returns reason or None."""
    for pattern, reason in SAFE_COMMANDS:
        if re.match(pattern, cmd):
            return reason
    return None


# A safe command (echo/cat/tee/...) must not silently overwrite files such as
# ~/.zshrc, ~/.ssh/authorized_keys, or a git hook. File writes outside these
# temp/null targets fall through to a permission prompt instead of auto-approving.
WRITE_OK_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr"}
WRITE_OK_PREFIXES = ("/tmp/", "/private/tmp/", "/var/folders/")


def _target_is_temp(target):
    target = target.strip("'\"")
    if target in WRITE_OK_TARGETS:
        return True
    return any(target.startswith(p) for p in WRITE_OK_PREFIXES)


def writes_outside_temp(segment, core_cmd):
    """True if the segment writes to a file outside the temp/null allowlist.

    Covers shell output redirects (>, >>, >|, &>) and tee's file operands.
    Quoted targets are treated as unverifiable (unsafe) rather than trusted.
    """
    # Hide quoted strings so a '>' inside quotes isn't read as a redirect, and a
    # quoted redirect target becomes an unverifiable placeholder (never temp).
    masked = re.sub(r'"[^"]*"', " \x00 ", segment)
    masked = re.sub(r"'[^']*'", " \x00 ", masked)
    # Drop fd-dup redirects (2>&1, >&2) — they don't create files.
    masked = re.sub(r"\d*>&\d*", " ", masked)
    for m in re.finditer(r"(?:&>>?|\d*>>?)\|?\s*([^\s|&;<>]+)", masked):
        if not _target_is_temp(m.group(1)):
            return True
    # tee writes to its file operands (after -a/-i style flags).
    if re.match(r"^tee\b", core_cmd):
        for arg in core_cmd.split()[1:]:
            if arg.startswith("-"):
                continue
            if not _target_is_temp(arg):
                return True
    return False


def sed_writes_or_execs(core_cmd):
    """True if a sed command writes outside temp or executes a shell command.

    sed can write files (the w/W commands and the s///w flag) and — on GNU sed —
    run shell commands (the s///e flag and the e command). A text filter must not
    silently overwrite ~/.zshrc or shell out, so those forms fall through to a
    prompt. Plain read-only sed (s///, p, d, y, ...) still auto-approves, as does
    a w/W write whose target is under the temp allowlist.
    """
    if not re.match(r"^sed\b", core_cmd):
        return False
    # A sed command sits at a script boundary (start, ';', '{', newline, -e, or
    # an opening quote) and may carry a leading line/regex address like 1, $,
    # 1,5 or /re/ — so `1e cmd` and `/re/w file` are commands, not text.
    addr = r"(?:[0-9]+|\$|/(?:\\.|[^/])*/)(?:\s*[,~+]\s*(?:[0-9]+|\$|/(?:\\.|[^/])*/))?\s*!?\s*"
    pos = r"(?:^|[;{\n]|-e\s+|['\"])\s*(?:" + addr + r")?"
    # w / W command writing to a file:  ...; w <file>   /   /re/W <file>
    for m in re.finditer(pos + r"[wW]\s+(\S+)", core_cmd):
        if not _target_is_temp(m.group(1)):
            return True
    # s///w (write) or s///e (execute) flag on a substitution. The write target
    # trails the flags (unverifiable) and e executes, so reject outright.
    for delim in "/|#,:@":
        d = re.escape(delim)
        if re.search(rf"s{d}(?:\\.|[^{d}])*{d}(?:\\.|[^{d}])*{d}[a-zA-Z]*[we]", core_cmd):
            return True
    # GNU 'e' execute command:  ...; e <command>   /   1e <command>
    if re.search(pos + r"e\s+\S", core_cmd):
        return True
    return False


# --- Main Bash logic ---
segments = split_command_chain(cmd)

reasons = []
for segment in segments:
    core_cmd, wrappers = strip_wrappers(segment)
    reason = check_safe(core_cmd)
    if not reason:
        sys.exit(0)  # One unsafe segment = reject entire command
    if writes_outside_temp(segment, core_cmd):
        sys.exit(0)  # Safe command, but writes to a non-temp file = reject
    if sed_writes_or_execs(core_cmd):
        sys.exit(0)  # sed that writes outside temp or shells out = reject
    if wrappers:
        reasons.append(f"{'+'.join(wrappers)} + {reason}")
    else:
        reasons.append(reason)

approve(" | ".join(reasons))
