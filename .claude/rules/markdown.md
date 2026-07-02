---
paths:
  - "**/*.md"
---

# Markdown

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
