#!/bin/bash
# ==============================================================================
# create-reminder.sh - Create a new reminder
# ==============================================================================
# Description:
#   Creates a new reminder in the specified list with optional due date,
#   priority, and notes.
#
# Usage:
#   ./create-reminder.sh --title "Call dentist"
#   ./create-reminder.sh --title "Submit report" --due "2026-01-31 17:00"
#   ./create-reminder.sh --title "Important task" --due "2026-01-31" --priority high --flag
#   ./create-reminder.sh --list "Work Tasks" --title "Review document" --notes "Check section 3"
#
# Options:
#   --title <text>      Reminder title (required)
#   --list <name>       List name (default: "Reminders")
#   --due <datetime>    Due date as "YYYY-MM-DD" or "YYYY-MM-DD HH:MM"
#   --priority <level>  Priority: high, medium, low, or none (default: none)
#   --flag              Flag the reminder
#   --notes <text>      Additional notes/description
#
# Example:
#   ./create-reminder.sh --title "Buy groceries" --list "Shopping"
#   ./create-reminder.sh --title "Quarterly report" --due "2026-01-31 17:00" --priority high --flag
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
TITLE=""
LIST_NAME="Reminders"
DUE=""
PRIORITY="none"
FLAG=false
NOTES=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --title)
            TITLE="$2"
            shift 2
            ;;
        --list)
            LIST_NAME="$2"
            shift 2
            ;;
        --due)
            DUE="$2"
            shift 2
            ;;
        --priority)
            PRIORITY="$2"
            shift 2
            ;;
        --flag)
            FLAG=true
            shift
            ;;
        --notes)
            NOTES="$2"
            shift 2
            ;;
        -h|--help)
            head -32 "$0" | tail -27
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate
[[ -z "$TITLE" ]] && error_exit "--title is required"

# Convert priority to number (0=none, 1=high, 5=medium, 9=low)
case "$PRIORITY" in
    high)   PRIORITY_NUM=1 ;;
    medium) PRIORITY_NUM=5 ;;
    low)    PRIORITY_NUM=9 ;;
    *)      PRIORITY_NUM=0 ;;
esac

# Escape special characters
TITLE_ESCAPED=$(escape_for_applescript "$TITLE")
NOTES_ESCAPED=$(escape_for_applescript "$NOTES")

# Build the properties string
PROPS="name:\"$TITLE_ESCAPED\""

if [[ "$PRIORITY_NUM" -gt 0 ]]; then
    PROPS="$PROPS, priority:$PRIORITY_NUM"
fi

if [[ "$FLAG" == "true" ]]; then
    PROPS="$PROPS, flagged:true"
fi

# Handle due date
DUE_SCRIPT=""
if [[ -n "$DUE" ]]; then
    # Check if it includes time
    if [[ "$DUE" =~ [0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2} ]]; then
        # Date with time
        DUE_FORMATTED=$(date -j -f "%Y-%m-%d %H:%M" "$DUE" "+%B %d, %Y %I:%M %p" 2>/dev/null)
        [[ -z "$DUE_FORMATTED" ]] && error_exit "Invalid date format. Use 'YYYY-MM-DD HH:MM'"
        PROPS="$PROPS, due date:date \"$DUE_FORMATTED\""
    else
        # Date only (all-day)
        DUE_FORMATTED=$(date -j -f "%Y-%m-%d" "$DUE" "+%B %d, %Y" 2>/dev/null)
        [[ -z "$DUE_FORMATTED" ]] && error_exit "Invalid date format. Use 'YYYY-MM-DD'"
        PROPS="$PROPS, allday due date:date \"$DUE_FORMATTED\""
    fi
fi

osascript <<EOF
tell application "Reminders"
    try
        set targetList to list "$LIST_NAME"
    on error
        return "Error: List '$LIST_NAME' not found."
    end try

    tell targetList
        set newReminder to make new reminder with properties {$PROPS}

        if "$NOTES_ESCAPED" is not "" then
            set body of newReminder to "$NOTES_ESCAPED"
        end if
    end tell

    set output to "Created reminder: $TITLE_ESCAPED"
    if "$DUE" is not "" then
        set output to output & " (due: $DUE)"
    end if
    return output
end tell
EOF
