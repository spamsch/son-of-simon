#!/bin/bash
# ==============================================================================
# create-contact.sh - Create a new contact in Contacts.app
# ==============================================================================
# Description:
#   Creates a new contact with the specified properties. Supports multiple
#   email addresses and phone numbers. Can optionally add the contact to
#   an existing group.
#
# Usage:
#   ./create-contact.sh --first-name "John"
#   ./create-contact.sh --first-name "John" --last-name "Smith" --email "john@example.com"
#   ./create-contact.sh --first-name "Jane" --email "jane@work.com" --email "jane@home.com"
#   ./create-contact.sh --first-name "Bob" --phone "+1-555-1234" --organization "Acme Inc"
#
# Options:
#   --first-name <text>      First name (required)
#   --last-name <text>       Last name
#   --email <address>        Email address (can be specified multiple times)
#   --phone <number>         Phone number (can be specified multiple times)
#   --organization <text>    Company/organization name
#   --job-title <text>       Job title
#   --group <name>           Add to existing group (error if group not found)
#
# Example:
#   ./create-contact.sh --first-name "John" --last-name "Doe" --email "john@example.com" --phone "+1-555-0123" --organization "Acme Inc" --group "Work"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
FIRST_NAME=""
LAST_NAME=""
EMAILS=()
PHONES=()
ORGANIZATION=""
JOB_TITLE=""
GROUP=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --first-name)
            FIRST_NAME="$2"
            shift 2
            ;;
        --last-name)
            LAST_NAME="$2"
            shift 2
            ;;
        --email)
            EMAILS+=("$2")
            shift 2
            ;;
        --phone)
            PHONES+=("$2")
            shift 2
            ;;
        --organization)
            ORGANIZATION="$2"
            shift 2
            ;;
        --job-title)
            JOB_TITLE="$2"
            shift 2
            ;;
        --group)
            GROUP="$2"
            shift 2
            ;;
        -h|--help)
            head -27 "$0" | tail -26
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate
[[ -z "$FIRST_NAME" ]] && error_exit "--first-name is required"

# Escape for AppleScript
FIRST_NAME_ESCAPED=$(escape_for_applescript "$FIRST_NAME")
LAST_NAME_ESCAPED=$(escape_for_applescript "$LAST_NAME")
ORG_ESCAPED=$(escape_for_applescript "$ORGANIZATION")
JOB_TITLE_ESCAPED=$(escape_for_applescript "$JOB_TITLE")
GROUP_ESCAPED=$(escape_for_applescript "$GROUP")

# Build properties string
PROPS="first name:\"$FIRST_NAME_ESCAPED\""

if [[ -n "$LAST_NAME" ]]; then
    PROPS="$PROPS, last name:\"$LAST_NAME_ESCAPED\""
fi

if [[ -n "$ORGANIZATION" ]]; then
    PROPS="$PROPS, organization:\"$ORG_ESCAPED\""
fi

if [[ -n "$JOB_TITLE" ]]; then
    PROPS="$PROPS, job title:\"$JOB_TITLE_ESCAPED\""
fi

# Build AppleScript for adding emails
ADD_EMAILS=""
for email in "${EMAILS[@]}"; do
    email_escaped=$(escape_for_applescript "$email")
    ADD_EMAILS="$ADD_EMAILS
        make new email at end of emails of newPerson with properties {label:\"work\", value:\"$email_escaped\"}"
done

# Build AppleScript for adding phones
ADD_PHONES=""
for phone in "${PHONES[@]}"; do
    phone_escaped=$(escape_for_applescript "$phone")
    ADD_PHONES="$ADD_PHONES
        make new phone at end of phones of newPerson with properties {label:\"mobile\", value:\"$phone_escaped\"}"
done

osascript <<EOF
tell application "Contacts"
    -- If group specified, verify it exists first
    if "$GROUP_ESCAPED" is not "" then
        try
            set targetGroup to group "$GROUP_ESCAPED"
        on error
            -- List available groups for helpful error message
            set groupNames to name of every group
            set AppleScript's text item delimiters to ", "
            set groupList to groupNames as text
            return "Error: Group '$GROUP_ESCAPED' not found. Available groups: " & groupList
        end try
    end if

    -- Create the contact
    set newPerson to make new person with properties {$PROPS}

    -- Add emails
    $ADD_EMAILS

    -- Add phones
    $ADD_PHONES

    -- Save changes
    save

    -- Add to group if specified
    if "$GROUP_ESCAPED" is not "" then
        add newPerson to group "$GROUP_ESCAPED"
        save
    end if

    -- Build confirmation output
    set output to "Created contact: " & name of newPerson & return
    set output to output & "ID: " & id of newPerson & return

    if (count of emails of newPerson) > 0 then
        repeat with e in emails of newPerson
            set output to output & "Email: " & value of e & return
        end repeat
    end if

    if (count of phones of newPerson) > 0 then
        repeat with ph in phones of newPerson
            set output to output & "Phone: " & value of ph & return
        end repeat
    end if

    if "$ORG_ESCAPED" is not "" then
        set output to output & "Organization: $ORG_ESCAPED" & return
    end if

    if "$JOB_TITLE_ESCAPED" is not "" then
        set output to output & "Job Title: $JOB_TITLE_ESCAPED" & return
    end if

    if "$GROUP_ESCAPED" is not "" then
        set output to output & "Group: $GROUP_ESCAPED" & return
    end if

    return output
end tell
EOF
