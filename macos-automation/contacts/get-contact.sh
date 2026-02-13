#!/bin/bash
# ==============================================================================
# get-contact.sh - Get full contact card details
# ==============================================================================
# Description:
#   Retrieves the full contact card for a person by name or Contacts ID.
#   Returns all available fields: names, emails, phones, addresses,
#   organization, job title, birthday, notes, and group memberships.
#
# Usage:
#   ./get-contact.sh --name "John Smith"
#   ./get-contact.sh --name "Smith" --exact
#   ./get-contact.sh --id "ABC123-DEF456"
#
# Options:
#   --name <text>    Search by contact name (contains match by default)
#   --id <id>        Look up by Contacts ID (exact match)
#   --exact          Use exact name match instead of contains
#
# Example:
#   ./get-contact.sh --name "John Smith" --exact
#   ./get-contact.sh --name "Smith"
#   ./get-contact.sh --id "1A2B3C4D-5E6F-7890-ABCD-EF1234567890:ABPerson"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
NAME=""
CONTACT_ID=""
EXACT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            NAME="$2"
            shift 2
            ;;
        --id)
            CONTACT_ID="$2"
            shift 2
            ;;
        --exact)
            EXACT=true
            shift
            ;;
        -h|--help)
            head -24 "$0" | tail -23
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate
if [[ -z "$NAME" && -z "$CONTACT_ID" ]]; then
    error_exit "Please specify --name or --id"
fi

# Escape for AppleScript
NAME_ESCAPED=$(escape_for_applescript "$NAME")
ID_ESCAPED=$(escape_for_applescript "$CONTACT_ID")

osascript <<EOF
tell application "Contacts"
    set matchedPeople to {}

    if "$ID_ESCAPED" is not "" then
        -- Look up by ID
        try
            set matchedPeople to {person id "$ID_ESCAPED"}
        on error
            return "No contact found with ID: $ID_ESCAPED"
        end try
    else if $EXACT then
        set matchedPeople to (every person whose name is "$NAME_ESCAPED")
    else
        set matchedPeople to (every person whose name contains "$NAME_ESCAPED")
    end if

    if (count of matchedPeople) is 0 then
        return "No contact found matching criteria."
    end if

    set output to ""

    repeat with p in matchedPeople
        set output to output & "=== CONTACT CARD ===" & return & return

        -- ID
        set output to output & "ID: " & id of p & return

        -- Names
        try
            set fn to first name of p
            if fn is not missing value then
                set output to output & "First Name: " & fn & return
            end if
        end try
        try
            set ln to last name of p
            if ln is not missing value then
                set output to output & "Last Name: " & ln & return
            end if
        end try
        set output to output & "Full Name: " & name of p & return

        -- Organization and Job Title
        try
            set org to organization of p
            if org is not missing value and org is not "" then
                set output to output & "Organization: " & org & return
            end if
        end try
        try
            set jt to job title of p
            if jt is not missing value and jt is not "" then
                set output to output & "Job Title: " & jt & return
            end if
        end try

        -- Emails with labels
        try
            set emailList to emails of p
            if (count of emailList) > 0 then
                set output to output & return & "Emails:" & return
                repeat with e in emailList
                    set eLabel to label of e
                    set eValue to value of e
                    -- Clean up label (remove _$!<>!$_ wrapping)
                    set cleanLabel to do shell script "echo " & quoted form of eLabel & " | sed 's/_\\$!<//;s/>!\\$_//'"
                    set output to output & "  " & cleanLabel & ": " & eValue & return
                end repeat
            end if
        end try

        -- Phones with labels
        try
            set phoneList to phones of p
            if (count of phoneList) > 0 then
                set output to output & return & "Phones:" & return
                repeat with ph in phoneList
                    set phLabel to label of ph
                    set phValue to value of ph
                    set cleanLabel to do shell script "echo " & quoted form of phLabel & " | sed 's/_\\$!<//;s/>!\\$_//'"
                    set output to output & "  " & cleanLabel & ": " & phValue & return
                end repeat
            end if
        end try

        -- Addresses with labels
        try
            set addrList to addresses of p
            if (count of addrList) > 0 then
                set output to output & return & "Addresses:" & return
                repeat with a in addrList
                    set aLabel to label of a
                    set cleanLabel to do shell script "echo " & quoted form of aLabel & " | sed 's/_\\$!<//;s/>!\\$_//'"
                    set output to output & "  " & cleanLabel & ":" & return
                    try
                        set s to street of a
                        if s is not missing value and s is not "" then
                            set output to output & "    Street: " & s & return
                        end if
                    end try
                    try
                        set c to city of a
                        if c is not missing value and c is not "" then
                            set output to output & "    City: " & c & return
                        end if
                    end try
                    try
                        set st to state of a
                        if st is not missing value and st is not "" then
                            set output to output & "    State: " & st & return
                        end if
                    end try
                    try
                        set z to zip of a
                        if z is not missing value and z is not "" then
                            set output to output & "    ZIP: " & z & return
                        end if
                    end try
                    try
                        set co to country of a
                        if co is not missing value and co is not "" then
                            set output to output & "    Country: " & co & return
                        end if
                    end try
                end repeat
            end if
        end try

        -- Birthday
        try
            set bday to birth date of p
            if bday is not missing value then
                set output to output & return & "Birthday: " & (bday as string) & return
            end if
        end try

        -- Notes
        try
            set n to note of p
            if n is not missing value and n is not "" then
                set output to output & return & "Notes: " & n & return
            end if
        end try

        -- Groups
        try
            set groupList to groups of p
            if (count of groupList) > 0 then
                set output to output & return & "Groups:" & return
                repeat with g in groupList
                    set output to output & "  - " & name of g & return
                end repeat
            end if
        end try

        set output to output & return
    end repeat

    if (count of matchedPeople) > 1 then
        set output to output & "Found " & (count of matchedPeople) & " matching contacts." & return
    end if

    return output
end tell
EOF
