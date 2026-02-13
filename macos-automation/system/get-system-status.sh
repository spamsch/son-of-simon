#!/bin/bash
# ==============================================================================
# get-system-status.sh - Report current macOS system status
# ==============================================================================
# Description:
#   Reports the current state of key system settings including WiFi, Bluetooth,
#   volume, dark mode, and Do Not Disturb.
#
# Usage:
#   ./get-system-status.sh
#
# Options:
#   -h, --help    Show this help message
#
# Example:
#   ./get-system-status.sh
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            head -18 "$0" | tail -13
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# --- WiFi ---
WIFI_DEVICE=$(networksetup -listallhardwareports | awk '/Wi-Fi/{getline; print $2}')
if [[ -n "$WIFI_DEVICE" ]]; then
    WIFI_POWER=$(networksetup -getairportpower "$WIFI_DEVICE" 2>/dev/null | awk '{print $NF}')
    if [[ "$WIFI_POWER" == "On" ]]; then
        WIFI_NETWORK=$(networksetup -getairportnetwork "$WIFI_DEVICE" 2>/dev/null | sed 's/^Current Wi-Fi Network: //')
        if [[ "$WIFI_NETWORK" == "You are not associated with an AirPort network." ]]; then
            WIFI_STATUS="On (not connected)"
        else
            WIFI_STATUS="On ($WIFI_NETWORK)"
        fi
    else
        WIFI_STATUS="Off"
    fi
else
    WIFI_STATUS="No WiFi device found"
fi

# --- Bluetooth ---
BT_STATE=$(osascript -l JavaScript -e '
ObjC.import("IOBluetooth");
var state = $.IOBluetoothPreferenceGetControllerPowerState();
state == 1 ? "On" : "Off";
' 2>/dev/null)
if [[ -z "$BT_STATE" ]]; then
    BT_STATE="Unknown"
fi

# --- Volume ---
VOLUME_LEVEL=$(osascript -e 'output volume of (get volume settings)' 2>/dev/null)
VOLUME_MUTED=$(osascript -e 'output muted of (get volume settings)' 2>/dev/null)
if [[ "$VOLUME_MUTED" == "true" ]]; then
    VOLUME_STATUS="$VOLUME_LEVEL% (muted)"
else
    VOLUME_STATUS="$VOLUME_LEVEL%"
fi

# --- Dark Mode ---
DARK_MODE=$(osascript -e 'tell application "System Events" to tell appearance preferences to get dark mode' 2>/dev/null)
if [[ "$DARK_MODE" == "true" ]]; then
    DARK_MODE_STATUS="On"
else
    DARK_MODE_STATUS="Off"
fi

# --- Do Not Disturb ---
# DND is hard to detect reliably; best-effort check
DND_STATUS="Unknown"
DND_VALUE=$(defaults read com.apple.controlcenter "NSStatusItem Visible FocusModes" 2>/dev/null)
if [[ "$DND_VALUE" == "1" ]]; then
    DND_STATUS="Focus active (best effort)"
elif [[ "$DND_VALUE" == "0" ]]; then
    DND_STATUS="Off (best effort)"
fi

# --- Output ---
echo "=== SYSTEM STATUS ==="
echo ""
echo "WiFi: $WIFI_STATUS"
echo "Bluetooth: $BT_STATE"
echo "Volume: $VOLUME_STATUS"
echo "Dark Mode: $DARK_MODE_STATUS"
echo "Do Not Disturb: $DND_STATUS"
