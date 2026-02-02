#!/usr/bin/env bash
#
# claude-plugins-export.sh
# Exports Claude Code marketplaces and plugins to a portable manifest
#
# PURPOSE:
#   Claude Code stores plugin configuration in JSON files that contain
#   machine-specific paths (install locations, cache paths). This script
#   extracts only the portable data (GitHub repo names for marketplaces,
#   plugin identifiers) into a manifest that can be version-controlled
#   and used to restore the same plugin setup on another machine.
#
# WHY THIS EXISTS:
#   When setting up Claude Code on a new machine, manually re-adding
#   marketplaces and reinstalling plugins is tedious. This script pairs
#   with claude-plugins-restore.sh to enable:
#   1. Export current config on machine A
#   2. Commit manifest to dotfiles repo
#   3. Pull dotfiles on machine B
#   4. Run restore script to replicate setup
#
# SOURCE FILES (read-only):
#   ~/.claude/plugins/known_marketplaces.json  - Marketplace registrations
#   ~/.claude/plugins/installed_plugins.json   - Installed plugin records
#
# OUTPUT:
#   ~/.claude/plugin-manifest.json - Portable manifest (git-tracked)
#
# USAGE:
#   ./claude-plugins-export.sh
#
# DEPENDENCIES:
#   - jq (JSON processor)
#

set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
PLUGINS_DIR="${CLAUDE_DIR}/plugins"
MARKETPLACES_FILE="${PLUGINS_DIR}/known_marketplaces.json"
INSTALLED_FILE="${PLUGINS_DIR}/installed_plugins.json"
MANIFEST_FILE="${CLAUDE_DIR}/plugin-manifest.json"

# Check for jq
if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed." >&2
    echo "Install with: brew install jq" >&2
    exit 1
fi

# Check source files exist
if [[ ! -f "${MARKETPLACES_FILE}" ]]; then
    echo "Error: Marketplaces file not found: ${MARKETPLACES_FILE}" >&2
    exit 1
fi

if [[ ! -f "${INSTALLED_FILE}" ]]; then
    echo "Error: Installed plugins file not found: ${INSTALLED_FILE}" >&2
    exit 1
fi

echo "Exporting Claude Code plugin configuration..."

# Extract marketplace GitHub repos
marketplaces=$(jq -r '[.[] | .source.repo] | sort' "${MARKETPLACES_FILE}")

# Extract plugin names (keys from the plugins object)
plugins=$(jq -r '[.plugins | keys[]] | sort' "${INSTALLED_FILE}")

# Create the manifest
jq -n \
    --argjson marketplaces "${marketplaces}" \
    --argjson plugins "${plugins}" \
    '{
        "marketplaces": $marketplaces,
        "plugins": $plugins
    }' > "${MANIFEST_FILE}"

echo "Manifest written to: ${MANIFEST_FILE}"
echo ""
echo "Contents:"
jq '.' "${MANIFEST_FILE}"
