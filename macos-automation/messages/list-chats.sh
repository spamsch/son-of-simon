#!/bin/bash
# ==============================================================================
# list-chats.sh - List recent iMessage/SMS chats from Messages.app
# ==============================================================================
# Description:
#   Lists recent chats by querying the Messages database (chat.db) using
#   read-only SQLite access. Shows chat display name or identifier, last
#   message date, message preview, and message count per chat.
#   Requires Full Disk Access for the calling process.
#
# Usage:
#   ./list-chats.sh
#   ./list-chats.sh --limit 10
#   ./list-chats.sh --days 30
#
# Options:
#   --limit <n>    Maximum number of chats to return (default: 20)
#   --days <n>     Only show chats with messages in the last n days (default: 7)
#
# Example:
#   ./list-chats.sh --limit 10 --days 14
#   ./list-chats.sh --days 30
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
LIMIT=20
DAYS=7

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        -h|--help)
            head -23 "$0" | tail -18
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Check if chat.db exists and is readable
CHAT_DB="$HOME/Library/Messages/chat.db"
if [[ ! -f "$CHAT_DB" ]]; then
    error_exit "Messages database not found at $CHAT_DB"
fi

if [[ ! -r "$CHAT_DB" ]]; then
    error_exit "Full Disk Access required. Grant in System Settings > Privacy & Security > Full Disk Access"
fi

# Query the Messages database (read-only mode)
# Apple epoch: nanoseconds since 2001-01-01 → date/1000000000 + 978307200 = Unix timestamp
RESULT=$(sqlite3 "file:${CHAT_DB}?mode=ro" <<SQL 2>&1
.headers off
.mode list
.separator "|"
SELECT
    c.chat_identifier,
    COALESCE(NULLIF(c.display_name, ''), c.chat_identifier) AS display,
    datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS last_msg_date,
    REPLACE(SUBSTR(COALESCE(m.text, ''), 1, 100), CHAR(10), ' ') AS preview,
    COUNT(cmj.message_id) AS msg_count
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
WHERE m.date/1000000000 + 978307200 > CAST(strftime('%s', 'now', '-${DAYS} days') AS INTEGER)
GROUP BY c.ROWID
HAVING m.date = MAX(m.date)
ORDER BY m.date DESC
LIMIT ${LIMIT};
SQL
)

# Check for errors (e.g., Full Disk Access denied)
if [[ $? -ne 0 ]]; then
    if echo "$RESULT" | grep -qi "authorization denied\|unable to open\|not authorized"; then
        error_exit "Full Disk Access required. Grant in System Settings > Privacy & Security > Full Disk Access"
    else
        error_exit "Failed to query Messages database: $RESULT"
    fi
fi

if [[ -z "$RESULT" ]]; then
    echo "No chats found in the last $DAYS day(s)."
    exit 0
fi

# Format and display results
CHAT_COUNT=0
echo "=== RECENT CHATS (last $DAYS days) ==="
echo ""

while IFS='|' read -r identifier display last_date preview msg_count; do
    CHAT_COUNT=$((CHAT_COUNT + 1))
    echo "Chat: $display"
    echo "  Identifier: $identifier"
    echo "  Last message: $last_date"
    echo "  Messages: $msg_count"
    if [[ -n "$preview" ]]; then
        echo "  Preview: $preview"
    fi
    echo "---"
done <<< "$RESULT"

echo ""
echo "Showing $CHAT_COUNT chat(s)"
