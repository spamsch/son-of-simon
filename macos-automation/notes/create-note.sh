#!/bin/bash
# ==============================================================================
# create-note.sh - Create a new note
# ==============================================================================
# Description:
#   Creates a new note in Notes.app. Can create plain text notes or HTML
#   formatted notes. Content can be provided directly or read from a file.
#
# Usage:
#   ./create-note.sh --title "Meeting Notes" --body "Discussion points..."
#   ./create-note.sh --title "Project Plan" --body-file plan.txt
#   ./create-note.sh --title "Formatted" --body "<h1>Title</h1><p>Content</p>" --html
#   ./create-note.sh --folder "Work" --title "Task List" --body "- Item 1"
#
# Options:
#   --title <text>      Note title (required)
#   --body <text>       Note body content
#   --body-file <file>  Read body from file
#   --folder <name>     Folder name (default: "Notes")
#   --html              Treat body as HTML content
#
# Example:
#   ./create-note.sh --title "Quick Note" --body "Remember to call John"
#   ./create-note.sh --folder "Work" --title "Meeting" --body-file meeting.md
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
TITLE=""
BODY=""
FOLDER="Notes"
HTML=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --title)
            TITLE="$2"
            shift 2
            ;;
        --body)
            BODY="$2"
            shift 2
            ;;
        --body-file)
            if [[ -f "$2" ]]; then
                BODY=$(cat "$2")
            else
                error_exit "Body file not found: $2"
            fi
            shift 2
            ;;
        --folder)
            FOLDER="$2"
            shift 2
            ;;
        --html)
            HTML=true
            shift
            ;;
        -h|--help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate
[[ -z "$TITLE" ]] && error_exit "--title is required"
[[ -z "$BODY" ]] && BODY="$TITLE"  # Use title as body if not provided

# Escape special characters for AppleScript
TITLE_ESCAPED=$(escape_for_applescript "$TITLE")
BODY_ESCAPED=$(escape_for_applescript "$BODY")

# Format body as HTML if not already
if [[ "$HTML" == "false" ]]; then
    # Convert plain text to basic HTML
    # Replace newlines with <br> and wrap in div
    BODY_HTML="<div><h1>$TITLE_ESCAPED</h1></div>"
    # Convert newlines to <br> for the body
    BODY_WITH_BR=$(echo "$BODY_ESCAPED" | sed 's/$/\\n/' | tr -d '\n' | sed 's/\\n$//;s/\\n/<br>/g')
    BODY_HTML="$BODY_HTML<div>$BODY_WITH_BR</div>"
else
    BODY_HTML="$BODY_ESCAPED"
fi

osascript <<EOF
tell application "Notes"
    try
        set targetFolder to folder "$FOLDER"
    on error
        return "Error: Folder '$FOLDER' not found."
    end try

    tell targetFolder
        make new note with properties {name:"$TITLE_ESCAPED", body:"$BODY_HTML"}
    end tell

    return "Created note: $TITLE_ESCAPED in folder '$FOLDER'"
end tell
EOF
