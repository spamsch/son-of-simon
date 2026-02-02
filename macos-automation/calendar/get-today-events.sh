#!/bin/bash
# ==============================================================================
# get-today-events.sh - Get all events scheduled for today
# ==============================================================================
# Description:
#   Retrieves all calendar events for today across all calendars or a specific
#   calendar. Shows event time, title, location, and calendar name.
#
# Usage:
#   ./get-today-events.sh
#   ./get-today-events.sh --calendar "Work"
#
# Options:
#   --calendar <name>   Only show events from the specified calendar
#
# Output:
#   A chronologically sorted list of today's events
#
# Example:
#   ./get-today-events.sh
#   ./get-today-events.sh --calendar "Personal"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
CALENDAR_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --calendar)
            CALENDAR_NAME="$2"
            shift 2
            ;;
        -h|--help)
            head -28 "$0" | tail -23
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

if [[ -n "$CALENDAR_NAME" ]]; then
    osascript <<EOF
tell application "Calendar"
    set todayStart to current date
    set time of todayStart to 0
    set todayEnd to todayStart + (24 * 60 * 60)

    set output to "=== TODAY'S EVENTS: $CALENDAR_NAME ===" & return & return

    try
        set targetCal to calendar "$CALENDAR_NAME"
    on error
        return "Calendar '$CALENDAR_NAME' not found."
    end try

    set todayEvents to (events of targetCal whose start date >= todayStart and start date < todayEnd)

    if (count of todayEvents) is 0 then
        return "No events scheduled for today in '$CALENDAR_NAME'."
    end if

    repeat with evt in todayEvents
        if allday event of evt then
            set timeStr to "All Day"
        else
            set startTime to start date of evt
            set h to hours of startTime
            set m to minutes of startTime
            if m < 10 then set m to "0" & m
            set ampm to "AM"
            if h >= 12 then set ampm to "PM"
            if h > 12 then set h to h - 12
            if h is 0 then set h to 12
            set timeStr to h & ":" & m & " " & ampm
        end if

        set output to output & timeStr & " - " & summary of evt & return
        if location of evt is not "" then
            set output to output & "         Location: " & location of evt & return
        end if
    end repeat

    return output
end tell
EOF
else
    osascript <<'EOF'
tell application "Calendar"
    set todayStart to current date
    set time of todayStart to 0
    set todayEnd to todayStart + (24 * 60 * 60)

    set output to "=== TODAY'S EVENTS ===" & return & return
    set foundAny to false

    repeat with c in calendars
        set todayEvents to (events of c whose start date >= todayStart and start date < todayEnd)

        if (count of todayEvents) > 0 then
            set foundAny to true
            set output to output & "📅 " & name of c & return

            repeat with evt in todayEvents
                if allday event of evt then
                    set timeStr to "All Day"
                else
                    set startTime to start date of evt
                    set h to hours of startTime
                    set m to minutes of startTime
                    if m < 10 then set m to "0" & m
                    set ampm to "AM"
                    if h >= 12 then set ampm to "PM"
                    if h > 12 then set h to h - 12
                    if h is 0 then set h to 12
                    set timeStr to h & ":" & m & " " & ampm
                end if

                set output to output & "  " & timeStr & " - " & summary of evt & return
                if location of evt is not "" then
                    set output to output & "           Location: " & location of evt & return
                end if
            end repeat
            set output to output & return
        end if
    end repeat

    if not foundAny then
        return "No events scheduled for today."
    end if

    return output
end tell
EOF
fi
