#!/usr/bin/env python3
"""
Claude Code PreToolUse Hook: Compositional Bash Command Approval

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
Registered in ~/.claude/settings.json:

    "hooks": {
      "PreToolUse": [{
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/approve-variants.py"}]
      }]
    }

EXTENDING
---------
To add new safe wrappers: Add to WRAPPER_PATTERNS (regex, name)
To add new safe commands: Add to SAFE_COMMANDS (regex, name)

DEBUG
-----
    echo '{"tool_name": "Bash", "tool_input": {"command": "timeout 30 pytest"}}' | python3 ~/.claude/hooks/approve-variants.py
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

    # Split on command separators: &&, ||, ;, |, & (background)
    if quoted_strings:
        segments = re.split(r"\s*(?:&&|\|\||;|\||&)\s*", cmd)
    else:
        segments = re.split(r"\s*(?:&&|\|\||;|\||&)\s*|\n", cmd)

    # Restore quoted strings and redirections
    def restore(s):
        s = re.sub(r"__REDIR_(\d*)_(\d*)__", r"\1>&\2", s)
        s = s.replace("__REDIR_AMPGT__", "&>")
        for i, qs in enumerate(quoted_strings):
            s = s.replace(f"__QUOTED_{i}__", qs)
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
    (r"^command\s+", "command"),
    # time (measure command execution time)
    (r"^time\s+", "time"),
]

# --- Safe core command patterns ---
SAFE_COMMANDS = [
    # ── Git ───────────────────────────────────────────────────────────────
    # read operations (with optional -C flag)
    (
        r"^git\s+(-C\s+\S+\s+)?"
        r"(diff|log|status|show|branch|stash\s+list|bisect|worktree\s+list|fetch"
        r"|remote|tag|rev-parse|rev-list|ls-files|ls-tree|describe|shortlog"
        r"|reflog|blame|config|name-rev|for-each-ref|cherry|count-objects"
        r"|verify-commit|verify-tag|ls-remote)\b",
        "git read op",
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
    # ── Common read-only / info commands ──────────────────────────────────
    (
        r"^(ls|cat|head|tail|wc|find|grep|rg|file|which|pwd|du|df"
        r"|curl|wget|sort|uniq|cut|tr|awk|sed|xargs"
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


# --- Main Bash logic ---
segments = split_command_chain(cmd)

reasons = []
for segment in segments:
    core_cmd, wrappers = strip_wrappers(segment)
    reason = check_safe(core_cmd)
    if not reason:
        sys.exit(0)  # One unsafe segment = reject entire command
    if wrappers:
        reasons.append(f"{'+'.join(wrappers)} + {reason}")
    else:
        reasons.append(reason)

approve(" | ".join(reasons))
