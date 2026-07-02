# Global Claude Code Rules

<!-- Topic rules live in ~/.claude/rules/: git-workflow.md,
     vscode-extensions.md, and markdown.md (path-scoped to **/*.md).
     The Markdown summary below is intentionally always-on so it applies to
     brand-new files a path-scoped rule wouldn't catch; full markdown
     conventions stay in rules/markdown.md. -->

## Markdown

When creating or editing any Markdown — including brand-new files —
the output must pass markdownlint-cli2 (fix issues automatically, never ask)
and use semantic line breaks (one sentence per line).
Full conventions live in `~/.claude/rules/markdown.md`,
loaded automatically when working with existing `.md` files.

## Python packaging

Never use bare `pip install` or `pip3 install` —
the system Python is externally managed (PEP 668) and Homebrew-owned.
Use `uv pip install` (inside a venv),
`uv add` (for project dependencies),
or `uv tool install` / `uvx` (for standalone CLI tools) instead.
Never use `pipx` —
use `uvx` (replaces `pipx run`) or `uv tool install` (replaces `pipx install`).
PreToolUse hooks enforce both rules.
