#!/bin/bash
# ==============================================================================
# list-calendars.sh - List all available calendars
# ==============================================================================
# Description:
#   Lists all calendars available in Calendar.app, showing name, event count,
#   and whether the calendar is writable.
#
# Usage:
#   ./list-calendars.sh
#   ./list-calendars.sh --with-counts
#
# Options:
#   --with-counts   Include event counts for each calendar
#
# Example:
#   ./list-calendars.sh
#   ./list-calendars.sh --with-counts
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

WITH_COUNTS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-counts)
            WITH_COUNTS=true
            shift
            ;;
        -h|--help)
            head -24 "$0" | tail -19
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

if [[ "$WITH_COUNTS" == "true" ]]; then
    osascript <<'EOF'
tell application "Calendar"
    set output to "=== CALENDARS ===" & return & return

    repeat with c in calendars
        set calName to name of c
        set evtCount to count of events of c
        set isWritable to writable of c

        set output to output & "📅 " & calName & return
        set output to output & "   Events: " & evtCount & return

        if isWritable then
            set output to output & "   Writable: Yes" & return
        else
            set output to output & "   Writable: No (read-only)" & return
        end if

        set output to output & return
    end repeat

    return output
end tell
EOF
else
    osascript <<'EOF'
tell application "Calendar"
    set output to "=== CALENDARS ===" & return & return

    repeat with c in calendars
        set calName to name of c
        set isWritable to writable of c

        if isWritable then
            set output to output & "📅 " & calName & return
        else
            set output to output & "📅 " & calName & " (read-only)" & return
        end if
    end repeat

    return output
end tell
EOF
fi
