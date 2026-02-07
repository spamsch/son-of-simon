---
id: whatsapp_assistant
name: WhatsApp Assistant
description: Read, search, and send WhatsApp messages using whatsapp-cli.
apps:
  - WhatsApp
tasks:
  - run_shell_command
examples:
  - "Show my recent WhatsApp chats"
  - "Read messages from Mom"
  - "Send a WhatsApp to +1234567890 saying I'm on my way"
  - "Search WhatsApp messages for flight confirmation"
  - "Find the contact for John"
safe_defaults:
  limit: 20
  store: ~/.macbot/whatsapp
confirm_before_write:
  - send message
requires_permissions: []
---

## Behavior Notes

### Tool
All commands use `run_shell_command` to invoke `whatsapp-cli` with `--store ~/.macbot/whatsapp`.

### Authentication
- First-time setup: `whatsapp-cli auth --store ~/.macbot/whatsapp`
- This displays a QR code the user must scan with WhatsApp on their phone
- Session persists ~20 days before re-authentication is needed
- If any command fails with an auth error, tell the user to run auth again

### Syncing Messages
- `whatsapp-cli sync --store ~/.macbot/whatsapp` downloads history and receives real-time messages
- Sync runs continuously until Ctrl+C — the user should run it in the background or before querying
- Messages are stored locally in a SQLite database at `~/.macbot/whatsapp/messages.db`
- If message queries return empty results, suggest the user runs sync first

### Listing Chats
- `whatsapp-cli chats list --store ~/.macbot/whatsapp`
- Filter by name: `--query "Mom"`
- Pagination: `--limit 20 --page 0`
- Results are sorted by most recent activity
- Each chat includes a JID (WhatsApp identifier) needed for other commands

### Reading Messages
- List messages from a specific chat: `whatsapp-cli messages list --chat <JID> --store ~/.macbot/whatsapp`
- List all recent messages: `whatsapp-cli messages list --store ~/.macbot/whatsapp`
- Pagination: `--limit 20 --page 0`
- Messages are sorted newest-first

### Searching Messages
- `whatsapp-cli messages search --query "search term" --store ~/.macbot/whatsapp`
- Search is case-insensitive with partial matching
- Pagination: `--limit 20 --page 0`

### Finding Contacts
- `whatsapp-cli contacts search --query "John" --store ~/.macbot/whatsapp`
- Returns name, phone number, and JID
- Maximum 50 results, sorted alphabetically

### Sending Messages
- To a phone number: `whatsapp-cli send --to <JID> --message "text" --store ~/.macbot/whatsapp`
- Individual JIDs look like: `1234567890@s.whatsapp.net`
- Group JIDs look like: `123456789-987654321@g.us`
- Always confirm message content with the user before sending

### JID Format
- **Individual**: phone number without `+` followed by `@s.whatsapp.net` (e.g. `1234567890@s.whatsapp.net`)
- **Group**: group ID followed by `@g.us`
- To send to a phone number, construct the JID: strip `+` and spaces, append `@s.whatsapp.net`

### Common Request Patterns
- **"my recent chats"** → `chats list` to show conversations
- **"messages from X"** → `chats list --query "X"` to find the JID, then `messages list --chat <JID>`
- **"send X a message"** → `contacts search --query "X"` to find JID, confirm message, then `send`
- **"search for X"** → `messages search --query "X"`
- **"unread messages"** → `messages list --limit 20` (most recent messages across chats)

### Output Format
- All whatsapp-cli commands return JSON
- Parse the JSON output to present results in a readable format to the user
- Show sender name, timestamp, and message content when displaying messages
