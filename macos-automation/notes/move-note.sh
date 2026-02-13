#!/bin/bash
# ==============================================================================
# move-note.sh - Move a note to a different folder
# ==============================================================================
# Usage:
#   ./move-note.sh --title "My Note" --to "Work"
#   ./move-note.sh --title "My Note" --from "Notes" --to "Work"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

TITLE=""
FROM=""
TO=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --title) TITLE="$2"; shift 2 ;;
        --from) FROM="$2"; shift 2 ;;
        --to) TO="$2"; shift 2 ;;
        *) error_exit "Unknown option: $1" ;;
    esac
done

[[ -z "$TITLE" ]] && error_exit "--title is required"
[[ -z "$TO" ]] && error_exit "--to is required"

TITLE_ESCAPED=$(escape_for_applescript "$TITLE")
FROM_ESCAPED=$(escape_for_applescript "$FROM")
TO_ESCAPED=$(escape_for_applescript "$TO")

osascript <<EOF
tell application "Notes"
    -- Find destination folder (case-sensitive to avoid ambiguity between e.g. "todos" and "Todos")
    set destFolder to missing value
    repeat with f in folders
        considering case
            if name of f is "$TO_ESCAPED" then
                set destFolder to contents of f
                exit repeat
            end if
        end considering
    end repeat
    if destFolder is missing value then
        return "Error: Destination folder '$TO_ESCAPED' not found."
    end if

    -- Detect smart folder: first note's container won't match the folder
    set destNoteCount to count of notes of destFolder
    if destNoteCount > 0 then
        try
            set destFolderId to id of destFolder
            set checkNote to first note of destFolder
            set checkNoteId to id of checkNote
            set globalCheckNote to note id checkNoteId
            set c to container of globalCheckNote
            set cId to id of c
            if cId is not destFolderId then
                return "Error: '$TO_ESCAPED' is a Smart Folder. Notes cannot be moved into Smart Folders. Adjust the Smart Folder query or move to a regular folder instead."
            end if
        end try
    end if

    -- Find the note using bulk property fetch
    -- (avoids "repeat with n in notes of folder" which triggers -1728 on iCloud folders)
    set foundNoteId to missing value
    set foundNoteName to ""

    if "$FROM_ESCAPED" is not "" then
        try
            -- Case-sensitive match to avoid ambiguity
            set srcFolder to missing value
            repeat with f in folders
                considering case
                    if name of f is "$FROM_ESCAPED" then
                        set srcFolder to contents of f
                        exit repeat
                    end if
                end considering
            end repeat
            if srcFolder is missing value then error "not found"
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
            return "Error: Source folder '$FROM_ESCAPED' not found."
        end try
    else
        -- Search all folders
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

    -- Get note by ID and move (avoids stale folder-scoped reference)
    set foundNote to note id foundNoteId
    move foundNote to destFolder
    return "Moved '" & foundNoteName & "' to folder '$TO_ESCAPED'"
end tell
EOF
