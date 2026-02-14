#!/bin/bash
# ==============================================================================
# list-tags.sh - List all Things3 tags
# ==============================================================================
# Description:
#   Lists all tags defined in Things3.
#
# Usage:
#   ./list-tags.sh
#   ./list-tags.sh --with-counts
#
# Options:
#   --with-counts       Show number of open to-dos per tag
#   --limit <n>         Maximum number of tags (default: 100)
#
# Example:
#   ./list-tags.sh --with-counts
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
WITH_COUNTS=false
LIMIT=100

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-counts)
            WITH_COUNTS=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            head -18 "$0" | tail -13
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

osascript <<EOF
tell application "Things3"
    set allTags to every tag
    set tagCount to count of allTags

    if tagCount is 0 then
        return "No tags found."
    end if

    set output to "=== THINGS3: TAGS ===" & return
    set output to output & tagCount & " tag(s)" & return & return

    set displayCount to 0
    repeat with tg in allTags
        if displayCount ≥ $LIMIT then exit repeat
        set displayCount to displayCount + 1
        set tgName to name of tg

        if $WITH_COUNTS then
            set openCount to count of (to dos of tg whose status is open)
            set output to output & "  " & tgName & " (" & openCount & " open)" & return
        else
            set output to output & "  " & tgName & return
        end if
    end repeat

    return output
end tell
EOF
