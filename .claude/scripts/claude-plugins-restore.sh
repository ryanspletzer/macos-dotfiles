#!/usr/bin/env bash
#
# claude-plugins-restore.sh
# Idempotently restores Claude Code marketplaces and plugins from manifest
#
# PURPOSE:
#   Reads the portable plugin manifest and ensures all listed marketplaces
#   and plugins are installed. Uses an idempotent get/test/set pattern:
#   only adds marketplaces or installs plugins that are missing.
#
# WHY THIS EXISTS:
#   When setting up Claude Code on a new machine (or after a clean install),
#   this script automates the restoration of your plugin configuration.
#   Safe to run multiple times - already-installed items are skipped.
#
# WORKFLOW:
#   1. List current marketplaces (claude plugin marketplace list)
#   2. Add any marketplaces from manifest that aren't present
#   3. List current plugins (claude plugin list)
#   4. Install any plugins from manifest that aren't present
#
# INPUT:
#   ~/.claude/plugin-manifest.json - Created by claude-plugins-export.sh
#
# USAGE:
#   ./claude-plugins-restore.sh
#
# DEPENDENCIES:
#   - jq (JSON processor)
#   - claude CLI (must be in PATH)
#

set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
MANIFEST_FILE="${CLAUDE_DIR}/plugin-manifest.json"

# Check for jq
if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed." >&2
    echo "Install with: brew install jq" >&2
    exit 1
fi

# Check manifest exists
if [[ ! -f "${MANIFEST_FILE}" ]]; then
    echo "Error: Manifest file not found: ${MANIFEST_FILE}" >&2
    echo "Run claude-plugins-export.sh first to create it." >&2
    exit 1
fi

# Check claude CLI is available
if ! command -v claude &>/dev/null; then
    echo "Error: claude CLI not found in PATH" >&2
    exit 1
fi

echo "Restoring Claude Code plugin configuration..."
echo ""

# Get current marketplaces
echo "=== Marketplaces ==="
current_marketplaces=$(claude plugin marketplace list 2>/dev/null || echo "")

# Read desired marketplaces from manifest
# Entries are either GitHub repo shorthand (owner/name) or git URLs (https://...)
while IFS= read -r entry; do
    [[ -z "${entry}" ]] && continue
    if echo "${current_marketplaces}" | grep -q "${entry}"; then
        echo "[OK] Marketplace already added: ${entry}"
    else
        echo "[ADD] Adding marketplace: ${entry}"
        claude plugin marketplace add "${entry}" || {
            echo "  [WARN] Failed to add marketplace: ${entry}" >&2
        }
    fi
done < <(jq -r '.marketplaces[]' "${MANIFEST_FILE}")

echo ""
echo "=== Plugins ==="

# Get current plugins
current_plugins=$(claude plugin list 2>/dev/null || echo "")

# Read desired plugins from manifest
while IFS= read -r plugin; do
    [[ -z "${plugin}" ]] && continue
    if echo "${current_plugins}" | grep -q "${plugin}"; then
        echo "[OK] Plugin already installed: ${plugin}"
    else
        echo "[INSTALL] Installing plugin: ${plugin}"
        claude plugin install "${plugin}" || {
            echo "  [WARN] Failed to install plugin: ${plugin}" >&2
        }
    fi
done < <(jq -r '.plugins[]' "${MANIFEST_FILE}")

echo ""
echo "Restore complete."
