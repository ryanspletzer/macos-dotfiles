# VS Code project extensions

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
