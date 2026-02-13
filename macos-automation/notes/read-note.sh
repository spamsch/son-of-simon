#!/bin/bash
# ==============================================================================
# read-note.sh - Read a note's content from Notes.app
# ==============================================================================
# Usage:
#   ./read-note.sh --title "My Note"
#   ./read-note.sh --title "My Note" --folder "Work"
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
    -- Find note using bulk property fetch (avoids -1728 on iCloud folders)
    set foundNoteId to missing value

    if "$FOLDER_ESCAPED" is not "" then
        try
            -- Case-sensitive first, then case-insensitive fallback
            set srcFolder to missing value
            repeat with f in folders
                considering case
                    if name of f is "$FOLDER_ESCAPED" then
                        set srcFolder to contents of f
                        exit repeat
                    end if
                end considering
            end repeat
            if srcFolder is missing value then
                repeat with f in folders
                    if name of f is "$FOLDER_ESCAPED" then
                        set srcFolder to contents of f
                        exit repeat
                    end if
                end repeat
            end if
            if srcFolder is missing value then error "not found"
            set nCount to count of notes of srcFolder
            if nCount > 0 then
                set noteIds to id of notes of srcFolder
                set noteNames to name of notes of srcFolder
                repeat with i from 1 to nCount
                    if item i of noteNames contains "$TITLE_ESCAPED" then
                        set foundNoteId to item i of noteIds
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

    set n to note id foundNoteId
    set c to container of n
    set output to "Title: " & name of n & return
    set output to output & "Folder: " & name of c & return
    set output to output & "Modified: " & (modification date of n as string) & return
    set output to output & return
    set output to output & plaintext of n
    return output
end tell
EOF
