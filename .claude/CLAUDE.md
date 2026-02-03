# Global Claude Code Rules

## Markdown quality

- ALL Markdown output must pass markdownlint-cli2
- Fix all MD0xx / MD01x issues automatically
- Use CommonMark-compatible Markdown
- No trailing whitespace
- Proper blank lines around lists and code blocks
- Headings must increment by one level (no H1 → H3 skips)
- When creating markdownlint config files, use YAML format
  (`.markdownlint.yaml`) instead of JSONC

## Enforcement

- If Markdown linting errors are possible, run the markdown linter fixer skill
- Never ask whether to lint; lint by default
