#!/bin/bash
# ==============================================================================
# execute-js.sh - Execute JavaScript in the current Safari tab
# ==============================================================================
# Description:
#   Executes arbitrary JavaScript code in Safari's current tab and returns
#   the result. Useful for extracting data from web pages.
#
# Usage:
#   ./execute-js.sh <javascript_code>
#   ./execute-js.sh "document.title"
#   ./execute-js.sh "JSON.stringify({url: location.href})"
#
# Arguments:
#   javascript_code   JavaScript code to execute (will be wrapped in eval)
#
# Output:
#   JSON with success status and the result of the JavaScript execution
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/../lib/common.sh" ]]; then
    source "$SCRIPT_DIR/../lib/common.sh"
else
    error_exit() { echo "{\"success\": false, \"error\": \"$1\"}" >&2; exit 1; }
fi

JS_CODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            head -22 "$0" | tail -17
            exit 0
            ;;
        -*)
            error_exit "Unknown option: $1"
            ;;
        *)
            JS_CODE="$1"
            shift
            ;;
    esac
done

[[ -z "$JS_CODE" ]] && error_exit "JavaScript code is required"

# Check Safari window
WINDOW_COUNT=$(osascript -e 'tell application "Safari" to count of windows' 2>/dev/null)
if [[ "$WINDOW_COUNT" == "0" ]] || [[ -z "$WINDOW_COUNT" ]]; then
    echo '{"success": false, "error": "No Safari window open"}'
    exit 1
fi

# Execute the JavaScript
# Use a temp file for complex JS to avoid escaping issues
TEMP_JS=$(mktemp)
echo "$JS_CODE" > "$TEMP_JS"

RESULT=$(osascript << EOF
set jsCode to read POSIX file "$TEMP_JS"
tell application "Safari"
    try
        set jsResult to do JavaScript jsCode in current tab of front window
        return jsResult
    on error errMsg
        return "ERROR:" & errMsg
    end try
end tell
EOF
)
EXIT_CODE=$?

rm -f "$TEMP_JS"

if [[ $EXIT_CODE -eq 0 ]]; then
    if [[ "$RESULT" == ERROR:* ]]; then
        ERROR_MSG="${RESULT#ERROR:}"
        echo "{\"success\": false, \"error\": \"JavaScript error: $ERROR_MSG\"}"
        exit 1
    else
        # Try to determine if result is already JSON
        if echo "$RESULT" | head -c1 | grep -q '[{[]'; then
            echo "{\"success\": true, \"result\": $RESULT}"
        else
            # Escape the result for JSON
            ESCAPED=$(echo "$RESULT" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' ' ')
            echo "{\"success\": true, \"result\": \"$ESCAPED\"}"
        fi
    fi
else
    echo "{\"success\": false, \"error\": \"AppleScript execution failed\"}"
    exit 1
fi
