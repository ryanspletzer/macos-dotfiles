"""Shared utilities for Claude Code PreToolUse enforcement hooks."""

import re


def strip_quoted_content(command: str) -> str:
    """Strip content that shouldn't be matched as actual command tokens.

    Removes (in order):
    1. Heredocs — <<EOF...EOF, <<'EOF'...EOF, <<-"EOF"...EOF
    2. Single-quoted strings — '...'
    3. Double-quoted strings — "..." (respects escaped quotes)
    4. Comments — # ... to end of line

    Returns the command with quoted/heredoc/comment content replaced by
    empty strings, so only real command tokens remain for keyword matching.
    """
    # 1. Heredocs: <<[-]?['"]?WORD['"]? ... WORD
    #    The delimiter line itself is consumed; everything between is removed.
    result = re.sub(
        r'<<-?\s*[\'"]?(\w+)[\'"]?.*?\n.*?\n\1\b',
        '',
        command,
        flags=re.DOTALL,
    )

    # 2. Single-quoted strings (no escape sequences in POSIX shells)
    result = re.sub(r"'[^']*'", '', result)

    # 3. Double-quoted strings (skip escaped quotes inside)
    result = re.sub(r'"(?:[^"\\]|\\.)*"', '', result)

    # 4. Shell comments: # to end of line
    #    Avoid stripping inside ${ } or #! shebangs at column 0
    result = re.sub(r'(?<![$!])\s#.*$', '', result, flags=re.MULTILINE)

    return result
