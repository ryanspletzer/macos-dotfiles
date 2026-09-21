# Claude Code–Specific Rules

@~/.agents/AGENTS.md

<!-- User-scope Claude Code file. Claude Code has no user-scope
     AGENTS.md, so this file stays as a thin shim.
     The tool-neutral global core lives in ~/.agents/AGENTS.md (imported
     above); Claude Code never reads .agents/ on its own, so the import
     is the only path in. ~/AGENTS.md holds home-repo notes only and is
     read natively (2.1.277+) when the working directory is ~, or through
     the parent-directory walk-up in sessions under ~ such as ~/git/*.
     Never add a CLAUDE.md at the ~ root or in ~/git: it would silently
     disable native AGENTS.md loading for every session beneath it.
     Topic rules live in ~/.claude/rules/: vscode-extensions.md
     and markdown.md (path-scoped to **/*.md).
     The Markdown summary in the global core is intentionally always-on
     so it applies to brand-new files a path-scoped rule wouldn't catch;
     full markdown conventions stay in rules/markdown.md.
     PreToolUse hooks in ~/.agents/hooks/ (wired via settings.json)
     enforce the Python packaging rules. -->

## Model delegation

For coding tasks, use your judgement to delegate implementation work
to a subagent on an appropriately lower-power model:
`sonnet` for substantive implementation, `haiku` for trivial or mechanical edits.
Keep design, review, auditing, and synthesis in the main loop.
Rationale and cost context live in `~/.claude/cost-optimization.md`.
