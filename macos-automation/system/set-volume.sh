#!/bin/bash
# ==============================================================================
# set-volume.sh - Set system volume level and mute state
# ==============================================================================
# Description:
#   Sets the system output volume level (0-100) and/or mute/unmute state.
#   Can combine level and mute options in a single call. Reports the
#   resulting state after changes are applied.
#
# Usage:
#   ./set-volume.sh --level 50
#   ./set-volume.sh --mute
#   ./set-volume.sh --unmute
#   ./set-volume.sh --level 75 --unmute
#
# Options:
#   --level <0-100>   Set volume level (0 to 100)
#   --mute            Mute audio output
#   --unmute          Unmute audio output
#   -h, --help        Show this help message
#
# Example:
#   ./set-volume.sh --level 50
#   ./set-volume.sh --mute
#   ./set-volume.sh --level 30 --unmute
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
LEVEL=""
MUTE_ACTION=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --level)
            LEVEL="$2"
            shift 2
            ;;
        --mute)
            MUTE_ACTION="mute"
            shift
            ;;
        --unmute)
            MUTE_ACTION="unmute"
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

# Validate at least one argument
[[ -z "$LEVEL" && -z "$MUTE_ACTION" ]] && error_exit "Please specify --level, --mute, or --unmute"

# Validate level range
if [[ -n "$LEVEL" ]]; then
    if ! [[ "$LEVEL" =~ ^[0-9]+$ ]] || [[ "$LEVEL" -lt 0 ]] || [[ "$LEVEL" -gt 100 ]]; then
        error_exit "Volume level must be a number between 0 and 100"
    fi
fi

# Apply volume level
if [[ -n "$LEVEL" ]]; then
    osascript -e "set volume output volume $LEVEL" 2>/dev/null
fi

# Apply mute/unmute
if [[ "$MUTE_ACTION" == "mute" ]]; then
    osascript -e 'set volume output muted true' 2>/dev/null
elif [[ "$MUTE_ACTION" == "unmute" ]]; then
    osascript -e 'set volume output muted false' 2>/dev/null
fi

# Report current state
CURRENT_LEVEL=$(osascript -e 'output volume of (get volume settings)' 2>/dev/null)
CURRENT_MUTED=$(osascript -e 'output muted of (get volume settings)' 2>/dev/null)

if [[ "$CURRENT_MUTED" == "true" ]]; then
    echo "Volume: ${CURRENT_LEVEL}% (muted)"
else
    echo "Volume: ${CURRENT_LEVEL}%"
fi
