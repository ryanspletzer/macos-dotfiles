# Claude Code Cost Optimization Reference

A human-facing reference (intentionally **not** loaded into context via `CLAUDE.md`,
so it costs zero tokens per session).
Optimize for **tokens processed per unit of work** —
this stretches the personal Max plan's usage limits **and**
lowers consumption spend on work API/Enterprise at the same time.

**On drift:** this file mixes two kinds of content —
durable policy/rubrics (how to think about the dials) and current configuration state
(what's actually enabled right now).
The second kind goes stale fast: an earlier revision claimed a Sonnet default
that had silently drifted to Opus,
and another listed a hook as "not yet applied" after it had already shipped.
Wherever this doc used to assert a current value, it now gives the command to check it live instead —
trust a command's output over any number written here.

## Default model & escalation

Two viable strategies, differing in where the expensive model sits:

1. **Sonnet-default, escalate up** — pin the global default to Sonnet
   (handles ~90% of coding tasks at a fraction of Opus/Fable token cost)
   and raise the model only for the hard step.
2. **Top-tier main loop, delegate down** — pin the default to Fable/Opus
   so judgment, design, and review get the strongest model,
   and delegate implementation work to Sonnet/Haiku subagents
   (the always-on rule lives in `~/AGENTS.md` under "Model delegation";
   pattern via Simon Willison's
   [Judgement](https://simonwillison.net/2026/Jul/3/judgement/) post).

Strategy 2 is current policy.
Either way, escalation/de-escalation stays narrow:

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

Check the current global default:

```sh
jq '.model' ~/.claude/settings.json
```

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

## Hooks run in parallel

Claude Code runs all hooks matching a given event/matcher **concurrently**, not sequentially,
and deduplicates identical handlers automatically
(confirmed against <https://code.claude.com/docs/en/hooks.md>).
Splitting checks into separate `PreToolUse` scripts therefore costs nothing in wall-clock time —
total latency is bounded by the slowest single hook, not the sum of all hooks.
Don't consolidate multiple hooks into one dispatcher script for speed;
only do it if the scripts need to share setup work or coordinate with each other.

## Subagents

- Implementation work is delegated to lower-tier subagents by judgement
  (see "Default model & escalation" above; the rule itself is in `~/AGENTS.md`).
- Delegate verbose operations (test runs, log scans, doc fetches) to subagents
  so bulky output stays in the subagent's context and only a summary returns to the main thread.
- Custom agents pin their tier in frontmatter (`model: sonnet|opus|haiku|inherit`).
  An unpinned agent inherits whatever model the parent session happens to be running —
  including an accidental Opus default — so always pin explicitly rather than relying on inherit.
- **Work / CI ceiling:** set `CLAUDE_CODE_SUBAGENT_MODEL` (env or settings) to force every
  subagent to one model regardless of frontmatter — a hard cost cap for headless/automation runs.

List every custom agent and its pinned model:

```sh
for f in ~/.claude/agents/*.md ~/git/*/.claude/agents/*.md; do
  [ -f "$f" ] && printf '%s: %s\n' "$f" "$(grep -m1 '^model:' "$f" || echo '(unpinned -- inherits session model)')"
done
```

## Plugins

Each **enabled** plugin injects its agents/skills/commands into context every session.
Audit with `/usage` + `/context`, then **disable** (not uninstall) anything not earning its context.
Re-enable on demand via `/plugin`.

List currently enabled plugins:

```sh
jq -r '.enabledPlugins | to_entries[] | select(.value) | .key' ~/.claude/settings.json
```

## Per-project model tiering

Pin a per-project default that overrides the global default by adding to
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

### Tier decisions

Recorded here because the *reasoning* is durable even when the *file* isn't —
use the command below to see whether a decision has actually been applied,
rather than trusting this list.

- **Haiku / Sonnet** — `neovm-lazyvim-tmux-learning`, `python_koans`: learning repos, low stakes.
- **Sonnet (default)** — `dev-machine-setup`, `ryanspletzer.github.io`,
  `vscode-selective-extensions`: normal project work, global default already covers it.
- **Opus** — `mcp-enterprise-auth`: security-sensitive auth work warrants the higher tier.

Check which repos actually have a pin applied vs. which still need one:

```sh
for f in ~/git/*/.claude/settings.json; do
  [ -f "$f" ] && printf '%s: %s\n' "$f" "$(jq -c '.model // "(none)"' "$f")"
done
```

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

- **TypeScript** — `typescript-lsp@claude-plugins-official`: `vscode-selective-extensions`
  (already enabled in `ryanspletzer.github.io`).
- **Python** — `pyright-lsp@claude-plugins-official`:
  `onenote-dump`, `python_koans`, `essential-math-for-data-science`.
- **PowerShell** — `powershell-editor-services@claude-code-lsps`:
  `PowerShellEX`, `powershell-style`.

Skip `gopls-lsp`, `rust-analyzer-lsp`, `swift-lsp`, `lua-lsp` until you work in those languages.

Check which LSP plugins are enabled in the current project:

```sh
jq -r '.enabledPlugins | to_entries[] | select(.value) | select(.key | endswith("-lsp")) | .key' .claude/settings.json
```

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
- Keep `CLAUDE.md` files lean (target < 200 lines);
  move workflow-specific instructions into load-on-demand skills
  (the `dotfiles-reference` skill is the model pattern).

Check current CLAUDE.md sizes:

```sh
wc -l ~/CLAUDE.md ~/.claude/CLAUDE.md ~/git/*/CLAUDE.md 2>/dev/null
```

## Remaining levers

- [x] `PreToolUse` hook (`filter-test-output.py`) filters test output to failures only —
  cuts tens of thousands of log tokens to hundreds.
- [ ] `MAX_THINKING_TOKENS=8000` to cap reasoning spend, or disable thinking in `/config`
  for simple work (effort currently left at default by choice).

## Sources

- <https://code.claude.com/docs/en/costs>
- <https://code.claude.com/docs/en/sub-agents>
- <https://code.claude.com/docs/en/hooks.md>
