# Claude Code–Specific Rules

@~/AGENTS.md

<!-- Shared cross-tool instructions live in ~/AGENTS.md (imported above).
     Topic rules live in ~/.claude/rules/: git-workflow.md,
     vscode-extensions.md, and markdown.md (path-scoped to **/*.md).
     The Markdown summary in AGENTS.md is intentionally always-on so it
     applies to brand-new files a path-scoped rule wouldn't catch;
     full markdown conventions stay in rules/markdown.md.
     PreToolUse hooks in ~/.agents/hooks/ (wired via settings.json)
     enforce the Python packaging rules. -->

## Model delegation

For coding tasks, use your judgement to delegate implementation work
to a subagent on an appropriately lower-power model:
`sonnet` for substantive implementation, `haiku` for trivial or mechanical edits.
Keep design, review, auditing, and synthesis in the main loop.
Rationale and cost context live in `~/.claude/cost-optimization.md`.
