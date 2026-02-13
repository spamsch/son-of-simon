#!/bin/bash
# ==============================================================================
# toggle-wifi.sh - Toggle WiFi on or off
# ==============================================================================
# Description:
#   Turns WiFi on, off, or toggles the current state. Auto-detects the WiFi
#   hardware device. Idempotent: reports if already in the desired state.
#
# Usage:
#   ./toggle-wifi.sh
#   ./toggle-wifi.sh --on
#   ./toggle-wifi.sh --off
#
# Options:
#   --on          Turn WiFi on
#   --off         Turn WiFi off
#   (no args)     Toggle current state
#   -h, --help    Show this help message
#
# Example:
#   ./toggle-wifi.sh --on
#   ./toggle-wifi.sh --off
#   ./toggle-wifi.sh
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

# Auto-detect WiFi device
WIFI_DEVICE=$(networksetup -listallhardwareports | awk '/Wi-Fi/{getline; print $2}')
[[ -z "$WIFI_DEVICE" ]] && error_exit "No WiFi device found"

# Get current state
CURRENT_POWER=$(networksetup -getairportpower "$WIFI_DEVICE" 2>/dev/null | awk '{print $NF}')

# Determine desired state
if [[ -z "$ACTION" ]]; then
    # Toggle
    if [[ "$CURRENT_POWER" == "On" ]]; then
        ACTION="off"
    else
        ACTION="on"
    fi
fi

# Apply
if [[ "$ACTION" == "on" ]]; then
    if [[ "$CURRENT_POWER" == "On" ]]; then
        echo "WiFi already on"
    else
        networksetup -setairportpower "$WIFI_DEVICE" on
        echo "WiFi turned on"
    fi
elif [[ "$ACTION" == "off" ]]; then
    if [[ "$CURRENT_POWER" == "Off" ]]; then
        echo "WiFi already off"
    else
        networksetup -setairportpower "$WIFI_DEVICE" off
        echo "WiFi turned off"
    fi
fi
