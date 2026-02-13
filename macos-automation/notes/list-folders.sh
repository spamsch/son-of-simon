#!/bin/bash
# ==============================================================================
# list-folders.sh - List all folders in Notes.app
# ==============================================================================
# Description:
#   Lists all folders (and subfolders) in Notes.app with note counts.
#
# Usage:
#   ./list-folders.sh
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

osascript <<'EOF'
tell application "Notes"
    set output to "=== NOTES FOLDERS ===" & return & return
    set folderCount to 0

    repeat with f in folders
        if name of f is not "Recently Deleted" then
            set folderCount to folderCount + 1
            set nCount to count of notes of f

            -- Detect smart folders: first note's container won't match the folder
            set isSmart to false
            if nCount > 0 then
                try
                    set fId to id of f
                    set firstNote to first note of f
                    set nId to id of firstNote
                    set globalNote to note id nId
                    set c to container of globalNote
                    set cId to id of c
                    if cId is not fId then
                        set isSmart to true
                    end if
                end try
            end if

            if isSmart then
                set output to output & "🔍 " & name of f & " (" & nCount & " notes, smart folder)" & return
            else
                set output to output & "📁 " & name of f & " (" & nCount & " notes)" & return
            end if
        end if
    end repeat

    set output to output & return & "Total: " & folderCount & " folder(s)"
    return output
end tell
EOF
