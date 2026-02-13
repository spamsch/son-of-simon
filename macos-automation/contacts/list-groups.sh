#!/bin/bash
# ==============================================================================
# list-groups.sh - List all contact groups
# ==============================================================================
# Description:
#   Lists all contact groups in Contacts.app with member counts. Optionally
#   shows the names of members in each group.
#
# Usage:
#   ./list-groups.sh
#   ./list-groups.sh --with-members
#   ./list-groups.sh --with-members --limit 10
#
# Options:
#   --with-members   Show member names under each group
#   --limit <n>      Limit number of groups displayed (default: 50)
#
# Example:
#   ./list-groups.sh
#   ./list-groups.sh --with-members --limit 25
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
WITH_MEMBERS=false
LIMIT=50

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-members)
            WITH_MEMBERS=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            head -21 "$0" | tail -20
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

osascript <<EOF
tell application "Contacts"
    set allGroups to every group
    set totalGroups to count of allGroups

    if totalGroups is 0 then
        return "No contact groups found."
    end if

    -- Cap at limit
    if totalGroups > $LIMIT then
        set displayCount to $LIMIT
    else
        set displayCount to totalGroups
    end if

    set output to "=== CONTACT GROUPS ===" & return & return

    repeat with i from 1 to displayCount
        set g to item i of allGroups
        set gName to name of g
        set memberList to every person of g
        set memberCount to count of memberList

        set output to output & gName & " (" & memberCount & " members)" & return

        if $WITH_MEMBERS and memberCount > 0 then
            -- Bulk-fetch names for performance
            set memberNames to name of every person of g
            repeat with mName in memberNames
                set output to output & "  - " & mName & return
            end repeat
            set output to output & return
        end if
    end repeat

    set output to output & return & "Total: " & totalGroups & " group(s)"
    if totalGroups > $LIMIT then
        set output to output & " (showing " & displayCount & ")"
    end if

    return output
end tell
EOF
