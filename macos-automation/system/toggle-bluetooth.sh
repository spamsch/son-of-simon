#!/bin/bash
# ==============================================================================
# toggle-bluetooth.sh - Toggle Bluetooth on or off
# ==============================================================================
# Description:
#   Turns Bluetooth on, off, or toggles the current state. Uses JXA with
#   IOBluetooth framework. Falls back to blueutil if available.
#   Idempotent: reports if already in the desired state.
#
# Usage:
#   ./toggle-bluetooth.sh
#   ./toggle-bluetooth.sh --on
#   ./toggle-bluetooth.sh --off
#
# Options:
#   --on          Turn Bluetooth on
#   --off         Turn Bluetooth off
#   (no args)     Toggle current state
#   -h, --help    Show this help message
#
# Example:
#   ./toggle-bluetooth.sh --on
#   ./toggle-bluetooth.sh --off
#   ./toggle-bluetooth.sh
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
            head -26 "$0" | tail -21
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Get current Bluetooth state
get_bt_state() {
    if command -v blueutil &>/dev/null; then
        local power
        power=$(blueutil -p 2>/dev/null)
        if [[ "$power" == "1" ]]; then
            echo "on"
        else
            echo "off"
        fi
    else
        local state
        state=$(osascript -l JavaScript -e '
ObjC.import("IOBluetooth");
$.IOBluetoothPreferenceGetControllerPowerState();
' 2>/dev/null)
        if [[ "$state" == "1" ]]; then
            echo "on"
        else
            echo "off"
        fi
    fi
}

# Set Bluetooth state (1 for on, 0 for off)
set_bt_state() {
    local desired="$1"
    if command -v blueutil &>/dev/null; then
        blueutil -p "$desired" 2>/dev/null
    else
        osascript -l JavaScript -e "
ObjC.import('IOBluetooth');
$.IOBluetoothPreferenceSetControllerPowerState($desired);
" 2>/dev/null
    fi
}

# Get current state
CURRENT_STATE=$(get_bt_state)

# Determine desired state
if [[ -z "$ACTION" ]]; then
    # Toggle
    if [[ "$CURRENT_STATE" == "on" ]]; then
        ACTION="off"
    else
        ACTION="on"
    fi
fi

# Apply
if [[ "$ACTION" == "on" ]]; then
    if [[ "$CURRENT_STATE" == "on" ]]; then
        echo "Bluetooth already on"
    else
        set_bt_state 1
        echo "Bluetooth turned on"
    fi
elif [[ "$ACTION" == "off" ]]; then
    if [[ "$CURRENT_STATE" == "off" ]]; then
        echo "Bluetooth already off"
    else
        set_bt_state 0
        echo "Bluetooth turned off"
    fi
fi
