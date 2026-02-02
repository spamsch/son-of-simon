#!/bin/bash
# ==============================================================================
# create-event.sh - Create a new calendar event
# ==============================================================================
# Description:
#   Creates a new event in the specified calendar with title, date/time,
#   location, and optional description.
#
# Usage:
#   ./create-event.sh --calendar "Work" --title "Meeting" --start "2026-01-30 14:00" --end "2026-01-30 15:00"
#   ./create-event.sh --calendar "Work" --title "Holiday" --date "2026-02-14" --all-day
#   ./create-event.sh --calendar "Work" --title "Standup" --start "2026-02-03 09:00" --duration 15
#
# Options:
#   --calendar <name>    Calendar name (required)
#   --title <text>       Event title (required)
#   --start <datetime>   Start date/time as "YYYY-MM-DD HH:MM" (required unless --all-day)
#   --end <datetime>     End date/time as "YYYY-MM-DD HH:MM"
#   --duration <mins>    Duration in minutes (alternative to --end)
#   --date <date>        Date for all-day events as "YYYY-MM-DD"
#   --all-day            Create an all-day event
#   --location <text>    Event location (optional)
#   --notes <text>       Event description/notes (optional)
#
# Example:
#   ./create-event.sh --calendar "Work" --title "Team Meeting" \
#       --start "2026-01-30 14:00" --end "2026-01-30 15:00" \
#       --location "Conference Room A"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
CALENDAR=""
TITLE=""
START=""
END=""
DURATION=""
DATE=""
ALL_DAY=false
LOCATION=""
NOTES=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --calendar)
            CALENDAR="$2"
            shift 2
            ;;
        --title)
            TITLE="$2"
            shift 2
            ;;
        --start)
            START="$2"
            shift 2
            ;;
        --end)
            END="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --date)
            DATE="$2"
            shift 2
            ;;
        --all-day)
            ALL_DAY=true
            shift
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --notes)
            NOTES="$2"
            shift 2
            ;;
        -h|--help)
            head -35 "$0" | tail -30
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate required fields
[[ -z "$CALENDAR" ]] && error_exit "--calendar is required"
[[ -z "$TITLE" ]] && error_exit "--title is required"

# Escape special characters
TITLE_ESCAPED=$(escape_for_applescript "$TITLE")
LOCATION_ESCAPED=$(escape_for_applescript "$LOCATION")
NOTES_ESCAPED=$(escape_for_applescript "$NOTES")

if [[ "$ALL_DAY" == "true" ]]; then
    [[ -z "$DATE" ]] && error_exit "--date is required for all-day events"

    # Parse the date
    DATE_FORMATTED=$(date -j -f "%Y-%m-%d" "$DATE" "+%B %d, %Y" 2>/dev/null)
    [[ -z "$DATE_FORMATTED" ]] && error_exit "Invalid date format. Use YYYY-MM-DD"

    osascript <<EOF
tell application "Calendar"
    try
        set targetCal to calendar "$CALENDAR"
    on error
        return "Error: Calendar '$CALENDAR' not found."
    end try

    tell targetCal
        set newEvent to make new event with properties {summary:"$TITLE_ESCAPED", start date:date "$DATE_FORMATTED", allday event:true}

        if "$LOCATION_ESCAPED" is not "" then
            set location of newEvent to "$LOCATION_ESCAPED"
        end if

        if "$NOTES_ESCAPED" is not "" then
            set description of newEvent to "$NOTES_ESCAPED"
        end if
    end tell

    return "Created all-day event: $TITLE_ESCAPED on $DATE_FORMATTED"
end tell
EOF
else
    [[ -z "$START" ]] && error_exit "--start is required for timed events"

    # Parse start date/time
    START_FORMATTED=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%B %d, %Y %I:%M %p" 2>/dev/null)
    [[ -z "$START_FORMATTED" ]] && error_exit "Invalid start format. Use 'YYYY-MM-DD HH:MM'"

    # Calculate or parse end time
    if [[ -n "$DURATION" ]]; then
        # Calculate end from duration
        START_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%s" 2>/dev/null)
        END_EPOCH=$((START_EPOCH + DURATION * 60))
        END_FORMATTED=$(date -j -f "%s" "$END_EPOCH" "+%B %d, %Y %I:%M %p" 2>/dev/null)
    elif [[ -n "$END" ]]; then
        END_FORMATTED=$(date -j -f "%Y-%m-%d %H:%M" "$END" "+%B %d, %Y %I:%M %p" 2>/dev/null)
        [[ -z "$END_FORMATTED" ]] && error_exit "Invalid end format. Use 'YYYY-MM-DD HH:MM'"
    else
        # Default to 1 hour duration
        START_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%s" 2>/dev/null)
        END_EPOCH=$((START_EPOCH + 3600))
        END_FORMATTED=$(date -j -f "%s" "$END_EPOCH" "+%B %d, %Y %I:%M %p" 2>/dev/null)
    fi

    osascript <<EOF
tell application "Calendar"
    try
        set targetCal to calendar "$CALENDAR"
    on error
        return "Error: Calendar '$CALENDAR' not found."
    end try

    tell targetCal
        set newEvent to make new event with properties {summary:"$TITLE_ESCAPED", start date:date "$START_FORMATTED", end date:date "$END_FORMATTED"}

        if "$LOCATION_ESCAPED" is not "" then
            set location of newEvent to "$LOCATION_ESCAPED"
        end if

        if "$NOTES_ESCAPED" is not "" then
            set description of newEvent to "$NOTES_ESCAPED"
        end if
    end tell

    return "Created event: $TITLE_ESCAPED at $START_FORMATTED"
end tell
EOF
fi
