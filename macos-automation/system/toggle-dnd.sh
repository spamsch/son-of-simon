#!/bin/bash
# ==============================================================================
# toggle-dnd.sh - Toggle Do Not Disturb via Shortcuts
# ==============================================================================
# Description:
#   Toggles Do Not Disturb (Focus mode) using a macOS Shortcut. Requires a
#   shortcut named "Toggle Do Not Disturb" to be set up in Shortcuts.app.
#   Provides setup instructions if the shortcut is not found.
#
# Usage:
#   ./toggle-dnd.sh
#   ./toggle-dnd.sh --on
#   ./toggle-dnd.sh --off
#
# Options:
#   --on          Turn Do Not Disturb on
#   --off         Turn Do Not Disturb off
#   (no args)     Toggle current state
#   -h, --help    Show this help message
#
# Example:
#   ./toggle-dnd.sh
#   ./toggle-dnd.sh --on
#   ./toggle-dnd.sh --off
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

# Check if shortcuts CLI exists
if ! command -v shortcuts &>/dev/null; then
    error_exit "shortcuts command not found. Requires macOS 12 (Monterey) or later."
fi

# Determine which shortcut to run based on action
if [[ "$ACTION" == "on" ]]; then
    SHORTCUT_NAME="Turn On Do Not Disturb"
elif [[ "$ACTION" == "off" ]]; then
    SHORTCUT_NAME="Turn Off Do Not Disturb"
else
    SHORTCUT_NAME="Toggle Do Not Disturb"
fi

# Check if the shortcut exists
if ! shortcuts list 2>/dev/null | grep -q "^${SHORTCUT_NAME}$"; then
    # Fall back to the toggle shortcut for on/off if specific ones don't exist
    if [[ -n "$ACTION" ]]; then
        SHORTCUT_NAME="Toggle Do Not Disturb"
        if ! shortcuts list 2>/dev/null | grep -q "^${SHORTCUT_NAME}$"; then
            echo "Shortcut 'Toggle Do Not Disturb' not found. To set up:"
            echo "  1. Open Shortcuts.app"
            echo "  2. Create a new shortcut named 'Toggle Do Not Disturb'"
            echo "  3. Add action: 'Set Focus' -> 'Do Not Disturb' -> Toggle"
            echo "  4. Save and try again"
            exit 1
        fi
    else
        echo "Shortcut 'Toggle Do Not Disturb' not found. To set up:"
        echo "  1. Open Shortcuts.app"
        echo "  2. Create a new shortcut named 'Toggle Do Not Disturb'"
        echo "  3. Add action: 'Set Focus' -> 'Do Not Disturb' -> Toggle"
        echo "  4. Save and try again"
        exit 1
    fi
fi

# Run the shortcut
if shortcuts run "$SHORTCUT_NAME" 2>/dev/null; then
    echo "Do Not Disturb toggled"
else
    error_exit "Failed to run shortcut '$SHORTCUT_NAME'"
fi
