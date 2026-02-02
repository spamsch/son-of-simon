#!/bin/bash
# ==============================================================================
# export-note.sh - Export a note to a file
# ==============================================================================
# Description:
#   Exports a note's content to a text or HTML file. Can export by note name
#   or export all notes from a folder.
#
# Usage:
#   ./export-note.sh --name "Meeting Notes" --output meeting.txt
#   ./export-note.sh --name "Project Plan" --output plan.html --format html
#   ./export-note.sh --folder "Work" --output-dir ./exports
#
# Options:
#   --name <text>        Note name to export (required unless --folder)
#   --folder <name>      Export all notes from folder
#   --output <file>      Output file path (for single note)
#   --output-dir <dir>   Output directory (for folder export)
#   --format <type>      Output format: text or html (default: text)
#
# Example:
#   ./export-note.sh --name "Quick Note" --output note.txt
#   ./export-note.sh --folder "Work" --output-dir ./work-notes --format html
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
NAME=""
FOLDER=""
OUTPUT=""
OUTPUT_DIR=""
FORMAT="text"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            NAME="$2"
            shift 2
            ;;
        --folder)
            FOLDER="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
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
[[ -z "$NAME" && -z "$FOLDER" ]] && error_exit "Please specify --name or --folder"
[[ -n "$NAME" && -z "$OUTPUT" ]] && error_exit "--output is required when using --name"
[[ -n "$FOLDER" && -z "$OUTPUT_DIR" ]] && error_exit "--output-dir is required when using --folder"

if [[ -n "$NAME" ]]; then
    # Export single note
    CONTENT=$(osascript <<EOF
tell application "Notes"
    set matchingNotes to (notes whose name is "$NAME")

    if (count of matchingNotes) is 0 then
        return "ERROR:Note '$NAME' not found."
    end if

    set n to item 1 of matchingNotes

    if "$FORMAT" is "html" then
        return body of n
    else
        return plaintext of n
    end if
end tell
EOF
)

    # Check for error
    if [[ "$CONTENT" == ERROR:* ]]; then
        error_exit "${CONTENT#ERROR:}"
    fi

    # Write to file
    echo "$CONTENT" > "$OUTPUT"
    success "Exported '$NAME' to $OUTPUT"

else
    # Export all notes from folder
    mkdir -p "$OUTPUT_DIR"

    # Get list of notes
    NOTES=$(osascript <<EOF
tell application "Notes"
    try
        set targetFolder to folder "$FOLDER"
    on error
        return "ERROR:Folder '$FOLDER' not found."
    end try

    set output to ""
    repeat with n in notes of targetFolder
        set output to output & name of n & "|||"
    end repeat
    return output
end tell
EOF
)

    # Check for error
    if [[ "$NOTES" == ERROR:* ]]; then
        error_exit "${NOTES#ERROR:}"
    fi

    # Process each note
    IFS='|||' read -ra NOTE_NAMES <<< "$NOTES"
    COUNT=0

    for NOTE_NAME in "${NOTE_NAMES[@]}"; do
        # Skip empty entries
        [[ -z "$NOTE_NAME" ]] && continue

        # Create safe filename
        SAFE_NAME=$(echo "$NOTE_NAME" | tr '/' '-' | tr ':' '-' | tr -d '\n')

        if [[ "$FORMAT" == "html" ]]; then
            EXT="html"
        else
            EXT="txt"
        fi

        OUTPUT_FILE="$OUTPUT_DIR/$SAFE_NAME.$EXT"

        # Export the note
        CONTENT=$(osascript <<EOF
tell application "Notes"
    tell folder "$FOLDER"
        set n to first note whose name is "$NOTE_NAME"
        if "$FORMAT" is "html" then
            return body of n
        else
            return plaintext of n
        end if
    end tell
end tell
EOF
)

        echo "$CONTENT" > "$OUTPUT_FILE"
        ((COUNT++))
        info "Exported: $SAFE_NAME"
    done

    success "Exported $COUNT note(s) to $OUTPUT_DIR"
fi
