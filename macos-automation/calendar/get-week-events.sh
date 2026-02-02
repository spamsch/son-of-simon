#!/bin/bash
# ==============================================================================
# get-week-events.sh - Get all events for the upcoming week
# ==============================================================================
# Description:
#   Retrieves all calendar events for the next 7 days (or custom range),
#   organized by day. Shows time, title, location, and calendar name.
#
# Usage:
#   ./get-week-events.sh
#   ./get-week-events.sh --days 14
#   ./get-week-events.sh --calendar "Work"
#
# Options:
#   --days <n>          Number of days to look ahead (default: 7)
#   --calendar <name>   Only show events from the specified calendar
#
# Example:
#   ./get-week-events.sh
#   ./get-week-events.sh --days 30 --calendar "Personal"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
DAYS=7
CALENDAR_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --calendar)
            CALENDAR_NAME="$2"
            shift 2
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

osascript <<EOF
tell application "Calendar"
    set startDate to current date
    set time of startDate to 0
    set endDate to startDate + ($DAYS * 24 * 60 * 60)

    set output to "=== NEXT $DAYS DAYS ===" & return & return

    set calList to {}
    if "$CALENDAR_NAME" is not "" then
        try
            set calList to {calendar "$CALENDAR_NAME"}
        on error
            return "Calendar '$CALENDAR_NAME' not found."
        end try
    else
        set calList to calendars
    end if

    set foundAny to false

    repeat with c in calList
        set periodEvents to (events of c whose start date >= startDate and start date < endDate)

        if (count of periodEvents) > 0 then
            set foundAny to true
            set output to output & "📅 " & name of c & return

            repeat with evt in periodEvents
                set evtDate to start date of evt
                set dateStr to (weekday of evtDate as string) & ", " & (month of evtDate as string) & " " & (day of evtDate)

                if allday event of evt then
                    set timeStr to "All Day"
                else
                    set h to hours of evtDate
                    set m to minutes of evtDate
                    if m < 10 then set m to "0" & m
                    set ampm to "AM"
                    if h >= 12 then set ampm to "PM"
                    if h > 12 then set h to h - 12
                    if h is 0 then set h to 12
                    set timeStr to h & ":" & m & " " & ampm
                end if

                set output to output & "  " & dateStr & return
                set output to output & "    " & timeStr & " - " & summary of evt & return

                if location of evt is not "" then
                    set output to output & "    Location: " & location of evt & return
                end if
            end repeat
            set output to output & return
        end if
    end repeat

    if not foundAny then
        return "No events scheduled for the next $DAYS days."
    end if

    return output
end tell
EOF
