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
