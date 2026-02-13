#!/bin/bash
# ==============================================================================
# send-message.sh - Send an iMessage or SMS via Messages.app
# ==============================================================================
# Description:
#   Sends a message to a recipient using Apple Messages. Attempts to send via
#   iMessage first, and falls back to SMS if iMessage service is unavailable.
#
# Usage:
#   ./send-message.sh --to <phone_or_email> --body <text>
#
# Options:
#   --to <address>     Recipient phone number or email (required)
#   --body <text>      Message body text (required)
#
# Example:
#   ./send-message.sh --to "+15551234567" --body "Hey, are you free tonight?"
#   ./send-message.sh --to "john@example.com" --body "Check your email"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
TO=""
BODY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --to)
            TO="$2"
            shift 2
            ;;
        --body)
            BODY="$2"
            shift 2
            ;;
        -h|--help)
            head -20 "$0" | tail -15
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate required fields
[[ -z "$TO" ]] && error_exit "--to is required"
[[ -z "$BODY" ]] && error_exit "--body is required"

# Escape special characters for AppleScript
TO_ESCAPED=$(escape_for_applescript "$TO")
BODY_ESCAPED=$(escape_for_applescript "$BODY")

osascript <<EOF
tell application "Messages"
    set recipientAddr to "$TO_ESCAPED"
    set bodyText to "$BODY_ESCAPED"

    -- Try iMessage first
    set targetService to missing value
    try
        set targetService to 1st service whose service type = iMessage
    end try

    if targetService is not missing value then
        try
            set targetBuddy to a buddy targetService whose handle is recipientAddr
            send bodyText to targetBuddy
            return "Message sent to " & recipientAddr & " (iMessage)"
        on error iMsgErr
            -- iMessage buddy not found, try SMS
            set targetService to missing value
        end try
    end if

    -- Fall back to SMS
    if targetService is missing value then
        try
            set targetService to 1st service whose service type = SMS
        on error
            return "Error: No iMessage or SMS service available"
        end try

        try
            set targetBuddy to a buddy targetService whose handle is recipientAddr
            send bodyText to targetBuddy
            return "Message sent to " & recipientAddr & " (SMS)"
        on error smsErr
            return "Error: Could not send message to " & recipientAddr & ". " & smsErr
        end try
    end if
end tell
EOF
