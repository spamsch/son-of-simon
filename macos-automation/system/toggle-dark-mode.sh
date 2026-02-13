#!/bin/bash
# ==============================================================================
# toggle-dark-mode.sh - Toggle macOS dark mode on or off
# ==============================================================================
# Description:
#   Enables, disables, or toggles macOS dark mode. Checks the current state
#   first for idempotent behavior.
#
# Usage:
#   ./toggle-dark-mode.sh
#   ./toggle-dark-mode.sh --on
#   ./toggle-dark-mode.sh --off
#
# Options:
#   --on          Enable dark mode
#   --off         Disable dark mode
#   (no args)     Toggle current state
#   -h, --help    Show this help message
#
# Example:
#   ./toggle-dark-mode.sh --on
#   ./toggle-dark-mode.sh --off
#   ./toggle-dark-mode.sh
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
ACTION=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --on)
            ACTION="on"
            shift
            ;;
        --off)
            ACTION="off"
            shift
            ;;
        -h|--help)
            head -25 "$0" | tail -20
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Get current state
CURRENT_STATE=$(osascript -e 'tell application "System Events" to tell appearance preferences to get dark mode' 2>/dev/null)

# Determine desired state
if [[ -z "$ACTION" ]]; then
    # Toggle
    if [[ "$CURRENT_STATE" == "true" ]]; then
        ACTION="off"
    else
        ACTION="on"
    fi
fi

# Apply
if [[ "$ACTION" == "on" ]]; then
    if [[ "$CURRENT_STATE" == "true" ]]; then
        echo "Dark mode already enabled"
    else
        osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to true' 2>/dev/null
        echo "Dark mode enabled"
    fi
elif [[ "$ACTION" == "off" ]]; then
    if [[ "$CURRENT_STATE" == "false" ]]; then
        echo "Dark mode already disabled"
    else
        osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to false' 2>/dev/null
        echo "Dark mode disabled"
    fi
fi
