# Global Claude Code Rules

## Markdown quality

- ALL Markdown output must pass markdownlint-cli2
- Fix all MD0xx / MD01x issues automatically
- Use CommonMark-compatible Markdown
- No trailing whitespace
- Proper blank lines around lists and code blocks
- Headings must increment by one level (no H1 → H3 skips)
- Prefer a `line_length` of 120 over the default 80
- When creating markdownlint config files, use YAML format
  (`.markdownlint.yaml`) instead of JSONC

## Semantic line breaks

Follow the semantic line breaks convention for all prose in Markdown files:

- Start each sentence on a new line
- Add a line break after clauses separated by commas, semicolons,
  colons, or em dashes when it aids readability
- Keep lines under ~120 characters where practical
  (links and code spans may exceed this)
- Never break within a hyphenated word
- These breaks are for source readability and diffs only;
  they must not change rendered output

## Git workflow

After making changes,
draft a commit message and present the standard commit confirmation
for user approval.

When re-syncing a branch with its base branch,
always prefer merge commits over rebasing.

## GPG commit signing and sandbox setup

GPG commit signing is enabled globally.
The global `~/.claude/settings.json` includes both
`permissions.additionalDirectories` (filesystem write access to `~/.gnupg`)
and `sandbox.network.allowUnixSockets` (GPG agent socket communication).
No per-project configuration is needed for GPG signing.

## Planning

When creating implementation plans,
write them to `.claude/plan-*.md` at the project root:

- Use descriptive filenames like `.claude/plan-add-auth.md`
  or `.claude/plan-refactor-api-client.md`
- If the plan evolves during implementation,
  update the plan file to reflect the final approach

## VS Code project launcher

When working in a project/repo,
create `.vscode/extensions.json` and a `.code.sh` launch script
so VS Code opens with only the extensions relevant to that project.
See `~/.claude/vs-code-launcher.md` for the full template and guidelines.

## Enforcement

- If Markdown linting errors are possible, run the markdown linter fixer skill
- Never ask whether to lint; lint by default
