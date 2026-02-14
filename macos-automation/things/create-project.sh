#!/bin/bash
# ==============================================================================
# create-project.sh - Create a new Things3 project
# ==============================================================================
# Description:
#   Creates a new project in Things3 with optional notes, due date, tags,
#   and area assignment.
#
# Usage:
#   ./create-project.sh --name "Home Renovation"
#   ./create-project.sh --name "Q1 Report" --due "2026-03-31" --tags "work"
#
# Options:
#   --name <text>       Project name (required)
#   --notes <text>      Project notes/description
#   --due <date>        Due date as "YYYY-MM-DD"
#   --tags <csv>        Comma-separated tag names
#   --area <name>       Assign to area
#
# Example:
#   ./create-project.sh --name "Vacation Planning" --tags "personal"
#   ./create-project.sh --name "Product Launch" --due "2026-06-01" --area "Work"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
NAME=""
NOTES=""
DUE=""
TAGS=""
AREA=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            NAME="$2"
            shift 2
            ;;
        --notes)
            NOTES="$2"
            shift 2
            ;;
        --due)
            DUE="$2"
            shift 2
            ;;
        --tags)
            TAGS="$2"
            shift 2
            ;;
        --area)
            AREA="$2"
            shift 2
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
[[ -z "$NAME" ]] && error_exit "--name is required"

# Escape for AppleScript
NAME_ESCAPED=$(escape_for_applescript "$NAME")
NOTES_ESCAPED=$(escape_for_applescript "$NOTES")
AREA_ESCAPED=$(escape_for_applescript "$AREA")

# Handle due date components
HAS_DUE=false
DUE_YEAR=2000
DUE_MONTH=1
DUE_DAY=1

if [[ -n "$DUE" ]]; then
    if [[ "$DUE" =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})$ ]]; then
        HAS_DUE=true
        DUE_YEAR="${BASH_REMATCH[1]}"
        DUE_MONTH=$((10#${BASH_REMATCH[2]}))
        DUE_DAY=$((10#${BASH_REMATCH[3]}))
    else
        error_exit "Invalid date format. Use 'YYYY-MM-DD'"
    fi
fi

osascript <<EOF
tell application "Things3"
    -- Build properties
    set props to {name:"$NAME_ESCAPED"}

    if "$NOTES_ESCAPED" is not "" then
        set notes of props to "$NOTES_ESCAPED"
    end if

    if "$TAGS" is not "" then
        set tag names of props to "$TAGS"
    end if

    -- Create the project
    set newProject to make new project with properties props

    -- Set due date
    if "$HAS_DUE" is "true" then
        set dueDate to current date
        set year of dueDate to $DUE_YEAR
        set month of dueDate to $DUE_MONTH
        set day of dueDate to $DUE_DAY
        set hours of dueDate to 0
        set minutes of dueDate to 0
        set seconds of dueDate to 0
        set due date of newProject to dueDate
    end if

    -- Assign to area
    if "$AREA_ESCAPED" is not "" then
        try
            set targetArea to area "$AREA_ESCAPED"
            set area of newProject to targetArea
        on error
            -- Area not found, continue without it
        end try
    end if

    -- Build confirmation
    set projID to id of newProject
    set output to "Created project: " & name of newProject
    if "$DUE" is not "" then
        set output to output & " (due: $DUE)"
    end if
    if "$TAGS" is not "" then
        set output to output & " #" & "$TAGS"
    end if
    if "$AREA_ESCAPED" is not "" then
        set output to output & " [area: $AREA_ESCAPED]"
    end if
    set output to output & return & "id: " & projID
    return output
end tell
EOF
