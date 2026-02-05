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

    # Parse the date components (locale-independent)
    YEAR=$(date -j -f "%Y-%m-%d" "$DATE" "+%Y" 2>/dev/null)
    MONTH=$(date -j -f "%Y-%m-%d" "$DATE" "+%-m" 2>/dev/null)
    DAY=$(date -j -f "%Y-%m-%d" "$DATE" "+%-d" 2>/dev/null)
    [[ -z "$YEAR" ]] && error_exit "Invalid date format. Use YYYY-MM-DD"

    osascript <<EOF
tell application "Calendar"
    try
        set targetCal to calendar "$CALENDAR"
    on error
        return "Error: Calendar '$CALENDAR' not found."
    end try

    -- Build date programmatically (locale-independent)
    set startDate to current date
    set year of startDate to $YEAR
    set month of startDate to $MONTH
    set day of startDate to $DAY
    set hours of startDate to 0
    set minutes of startDate to 0
    set seconds of startDate to 0

    tell targetCal
        set newEvent to make new event with properties {summary:"$TITLE_ESCAPED", start date:startDate, allday event:true}

        if "$LOCATION_ESCAPED" is not "" then
            set location of newEvent to "$LOCATION_ESCAPED"
        end if

        if "$NOTES_ESCAPED" is not "" then
            set description of newEvent to "$NOTES_ESCAPED"
        end if
    end tell

    return "Created all-day event: $TITLE_ESCAPED on $DATE"
end tell
EOF
else
    [[ -z "$START" ]] && error_exit "--start is required for timed events"

    # Parse start date/time components (locale-independent)
    START_YEAR=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%Y" 2>/dev/null)
    START_MONTH=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%-m" 2>/dev/null)
    START_DAY=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%-d" 2>/dev/null)
    START_HOUR=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%-H" 2>/dev/null)
    START_MIN=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%-M" 2>/dev/null)
    [[ -z "$START_YEAR" ]] && error_exit "Invalid start format. Use 'YYYY-MM-DD HH:MM'"

    # Calculate end time
    if [[ -n "$DURATION" ]]; then
        # Calculate end from duration
        START_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%s" 2>/dev/null)
        END_EPOCH=$((START_EPOCH + DURATION * 60))
    elif [[ -n "$END" ]]; then
        END_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "$END" "+%s" 2>/dev/null)
        [[ -z "$END_EPOCH" ]] && error_exit "Invalid end format. Use 'YYYY-MM-DD HH:MM'"
    else
        # Default to 1 hour duration
        START_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%s" 2>/dev/null)
        END_EPOCH=$((START_EPOCH + 3600))
    fi

    END_YEAR=$(date -j -f "%s" "$END_EPOCH" "+%Y" 2>/dev/null)
    END_MONTH=$(date -j -f "%s" "$END_EPOCH" "+%-m" 2>/dev/null)
    END_DAY=$(date -j -f "%s" "$END_EPOCH" "+%-d" 2>/dev/null)
    END_HOUR=$(date -j -f "%s" "$END_EPOCH" "+%-H" 2>/dev/null)
    END_MIN=$(date -j -f "%s" "$END_EPOCH" "+%-M" 2>/dev/null)

    osascript <<EOF
tell application "Calendar"
    try
        set targetCal to calendar "$CALENDAR"
    on error
        return "Error: Calendar '$CALENDAR' not found."
    end try

    -- Build start date programmatically (locale-independent)
    set startDate to current date
    set year of startDate to $START_YEAR
    set month of startDate to $START_MONTH
    set day of startDate to $START_DAY
    set hours of startDate to $START_HOUR
    set minutes of startDate to $START_MIN
    set seconds of startDate to 0

    -- Build end date programmatically (locale-independent)
    set endDate to current date
    set year of endDate to $END_YEAR
    set month of endDate to $END_MONTH
    set day of endDate to $END_DAY
    set hours of endDate to $END_HOUR
    set minutes of endDate to $END_MIN
    set seconds of endDate to 0

    tell targetCal
        set newEvent to make new event with properties {summary:"$TITLE_ESCAPED", start date:startDate, end date:endDate}

        if "$LOCATION_ESCAPED" is not "" then
            set location of newEvent to "$LOCATION_ESCAPED"
        end if

        if "$NOTES_ESCAPED" is not "" then
            set description of newEvent to "$NOTES_ESCAPED"
        end if
    end tell

    return "Created event: $TITLE_ESCAPED on $START"
end tell
EOF
fi
