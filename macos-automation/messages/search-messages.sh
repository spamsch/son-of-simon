#!/bin/bash
# ==============================================================================
# search-messages.sh - Search iMessage/SMS history in Messages.app
# ==============================================================================
# Description:
#   Searches the Messages database (chat.db) for messages matching text content
#   and/or sender handle. Uses read-only SQLite access. Requires Full Disk
#   Access for the calling process.
#
# Usage:
#   ./search-messages.sh --query <text>
#   ./search-messages.sh --from <handle>
#   ./search-messages.sh --query <text> --from <handle> --days 30
#
# Options:
#   --query <text>     Search for messages containing text
#   --from <handle>    Filter by sender phone number or email
#   --days <n>         Only search messages from last n days (default: 7)
#   --limit <n>        Maximum number of results (default: 20)
#
# Example:
#   ./search-messages.sh --query "dinner" --days 14
#   ./search-messages.sh --from "+15551234567" --limit 10
#   ./search-messages.sh --query "meeting" --from "john@example.com" --days 30
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
QUERY=""
FROM=""
DAYS=7
LIMIT=20

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --query)
            QUERY="$2"
            shift 2
            ;;
        --from)
            FROM="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            head -25 "$0" | tail -20
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate: at least --query or --from required
if [[ -z "$QUERY" && -z "$FROM" ]]; then
    error_exit "At least --query or --from is required"
fi

# Check if chat.db exists and is readable
CHAT_DB="$HOME/Library/Messages/chat.db"
if [[ ! -f "$CHAT_DB" ]]; then
    error_exit "Messages database not found at $CHAT_DB"
fi

if [[ ! -r "$CHAT_DB" ]]; then
    error_exit "Full Disk Access required. Grant in System Settings > Privacy & Security > Full Disk Access"
fi

# Build WHERE clauses
WHERE_CLAUSES="m.date/1000000000 + 978307200 > CAST(strftime('%s', 'now', '-${DAYS} days') AS INTEGER)"

if [[ -n "$QUERY" ]]; then
    # Escape single quotes for SQL
    QUERY_SQL="${QUERY//\'/\'\'}"
    WHERE_CLAUSES="$WHERE_CLAUSES AND m.text LIKE '%${QUERY_SQL}%'"
fi

if [[ -n "$FROM" ]]; then
    FROM_SQL="${FROM//\'/\'\'}"
    WHERE_CLAUSES="$WHERE_CLAUSES AND h.id LIKE '%${FROM_SQL}%'"
fi

# Query the Messages database (read-only mode)
RESULT=$(sqlite3 "file:${CHAT_DB}?mode=ro" <<SQL 2>&1
.headers off
.mode list
.separator "|"
SELECT
    datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS msg_date,
    COALESCE(h.id, 'me') AS sender,
    COALESCE(c.chat_identifier, '') AS chat,
    REPLACE(SUBSTR(COALESCE(m.text, ''), 1, 200), CHAR(10), ' ') AS text
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
LEFT JOIN chat c ON cmj.chat_id = c.ROWID
WHERE $WHERE_CLAUSES
  AND m.text IS NOT NULL
  AND m.text != ''
ORDER BY m.date DESC
LIMIT ${LIMIT};
SQL
)

# Check for errors
if [[ $? -ne 0 ]]; then
    if echo "$RESULT" | grep -qi "authorization denied\|unable to open\|not authorized"; then
        error_exit "Full Disk Access required. Grant in System Settings > Privacy & Security > Full Disk Access"
    else
        error_exit "Failed to query Messages database: $RESULT"
    fi
fi

if [[ -z "$RESULT" ]]; then
    echo "No messages found matching criteria in the last $DAYS day(s)."
    exit 0
fi

# Format and display results
MSG_COUNT=0
SEARCH_DESC=""
if [[ -n "$QUERY" ]]; then
    SEARCH_DESC="query=\"$QUERY\""
fi
if [[ -n "$FROM" ]]; then
    [[ -n "$SEARCH_DESC" ]] && SEARCH_DESC="$SEARCH_DESC, "
    SEARCH_DESC="${SEARCH_DESC}from=\"$FROM\""
fi

echo "=== MESSAGE SEARCH ($SEARCH_DESC, last $DAYS days) ==="
echo ""

while IFS='|' read -r msg_date sender chat text; do
    MSG_COUNT=$((MSG_COUNT + 1))
    echo "Date: $msg_date"
    echo "From: $sender"
    if [[ -n "$chat" ]]; then
        echo "Chat: $chat"
    fi
    echo "Text: $text"
    echo "---"
done <<< "$RESULT"

echo ""
echo "Found $MSG_COUNT message(s)"
