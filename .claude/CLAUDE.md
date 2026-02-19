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

## Git commit workflow

After making changes,
always copy the generated commit message to the clipboard via `pbcopy`,
then present the standard commit confirmation
so the user can choose whether to commit via Claude Code or manually.

- **Always**: Draft the commit message and copy it to the clipboard via `pbcopy`.
- **Then**: Present the commit for user approval (the usual "commit this" flow).
  The user may approve the commit or decline and use the clipboard message manually.

## Enforcement

- If Markdown linting errors are possible, run the markdown linter fixer skill
- Never ask whether to lint; lint by default
