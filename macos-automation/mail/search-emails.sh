#!/bin/bash
# ==============================================================================
# search-emails.sh - Search emails by sender, subject, or content
# ==============================================================================
# Description:
#   Searches the inbox for emails matching specified criteria. Can filter by
#   sender email/name, subject text, or limit results.
#
# Usage:
#   ./search-emails.sh --sender <pattern>
#   ./search-emails.sh --subject <pattern>
#   ./search-emails.sh --sender <pattern> --subject <pattern>
#   ./search-emails.sh --sender <pattern> --limit <n>
#
# Options:
#   --sender <pattern>   Search for emails from sender containing pattern
#   --subject <pattern>  Search for emails with subject containing pattern
#   --limit <n>          Limit results to n messages (default: 20)
#
# Example:
#   ./search-emails.sh --sender "john@example.com"
#   ./search-emails.sh --subject "Invoice" --limit 5
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
SENDER_PATTERN=""
SUBJECT_PATTERN=""
LIMIT=20

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --sender)
            SENDER_PATTERN="$2"
            shift 2
            ;;
        --subject)
            SUBJECT_PATTERN="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

if [[ -z "$SENDER_PATTERN" && -z "$SUBJECT_PATTERN" ]]; then
    error_exit "Please specify --sender or --subject pattern"
fi

# Build the AppleScript filter condition
FILTER_CONDITION=""
if [[ -n "$SENDER_PATTERN" && -n "$SUBJECT_PATTERN" ]]; then
    FILTER_CONDITION="sender contains \"$SENDER_PATTERN\" and subject contains \"$SUBJECT_PATTERN\""
elif [[ -n "$SENDER_PATTERN" ]]; then
    FILTER_CONDITION="sender contains \"$SENDER_PATTERN\""
else
    FILTER_CONDITION="subject contains \"$SUBJECT_PATTERN\""
fi

osascript <<EOF
tell application "Mail"
    set matchingMsgs to (messages of inbox whose $FILTER_CONDITION)
    set msgCount to count of matchingMsgs

    if msgCount is 0 then
        return "No messages found matching criteria."
    end if

    set displayCount to msgCount
    if displayCount > $LIMIT then
        set displayCount to $LIMIT
    end if

    set output to "=== FOUND " & msgCount & " MESSAGES (showing " & displayCount & ") ===" & return & return

    repeat with i from 1 to displayCount
        set msg to item i of matchingMsgs
        set output to output & "Subject: " & subject of msg & return
        set output to output & "From: " & sender of msg & return
        set output to output & "Date: " & (date received of msg as string) & return
        set output to output & "Read: " & read status of msg & return
        set output to output & "---" & return
    end repeat

    return output
end tell
EOF
