#!/bin/bash
# ==============================================================================
# physical-click.sh - Perform physical mouse click on element
# ==============================================================================
# Description:
#   Uses cliclick to perform a real mouse click on an element identified by ref.
#   This bypasses anti-bot detection that blocks synthetic JavaScript events.
#
# Prerequisites:
#   - Run snapshot.sh first to generate refs
#   - cliclick installed (brew install cliclick)
#
# Usage:
#   ./physical-click.sh <ref>
#   ./physical-click.sh e21
#
# Arguments:
#   ref     Element reference from snapshot (e.g., e1, e2)
#
# Output:
#   JSON with success status and click coordinates
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/../lib/common.sh" ]]; then
    source "$SCRIPT_DIR/../lib/common.sh"
else
    error_exit() { echo "{\"success\": false, \"error\": \"$1\"}" >&2; exit 1; }
fi

REF=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            head -26 "$0" | tail -21
            exit 0
            ;;
        -*)
            error_exit "Unknown option: $1"
            ;;
        *)
            REF="$1"
            shift
            ;;
    esac
done

[[ -z "$REF" ]] && error_exit "Element ref is required (e.g., e1)"

# Check cliclick is installed
if ! command -v cliclick &> /dev/null; then
    error_exit "cliclick is required. Install with: brew install cliclick"
fi

# Check Safari window
WINDOW_COUNT=$(osascript -e 'tell application "Safari" to count of windows' 2>/dev/null)
if [[ "$WINDOW_COUNT" == "0" ]] || [[ -z "$WINDOW_COUNT" ]]; then
    echo '{"success": false, "error": "No Safari window open"}'
    exit 1
fi

# Check library
HAS_LIB=$(osascript -e 'tell application "Safari" to do JavaScript "typeof window.__ariaGetElement === '\''function'\''" in current tab of front window' 2>/dev/null)
if [[ "$HAS_LIB" != "true" ]]; then
    echo '{"success": false, "error": "ARIA library not loaded. Run snapshot.sh --inject first."}'
    exit 1
fi

# Get element position (relative to viewport)
ELEM_POS=$(osascript -e "tell application \"Safari\" to do JavaScript \"
var el = window.__ariaGetElement('$REF');
if (el) {
  var r = el.getBoundingClientRect();
  Math.round(r.left + r.width/2) + ',' + Math.round(r.top + r.height/2);
} else {
  'not_found';
}
\" in current tab of front window" 2>/dev/null)

if [[ "$ELEM_POS" == "not_found" ]] || [[ -z "$ELEM_POS" ]]; then
    echo "{\"success\": false, \"error\": \"Element $REF not found. Run snapshot again.\"}"
    exit 1
fi

# Get Safari window bounds
BOUNDS=$(osascript -e 'tell application "Safari" to bounds of front window' 2>/dev/null)
WIN_X=$(echo "$BOUNDS" | cut -d',' -f1 | tr -d ' ')
WIN_Y=$(echo "$BOUNDS" | cut -d',' -f2 | tr -d ' ')

# Parse element position
ELEM_X=$(echo "$ELEM_POS" | cut -d',' -f1)
ELEM_Y=$(echo "$ELEM_POS" | cut -d',' -f2)

# Safari toolbar offset (URL bar + tab bar)
TOOLBAR_OFFSET=75

# Calculate absolute screen coordinates
CLICK_X=$((WIN_X + ELEM_X))
CLICK_Y=$((WIN_Y + TOOLBAR_OFFSET + ELEM_Y))

# Small random delay before click (human-like)
sleep 0.$((RANDOM % 15 + 5))

# Perform physical click
cliclick c:"$CLICK_X","$CLICK_Y"
EXIT_CODE=$?

# Small delay after click
sleep 0.$((RANDOM % 10 + 3))

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "{\"success\": true, \"x\": $CLICK_X, \"y\": $CLICK_Y, \"ref\": \"$REF\"}"
else
    echo "{\"success\": false, \"error\": \"cliclick failed with code $EXIT_CODE\"}"
    exit 1
fi
