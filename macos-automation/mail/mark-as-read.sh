#!/bin/bash
# ==============================================================================
# mark-as-read.sh - Mark emails as read
# ==============================================================================
# Description:
#   Marks emails as read based on various criteria. Can mark all unread,
#   specific sender's emails, or emails with specific subject patterns.
#
# Usage:
#   ./mark-as-read.sh --all
#   ./mark-as-read.sh --sender <pattern>
#   ./mark-as-read.sh --subject <pattern>
#   ./mark-as-read.sh --older-than <days>
#
# Options:
#   --all                Mark all unread emails as read
#   --sender <pattern>   Mark emails from sender matching pattern
#   --subject <pattern>  Mark emails with subject matching pattern
#   --older-than <days>  Mark emails older than n days
#   --dry-run            Show what would be marked without actually marking
#
# Example:
#   ./mark-as-read.sh --all
#   ./mark-as-read.sh --sender "newsletter@"
#   ./mark-as-read.sh --older-than 30
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
MARK_ALL=false
SENDER_PATTERN=""
SUBJECT_PATTERN=""
OLDER_THAN=""
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            MARK_ALL=true
            shift
            ;;
        --sender)
            SENDER_PATTERN="$2"
            shift 2
            ;;
        --subject)
            SUBJECT_PATTERN="$2"
            shift 2
            ;;
        --older-than)
            OLDER_THAN="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            head -35 "$0" | tail -30
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate that at least one filter is specified
if [[ "$MARK_ALL" == "false" && -z "$SENDER_PATTERN" && -z "$SUBJECT_PATTERN" && -z "$OLDER_THAN" ]]; then
    error_exit "Please specify --all, --sender, --subject, or --older-than"
fi

# Build filter condition
FILTER=""
if [[ "$MARK_ALL" == "true" ]]; then
    FILTER="read status is false"
elif [[ -n "$SENDER_PATTERN" ]]; then
    FILTER="read status is false and sender contains \"$SENDER_PATTERN\""
elif [[ -n "$SUBJECT_PATTERN" ]]; then
    FILTER="read status is false and subject contains \"$SUBJECT_PATTERN\""
fi

if [[ -n "$OLDER_THAN" ]]; then
    osascript <<EOF
tell application "Mail"
    set cutoffDate to (current date) - ($OLDER_THAN * 24 * 60 * 60)
    set targetMsgs to (messages of inbox whose read status is false and date received < cutoffDate)
    set msgCount to count of targetMsgs

    if msgCount is 0 then
        return "No unread messages older than $OLDER_THAN days."
    end if

    if $DRY_RUN then
        return "Would mark " & msgCount & " messages as read."
    else
        repeat with msg in targetMsgs
            set read status of msg to true
        end repeat
        return "Marked " & msgCount & " messages as read."
    end if
end tell
EOF
else
    osascript <<EOF
tell application "Mail"
    set targetMsgs to (messages of inbox whose $FILTER)
    set msgCount to count of targetMsgs

    if msgCount is 0 then
        return "No matching unread messages found."
    end if

    if $DRY_RUN then
        return "Would mark " & msgCount & " messages as read."
    else
        repeat with msg in targetMsgs
            set read status of msg to true
        end repeat
        return "Marked " & msgCount & " messages as read."
    end if
end tell
EOF
fi
