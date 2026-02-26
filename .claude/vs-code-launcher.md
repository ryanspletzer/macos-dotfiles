# VS Code Project Launcher

When working in a project/repo,
create or update these files so VS Code launches with only the
extensions relevant to that project.

## `.vscode/extensions.json`

Populate `recommendations` with the extension IDs the project actually needs
(language support, linters, formatters, debuggers, framework tools, etc.).
Choose extensions based on the languages, frameworks, and tooling in the repo.
Include `unwantedRecommendations` when specific extensions are known
to conflict or cause problems.

If the repo already has an `extensions.json`,
merge into it rather than replacing it.

## `.code.sh` (bash)

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

## `.code.ps1` (PowerShell)

Create a cross-platform PowerShell launch script with this template:

```powershell
#!/usr/bin/env pwsh
# Launch VS Code with only the extensions recommended for this project.
# Reads .vscode/extensions.json and disables everything else.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ExtensionsJson = Join-Path $ScriptDir '.vscode' 'extensions.json'

if (-not (Test-Path $ExtensionsJson)) {
    Write-Warning 'No .vscode/extensions.json found — launching VS Code normally.'
    code $ScriptDir
    return
}

$Wanted = (Get-Content $ExtensionsJson -Raw | ConvertFrom-Json).recommendations
$Installed = code --list-extensions

$DisableFlags = @()
foreach ($Ext in $Installed) {
    if ($Ext -notin $Wanted) {
        $DisableFlags += '--disable-extension'
        $DisableFlags += $Ext
    }
}

code @DisableFlags $ScriptDir
```

## Guidelines

- The bash script requires `jq`; the PowerShell script uses native JSON parsing
- Mark the bash script executable: `chmod +x .code.sh`
- Extension ID comparison is case-insensitive in both scripts
  (`-notin` is case-insensitive by default in PowerShell)
- If `.vscode/extensions.json` is missing,
  both scripts fall back to a normal VS Code launch
- Do not create these files in the home folder repo itself;
  only in actual project/repo directories
