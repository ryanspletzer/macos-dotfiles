# Claude Code–Specific Rules

@~/AGENTS.md

<!-- User-scope Claude Code file. Claude Code has no user-scope
     AGENTS.md, so this file stays as a thin shim.
     Shared cross-tool instructions live in ~/AGENTS.md (imported above).
     When the working directory is ~ itself, Claude Code (2.1.277+) reads
     ~/AGENTS.md natively and skips the duplicate import; everywhere else,
     and in sessions that cannot read AGENTS.md (Bedrock/Vertex, telemetry
     off, first session after an upgrade), the import carries it.
     Never add a CLAUDE.md at the ~ root: it would silently disable
     native AGENTS.md loading.
     Topic rules live in ~/.claude/rules/: vscode-extensions.md
     and markdown.md (path-scoped to **/*.md).
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
