#!/usr/bin/env bash
# Fetch / update PowerShell Editor Services (PSES) for Emacs eglot.
#
# Installs the bundle into ~/.config/emacs/powershell-editor-services/, which is
# the -BundledModulesPath. The LSP entry point is then:
#   ~/.config/emacs/powershell-editor-services/PowerShellEditorServices/Start-EditorServices.ps1
#
# PSES is NOT on Homebrew (it ships as a PowerShell module in a GitHub release
# zip). This keeps the Emacs copy independent of Neovim/Mason. Re-run any time
# to update to the latest release.
set -euo pipefail

dest="${HOME}/.config/emacs/powershell-editor-services"
api="https://api.github.com/repos/PowerShell/PowerShellEditorServices/releases/latest"

echo "Resolving latest PSES release..."
url="$(curl -fsSL "${api}" \
  | grep -oE 'https://[^"]*/PowerShellEditorServices\.zip' \
  | head -1)"

if [[ -z "${url}" ]]; then
  echo "error: could not determine PSES download URL from ${api}" >&2
  exit 1
fi

echo "Downloading: ${url}"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
curl -fsSL "${url}" -o "${tmp}/pses.zip"

echo "Installing to: ${dest}"
rm -rf "${dest}"
mkdir -p "${dest}"
unzip -q "${tmp}/pses.zip" -d "${dest}"

start="${dest}/PowerShellEditorServices/Start-EditorServices.ps1"
if [[ -f "${start}" ]]; then
  echo "PSES installed. Entry point:"
  echo "  ${start}"
else
  echo "warning: expected start script not found at ${start}" >&2
  echo "Unpacked contents:" >&2
  ls -1 "${dest}" >&2
  exit 1
fi
