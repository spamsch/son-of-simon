#!/bin/bash
# ==============================================================================
# search-contacts.sh - Search contacts by name, email, phone, or organization
# ==============================================================================
# Description:
#   Searches contacts in Contacts.app matching specified criteria. Uses fast
#   'whose' clause for name and organization lookups. For email and phone,
#   iterates all people since Contacts.app doesn't support 'whose' on
#   multi-value properties reliably.
#
# Usage:
#   ./search-contacts.sh --name "John"
#   ./search-contacts.sh --email "example.com"
#   ./search-contacts.sh --phone "555"
#   ./search-contacts.sh --organization "Acme" --limit 10
#
# Options:
#   --name <pattern>          Search by contact name (contains match)
#   --email <pattern>         Search by email address (contains match)
#   --phone <pattern>         Search by phone number (contains match)
#   --organization <pattern>  Search by organization name (contains match)
#   --limit <n>               Limit results (default: 20)
#
# Example:
#   ./search-contacts.sh --name "Smith"
#   ./search-contacts.sh --email "@gmail.com" --limit 50
#   ./search-contacts.sh --organization "Apple" --name "John"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
NAME_PATTERN=""
EMAIL_PATTERN=""
PHONE_PATTERN=""
ORG_PATTERN=""
LIMIT=20

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            NAME_PATTERN="$2"
            shift 2
            ;;
        --email)
            EMAIL_PATTERN="$2"
            shift 2
            ;;
        --phone)
            PHONE_PATTERN="$2"
            shift 2
            ;;
        --organization)
            ORG_PATTERN="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            head -28 "$0" | tail -27
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate - at least one search criterion required
if [[ -z "$NAME_PATTERN" && -z "$EMAIL_PATTERN" && -z "$PHONE_PATTERN" && -z "$ORG_PATTERN" ]]; then
    error_exit "At least one search criterion required: --name, --email, --phone, or --organization"
fi

# Escape for AppleScript
NAME_ESCAPED=$(escape_for_applescript "$NAME_PATTERN")
EMAIL_ESCAPED=$(escape_for_applescript "$EMAIL_PATTERN")
PHONE_ESCAPED=$(escape_for_applescript "$PHONE_PATTERN")
ORG_ESCAPED=$(escape_for_applescript "$ORG_PATTERN")

osascript <<EOF
tell application "Contacts"
    set matchedPeople to {}

    -- Determine search strategy based on criteria
    -- Name and organization support fast 'whose' clause
    -- Email and phone require iteration over multi-value properties

    if "$EMAIL_ESCAPED" is not "" or "$PHONE_ESCAPED" is not "" then
        -- Need to iterate: get candidate set first
        if "$NAME_ESCAPED" is not "" and "$ORG_ESCAPED" is not "" then
            set candidates to (every person whose name contains "$NAME_ESCAPED" and organization contains "$ORG_ESCAPED")
        else if "$NAME_ESCAPED" is not "" then
            set candidates to (every person whose name contains "$NAME_ESCAPED")
        else if "$ORG_ESCAPED" is not "" then
            set candidates to (every person whose organization contains "$ORG_ESCAPED")
        else
            set candidates to every person
        end if

        repeat with p in candidates
            if (count of matchedPeople) >= $LIMIT then exit repeat

            set includeContact to true

            -- Filter by email
            if "$EMAIL_ESCAPED" is not "" then
                set emailMatch to false
                try
                    set emailList to value of emails of p
                    repeat with e in emailList
                        if e contains "$EMAIL_ESCAPED" then
                            set emailMatch to true
                            exit repeat
                        end if
                    end repeat
                end try
                if not emailMatch then set includeContact to false
            end if

            -- Filter by phone
            if includeContact and "$PHONE_ESCAPED" is not "" then
                set phoneMatch to false
                try
                    set phoneList to value of phones of p
                    repeat with ph in phoneList
                        if ph contains "$PHONE_ESCAPED" then
                            set phoneMatch to true
                            exit repeat
                        end if
                    end repeat
                end try
                if not phoneMatch then set includeContact to false
            end if

            if includeContact then
                set end of matchedPeople to p
            end if
        end repeat
    else
        -- Fast path: only name and/or organization criteria (use 'whose')
        if "$NAME_ESCAPED" is not "" and "$ORG_ESCAPED" is not "" then
            set matchedPeople to (every person whose name contains "$NAME_ESCAPED" and organization contains "$ORG_ESCAPED")
        else if "$NAME_ESCAPED" is not "" then
            set matchedPeople to (every person whose name contains "$NAME_ESCAPED")
        else if "$ORG_ESCAPED" is not "" then
            set matchedPeople to (every person whose organization contains "$ORG_ESCAPED")
        end if
    end if

    set totalFound to count of matchedPeople
    if totalFound is 0 then
        return "No contacts found matching criteria."
    end if

    -- Cap at limit
    if totalFound > $LIMIT then
        set displayCount to $LIMIT
    else
        set displayCount to totalFound
    end if

    set output to "=== FOUND " & totalFound & " CONTACT(S) ===" & return & return

    repeat with i from 1 to displayCount
        set p to item i of matchedPeople

        set output to output & "Name: " & name of p & return

        -- Emails
        try
            set emailList to emails of p
            if (count of emailList) > 0 then
                repeat with e in emailList
                    set output to output & "Email: " & value of e & return
                end repeat
            end if
        end try

        -- Phones
        try
            set phoneList to phones of p
            if (count of phoneList) > 0 then
                repeat with ph in phoneList
                    set output to output & "Phone: " & value of ph & return
                end repeat
            end if
        end try

        -- Organization
        try
            set org to organization of p
            if org is not missing value and org is not "" then
                set output to output & "Organization: " & org & return
            end if
        end try

        set output to output & "---" & return
    end repeat

    if totalFound > $LIMIT then
        set output to output & return & "Showing " & displayCount & " of " & totalFound & " results (limit: $LIMIT)"
    end if

    return output
end tell
EOF
