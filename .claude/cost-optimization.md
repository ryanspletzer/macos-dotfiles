# Claude Code Cost Optimization Reference

A human-facing reference (intentionally **not** loaded into context via `CLAUDE.md`,
so it costs zero tokens per session).
Optimize for **tokens processed per unit of work** —
this stretches the personal Max plan's usage limits **and**
lowers consumption spend on work API/Enterprise at the same time.

## Default model & escalation

The global default is pinned to **Sonnet** in `~/.claude/settings.json` (`"model": "sonnet"`).
Sonnet handles ~90% of coding tasks well at a fraction of Opus token cost.
Escalate only when the task warrants it:

- `/model opus` — switch the current session to Opus for hard architecture or multi-step reasoning.
- `/fast` — when on Opus, faster output (still Opus, not a downgrade); UX, not a cost lever.
- `/effort` — raise reasoning per-task if a specific task needs deeper thinking
  (effort is otherwise left at the model default; nothing is pinned).
- `/model sonnet` — drop back down when the hard part is done.

## Measuring usage

- `/usage` — token breakdown attributed to skills, subagents, plugins, and MCP servers.
  Press `d` / `w` to toggle 24h / 7d.
- `/context` — what currently occupies the context window.
- Capture both **before and after** any change to verify the effect rather than guessing.

## Subagents

- Delegate verbose operations (test runs, log scans, doc fetches) to subagents
  so bulky output stays in the subagent's context and only a summary returns to the main thread.
- Custom agents pin their tier in frontmatter (`model: sonnet|opus|haiku|inherit`).
  `code-improvement-reviewer` is on `sonnet`; built-in `Explore` runs on `haiku`.
- **Work / CI ceiling:** set `CLAUDE_CODE_SUBAGENT_MODEL` (env or settings) to force every
  subagent to one model regardless of frontmatter — a hard cost cap for headless/automation runs.

## Plugins

Each **enabled** plugin injects its agents/skills/commands into context every session.
Currently enabled: `commit-commands`, `pr-review-toolkit`, `code-review`,
`security-guidance`, `episodic-memory`, `markdown-linter-fixer`.

Audit with `/usage` + `/context`, then **disable** (not uninstall) anything not earning its context:

- Check whether `pr-review-toolkit` and `code-review` both justify their footprint, or overlap.
- Check whether `episodic-memory` injection is worth its cost for everyday work.
- Re-enable on demand via `/plugin`.

## Per-project model tiering

Pin a per-project default that overrides the global Sonnet default by adding to
`<project>/.claude/settings.json`:

```jsonc
{
  "model": "haiku" // or "sonnet" / "opus" per the rubric below
}
```

### Tiering rubric

- **Haiku / Sonnet** — low-stakes, repetitive, or learning work:
  `anthropic-practice*`, `neovm-lazyvim-tmux-learning`, `python_koans`.
- **Sonnet (default)** — most real project work:
  `dev-machine-setup`, `ryanspletzer.github.io`, `vscode-selective-extensions`.
- **Opus** — genuinely hard reasoning / architecture:
  `mcp-enterprise-auth`.

Pin Opus only where work consistently needs it; otherwise escalate per-session with `/model opus`.

### Optional per-project compaction hint

For verbose-test projects, add to that project's `CLAUDE.md`:

```markdown
# Compact instructions
When compacting, focus on test output and code changes.
```

### Per-project code-intelligence (LSP) plugins

Code-intelligence plugins *reduce* spend on typed-language work:
a single "go to definition" replaces a grep plus reading several candidate files,
and they auto-report type errors after edits (no compiler run needed).
They are already installed (disabled) — enabling is a per-project flag flip, no download.

**Enable per-project, never globally** — each LSP adds tool definitions and spawns a
language server, so it should only load where that language lives.
Set it in `<project>/.claude/settings.json`:

```jsonc
{
  "enabledPlugins": {
    "csharp-lsp@claude-plugins-official": true
  }
}
```

Language → plugin → applicable repos:

- **C#** — `csharp-lsp@claude-plugins-official`:
  `anthropic-practice*` repos.
- **TypeScript** — `typescript-lsp@claude-plugins-official`:
  `vscode-selective-extensions` (already enabled in `ryanspletzer.github.io`).
- **Python** — `pyright-lsp@claude-plugins-official`:
  `onenote-dump`, `python_koans`, `essential-math-for-data-science`.
- **PowerShell** — `powershell-editor-services@claude-code-lsps`:
  `PowerShellEX`, `powershell-style`.

Skip `gopls-lsp`, `rust-analyzer-lsp`, `swift-lsp`, `lua-lsp` until you work in those languages.

## Work / Enterprise portability

Replicate the same patterns on the work machine (separate config):

- `settings.json` `"model": "sonnet"` default — same field, versioned.
- `CLAUDE_CODE_SUBAGENT_MODEL` ceiling for CI / headless runs.
- Prefer CLI tools (`gh`, `aws`, `gcloud`, `sentry-cli`) over MCP servers where possible —
  MCP tool defs are deferred but CLIs add no per-tool context tax at all.
- Be aware of org-level TPM/RPM rate-limit recommendations under Enterprise.

## Other levers (not yet applied)

- `MAX_THINKING_TOKENS=8000` to cap reasoning spend, or disable thinking in `/config`
  for simple work (effort currently left at default by choice).
- A `PreToolUse` Bash hook that filters test output to failures only —
  cuts tens of thousands of log tokens to hundreds; complements the existing safety hooks.
- Keep `CLAUDE.md` files lean (target < 200 lines); move workflow-specific instructions
  into load-on-demand skills (the `dotfiles-reference` skill is the model pattern).
  Current `CLAUDE.md` files are already well under target.

## Sources

- <https://code.claude.com/docs/en/costs>
- <https://code.claude.com/docs/en/sub-agents>
