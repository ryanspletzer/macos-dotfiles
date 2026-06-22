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
- `/effort` — raise reasoning per-task if a specific task needs deeper thinking,
  then drop it back: thinking tokens bill as **output**,
  so a high-effort task can out-cost a higher model tier
  (effort is otherwise left at the model default; nothing is pinned).
- `/model sonnet` — drop back down when the hard part is done.

**Escalate narrowly:** raise model *or* effort for the single hard step,
then de-escalate immediately —
the cost discipline is symmetric for both dials.

## Measuring usage

- `/usage` — token breakdown attributed to skills, subagents, plugins, and MCP servers.
  Press `d` / `w` to toggle 24h / 7d.
- `/context` — what currently occupies the context window.
- Capture both **before and after** any change to verify the effect rather than guessing.

## Caching & session cadence

Prompt caching is a first-order cost lever, not a detail:
the system prompt, tools, and conversation prefix are cached and re-read
at a fraction of input cost on each turn — but the cache has a **5-minute TTL**.

- A **warm** session (steady back-and-forth) keeps re-reading context at cache rates;
  a **cold** resume after a long idle pays full input price to rebuild the prefix.
- Batch related work into one active session rather than returning to it hours later.
- Anything that sleeps or polls on a long interval (> 5 min) loses the cache between wakeups —
  prefer a tight cadence or accept one cold rebuild,
  not repeated 5–10 min polls that each pay the miss.

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

Two dials, not one — **model × effort**.
Thinking tokens bill as output,
so effort is the second-biggest lever after model tier:

| Work type | Model | Effort |
| --- | --- | --- |
| Low-stakes, repetitive, or learning | Haiku / Sonnet | low / default |
| Most real project work | Sonnet (default) | default |
| Genuinely hard reasoning / architecture | Opus | high — for the hard step only, then drop back |

Repos by tier:

- **Haiku / Sonnet** — `neovm-lazyvim-tmux-learning`, `python_koans`.
- **Sonnet (default)** — `dev-machine-setup`, `ryanspletzer.github.io`, `vscode-selective-extensions`.
- **Opus** — `mcp-enterprise-auth`.

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

## Output & context hygiene

Output tokens are the expensive tokens;
resident context is a recurring per-turn tax.

- The tracked **Concise** output style trims response verbosity —
  it is itself a cost lever, not just a UX preference.
- `/clear` between unrelated tasks drops dead context so it stops riding along every turn.
- Everything resident in the context window is re-processed each turn,
  so the "keep `CLAUDE.md` lean" point below is about this recurring tax,
  not a one-time cost.

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
