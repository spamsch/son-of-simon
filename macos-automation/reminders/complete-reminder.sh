#!/bin/bash
# ==============================================================================
# complete-reminder.sh - Mark reminders as complete
# ==============================================================================
# Description:
#   Marks one or more reminders as complete. Can find reminders by exact name
#   or by pattern matching.
#
# Usage:
#   ./complete-reminder.sh --name "Call dentist"
#   ./complete-reminder.sh --pattern "report"
#   ./complete-reminder.sh --list "Work Tasks" --name "Review document"
#
# Options:
#   --name <text>       Exact reminder name to complete
#   --pattern <text>    Complete all reminders containing this text
#   --list <name>       Only search in the specified list
#   --dry-run           Show what would be completed without actually completing
#
# Example:
#   ./complete-reminder.sh --name "Buy groceries"
#   ./complete-reminder.sh --pattern "meeting" --dry-run
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
NAME=""
PATTERN=""
LIST_NAME=""
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            NAME="$2"
            shift 2
            ;;
        --pattern)
            PATTERN="$2"
            shift 2
            ;;
        --list)
            LIST_NAME="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
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

# Validate
[[ -z "$NAME" && -z "$PATTERN" ]] && error_exit "Please specify --name or --pattern"

if [[ -n "$NAME" ]]; then
    # Complete by exact name
    osascript <<EOF
tell application "Reminders"
    set found to false
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

    repeat with l in listCollection
        try
            set matchingReminders to (reminders of l whose name is "$NAME" and completed is false)
            repeat with r in matchingReminders
                set found to true
                if $DRY_RUN then
                    set output to output & "Would complete: " & name of r & " (in " & name of l & ")" & return
                else
                    set completed of r to true
                    set output to output & "Completed: " & name of r & " (in " & name of l & ")" & return
                end if
            end repeat
        end try
    end repeat

    if not found then
        return "No incomplete reminder found with name '$NAME'."
    end if

    return output
end tell
EOF
else
    # Complete by pattern
    osascript <<EOF
tell application "Reminders"
    set completedCount to 0
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

    repeat with l in listCollection
        try
            set matchingReminders to (reminders of l whose name contains "$PATTERN" and completed is false)
            repeat with r in matchingReminders
                set completedCount to completedCount + 1
                if $DRY_RUN then
                    set output to output & "Would complete: " & name of r & " (in " & name of l & ")" & return
                else
                    set completed of r to true
                    set output to output & "Completed: " & name of r & " (in " & name of l & ")" & return
                end if
            end repeat
        end try
    end repeat

    if completedCount is 0 then
        return "No incomplete reminders found matching '$PATTERN'."
    end if

    if $DRY_RUN then
        set output to output & return & "Would complete " & completedCount & " reminder(s)."
    else
        set output to output & return & "Completed " & completedCount & " reminder(s)."
    end if

    return output
end tell
EOF
fi
