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
readarray -t desired_marketplaces < <(jq -r '.marketplaces[]' "${MANIFEST_FILE}")

for repo in "${desired_marketplaces[@]}"; do
    # Extract marketplace name from repo (last part after /)
    # Note: This is a heuristic - the actual name may differ
    if echo "${current_marketplaces}" | grep -q "${repo}"; then
        echo "[OK] Marketplace already added: ${repo}"
    else
        echo "[ADD] Adding marketplace: ${repo}"
        claude plugin marketplace add "${repo}" || {
            echo "  [WARN] Failed to add marketplace: ${repo}" >&2
        }
    fi
done

echo ""
echo "=== Plugins ==="

# Get current plugins
current_plugins=$(claude plugin list 2>/dev/null || echo "")

# Read desired plugins from manifest
readarray -t desired_plugins < <(jq -r '.plugins[]' "${MANIFEST_FILE}")

for plugin in "${desired_plugins[@]}"; do
    if echo "${current_plugins}" | grep -q "${plugin}"; then
        echo "[OK] Plugin already installed: ${plugin}"
    else
        echo "[INSTALL] Installing plugin: ${plugin}"
        claude plugin install "${plugin}" || {
            echo "  [WARN] Failed to install plugin: ${plugin}" >&2
        }
    fi
done

echo ""
echo "Restore complete."
