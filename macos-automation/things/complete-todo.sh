#!/bin/bash
# ==============================================================================
# complete-todo.sh - Mark a Things3 to-do as complete
# ==============================================================================
# Description:
#   Marks one or more to-dos as complete. Can find to-dos by exact name,
#   pattern matching, or ID.
#
# Usage:
#   ./complete-todo.sh --name "Buy groceries"
#   ./complete-todo.sh --pattern "report"
#   ./complete-todo.sh --id "ABC123"
#
# Options:
#   --name <text>       Exact to-do name to complete
#   --pattern <text>    Complete all to-dos containing this text
#   --id <id>           Complete to-do by ID
#   --dry-run           Show what would be completed without completing
#
# Example:
#   ./complete-todo.sh --name "Buy milk"
#   ./complete-todo.sh --pattern "meeting" --dry-run
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
NAME=""
PATTERN=""
TODO_ID=""
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
        --id)
            TODO_ID="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
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

# Validate
[[ -z "$NAME" && -z "$PATTERN" && -z "$TODO_ID" ]] && error_exit "Please specify --name, --pattern, or --id"

NAME_ESCAPED=$(escape_for_applescript "$NAME")
PATTERN_ESCAPED=$(escape_for_applescript "$PATTERN")

osascript <<EOF
tell application "Things3"
    set output to ""
    set completedCount to 0

    if "$TODO_ID" is not "" then
        -- Complete by ID
        try
            set t to to do id "$TODO_ID"
            if status of t is not open then
                return "To-do is already completed or canceled."
            end if
            if $DRY_RUN then
                return "Would complete: " & name of t & " (id: $TODO_ID)"
            else
                set status of t to completed
                return "Completed: " & name of t & " (id: $TODO_ID)"
            end if
        on error
            return "Error: No to-do found with id '$TODO_ID'."
        end try
    else if "$NAME_ESCAPED" is not "" then
        -- Complete by exact name
        set allTodos to to dos whose name is "$NAME_ESCAPED" and status is open
        if (count of allTodos) is 0 then
            return "No open to-do found with name '$NAME_ESCAPED'."
        end if

        repeat with t in allTodos
            set completedCount to completedCount + 1
            if $DRY_RUN then
                -- Get project for context
                set tProject to ""
                try
                    set tProject to name of project of t
                end try
                if tProject is not "" then
                    set output to output & "Would complete: " & name of t & " [" & tProject & "]" & return
                else
                    set output to output & "Would complete: " & name of t & return
                end if
            else
                set status of t to completed
                set output to output & "Completed: " & name of t & return
            end if
        end repeat
    else
        -- Complete by pattern
        set allTodos to to dos whose name contains "$PATTERN_ESCAPED" and status is open
        if (count of allTodos) is 0 then
            return "No open to-dos found matching '$PATTERN_ESCAPED'."
        end if

        repeat with t in allTodos
            set completedCount to completedCount + 1
            if $DRY_RUN then
                set tProject to ""
                try
                    set tProject to name of project of t
                end try
                if tProject is not "" then
                    set output to output & "Would complete: " & name of t & " [" & tProject & "]" & return
                else
                    set output to output & "Would complete: " & name of t & return
                end if
            else
                set status of t to completed
                set output to output & "Completed: " & name of t & return
            end if
        end repeat
    end if

    if $DRY_RUN then
        set output to output & return & "Would complete " & completedCount & " to-do(s)."
    else
        set output to output & return & "Completed " & completedCount & " to-do(s)."
    end if

    return output
end tell
EOF
