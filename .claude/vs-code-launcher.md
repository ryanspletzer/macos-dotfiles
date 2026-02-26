# VS Code Project Launcher

When working in a project/repo,
create or update two files so VS Code launches with only the
extensions relevant to that project.

## `.vscode/extensions.json`

Populate `recommendations` with the extension IDs the project actually needs
(language support, linters, formatters, debuggers, framework tools, etc.).
Choose extensions based on the languages, frameworks, and tooling in the repo.
Include `unwantedRecommendations` when specific extensions are known
to conflict or cause problems.

If the repo already has an `extensions.json`,
merge into it rather than replacing it.

## `.code.sh`

Create a launch script at the project root with this template:

```bash
#!/usr/bin/env bash
# Launch VS Code with only the extensions recommended for this project.
# Reads .vscode/extensions.json and disables everything else.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTENSIONS_JSON="$SCRIPT_DIR/.vscode/extensions.json"

if [[ ! -f "$EXTENSIONS_JSON" ]]; then
  echo "No .vscode/extensions.json found — launching VS Code normally." >&2
  code "$SCRIPT_DIR"
  exit 0
fi

# Wanted extensions (lowercased for case-insensitive comparison)
mapfile -t WANTED < <(
  jq -r '.recommendations[]' "$EXTENSIONS_JSON" | tr '[:upper:]' '[:lower:]'
)

DISABLE_FLAGS=()
while IFS= read -r ext; do
  ext_lower="${ext,,}"
  match=false
  for wanted in "${WANTED[@]}"; do
    if [[ "$ext_lower" == "$wanted" ]]; then
      match=true
      break
    fi
  done
  if [[ "$match" == false ]]; then
    DISABLE_FLAGS+=("--disable-extension" "$ext")
  fi
done < <(code --list-extensions)

code "${DISABLE_FLAGS[@]}" "$SCRIPT_DIR"
```

## Guidelines

- The script requires `jq`
- Mark it executable: `chmod +x .code.sh`
- Extension ID comparison is case-insensitive
- If `.vscode/extensions.json` is missing,
  the script falls back to a normal VS Code launch
- Do not create these files in the home folder repo itself;
  only in actual project/repo directories
