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

## Running markdownlint-cli2

markdownlint-cli2 discovers config only from the linted file's directory up to
the current working directory — never above the directory it is invoked from.
So run it from the directory that holds `.markdownlint.yaml`
(usually the repo root), or pass `--config <path-to>/.markdownlint.yaml`.
Linting from a subdirectory whose config lives higher up silently falls back to
the built-in default `line_length: 80` and can wrap lines to the wrong width.
