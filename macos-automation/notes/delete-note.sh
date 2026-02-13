#!/bin/bash
# ==============================================================================
# delete-note.sh - Delete a note in Notes.app
# ==============================================================================
# Usage:
#   ./delete-note.sh --title "My Note"
#   ./delete-note.sh --title "My Note" --folder "Work"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

TITLE=""
FOLDER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --title) TITLE="$2"; shift 2 ;;
        --folder) FOLDER="$2"; shift 2 ;;
        *) error_exit "Unknown option: $1" ;;
    esac
done

[[ -z "$TITLE" ]] && error_exit "--title is required"

TITLE_ESCAPED=$(escape_for_applescript "$TITLE")
FOLDER_ESCAPED=$(escape_for_applescript "$FOLDER")

osascript <<EOF
tell application "Notes"
    -- Find note using bulk property fetch
    -- (avoids "repeat with n in notes of folder" which triggers -1728 on iCloud folders)
    set foundNoteId to missing value
    set foundNoteName to ""

    if "$FOLDER_ESCAPED" is not "" then
        try
            set srcFolder to folder "$FOLDER_ESCAPED"
            set nCount to count of notes of srcFolder
            if nCount > 0 then
                set noteIds to id of notes of srcFolder
                set noteNames to name of notes of srcFolder
                repeat with i from 1 to nCount
                    if item i of noteNames contains "$TITLE_ESCAPED" then
                        set foundNoteId to item i of noteIds
                        set foundNoteName to item i of noteNames
                        exit repeat
                    end if
                end repeat
            end if
        on error
            return "Error: Folder '$FOLDER_ESCAPED' not found."
        end try
    else
        repeat with f in folders
            if name of f is not "Recently Deleted" then
                set nCount to count of notes of f
                if nCount > 0 then
                    try
                        set noteIds to id of notes of f
                        set noteNames to name of notes of f
                        repeat with i from 1 to nCount
                            if item i of noteNames contains "$TITLE_ESCAPED" then
                                set foundNoteId to item i of noteIds
                                set foundNoteName to item i of noteNames
                                exit repeat
                            end if
                        end repeat
                    end try
                end if
            end if
            if foundNoteId is not missing value then exit repeat
        end repeat
    end if

    if foundNoteId is missing value then
        return "Error: Note matching '$TITLE_ESCAPED' not found."
    end if

    set foundNote to note id foundNoteId
    delete foundNote
    return "Deleted note '" & foundNoteName & "'"
end tell
EOF
