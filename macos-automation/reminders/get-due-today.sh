#!/bin/bash
# ==============================================================================
# get-due-today.sh - Get reminders due today
# ==============================================================================
# Description:
#   Retrieves all incomplete reminders that are due today, organized by list.
#   Also shows overdue reminders if any exist.
#
# Usage:
#   ./get-due-today.sh
#   ./get-due-today.sh --include-overdue
#   ./get-due-today.sh --list "Work Tasks"
#
# Options:
#   --include-overdue   Also show overdue reminders
#   --list <name>       Only check the specified list
#
# Example:
#   ./get-due-today.sh
#   ./get-due-today.sh --include-overdue
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

INCLUDE_OVERDUE=false
LIST_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --include-overdue)
            INCLUDE_OVERDUE=true
            shift
            ;;
        --list)
            LIST_NAME="$2"
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
tell application "Reminders"
    set now to current date
    set todayStart to now
    set time of todayStart to 0
    set todayEnd to todayStart + (24 * 60 * 60)

    set output to ""

    set listCollection to {}
    if "$LIST_NAME" is not "" then
        try
            set listCollection to {list "$LIST_NAME"}
        on error
            return "List '$LIST_NAME' not found."
        end try
    else
        set listCollection to every list
    end if

    -- Overdue reminders
    if $INCLUDE_OVERDUE then
        set overdueCount to 0
        set overdueOutput to ""

        repeat with l in listCollection
            try
                set overdueReminders to (reminders of l whose due date < todayStart and completed is false)
                repeat with r in overdueReminders
                    set overdueCount to overdueCount + 1
                    set overdueOutput to overdueOutput & "  ⚠️ " & name of r & return
                    set overdueOutput to overdueOutput & "     Due: " & (due date of r as string) & return
                    set overdueOutput to overdueOutput & "     List: " & name of l & return
                end repeat
            end try
        end repeat

        if overdueCount > 0 then
            set output to output & "=== OVERDUE (" & overdueCount & ") ===" & return & return
            set output to output & overdueOutput & return
        end if
    end if

    -- Today's reminders
    set todayCount to 0
    set todayOutput to ""

    repeat with l in listCollection
        try
            set todayReminders to (reminders of l whose due date >= todayStart and due date < todayEnd and completed is false)
            repeat with r in todayReminders
                set todayCount to todayCount + 1
                set priorityStr to ""
                if priority of r is 1 then set priorityStr to " ❗"
                if flagged of r then set priorityStr to priorityStr & " 🚩"

                set todayOutput to todayOutput & "  □ " & name of r & priorityStr & return

                -- Show time if set
                set dueTime to due date of r
                set h to hours of dueTime
                set m to minutes of dueTime
                if h is not 0 or m is not 0 then
                    if m < 10 then set m to "0" & m
                    set todayOutput to todayOutput & "     Time: " & h & ":" & m & return
                end if

                set todayOutput to todayOutput & "     List: " & name of l & return
            end repeat
        end try
    end repeat

    if todayCount > 0 then
        set output to output & "=== DUE TODAY (" & todayCount & ") ===" & return & return
        set output to output & todayOutput
    else if output is "" then
        return "No reminders due today."
    end if

    return output
end tell
EOF
