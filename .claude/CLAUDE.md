# Global Claude Code Rules

## Markdown

- ALL Markdown output must pass markdownlint-cli2; fix issues automatically,
  never ask whether to lint
- When creating markdownlint config files, use YAML format
  (`.markdownlint.yaml`) instead of JSONC
- Prefer a `line_length` of 120 over the default 80
- Follow the semantic line breaks convention for all prose in Markdown files:
  - Start each sentence on a new line
  - Add a line break after clauses separated by commas, semicolons,
    colons, or em dashes when it aids readability
  - Never break within a hyphenated word
  - These breaks are for source readability and diffs only;
    they must not change rendered output

## Git workflow

When re-syncing a branch with its base branch,
always prefer merge commits over rebasing.

## Planning

When creating implementation plans,
write them to `.claude/plan-*.md` at the project root:

- Use descriptive filenames like `.claude/plan-add-auth.md`
  or `.claude/plan-refactor-api-client.md`
- If the plan evolves during implementation,
  update the plan file to reflect the final approach

## VS Code project extensions

When working in a project/repo,
create `.vscode/extensions.json` with `recommendations` listing only the
extension IDs the project needs
(language support, linters, formatters, debuggers, framework tools, etc.).
If the repo already has an `extensions.json`,
merge into it rather than replacing it.
A shell-level `code` function in each shell config reads this file
and disables non-recommended extensions automatically.

Always-recommended (language-agnostic) extensions are listed in
`.claude/vscode-base-extensions.md` — include them in every project.
