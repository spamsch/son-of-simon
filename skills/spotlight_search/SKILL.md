---
id: spotlight_search
name: Spotlight Search
description: Fast indexed search for files and documents on disk using macOS Spotlight (mdfind).
apps:
  - Spotlight
  - Finder
tasks:
  - spotlight_search
examples:
  - "Find PDFs containing budget"
  - "Search for files named meeting notes"
  - "Find documents modified in the last 3 days"
  - "Search for images in my Downloads folder"
  - "Find spreadsheets about revenue"
  - "Look for presentations created this week"
safe_defaults:
  limit: 20
  days: 30
confirm_before_write: []
requires_permissions: []
---

## Behavior Notes

### What This Tool Does

`spotlight_search` uses macOS Spotlight (mdfind) to search the system's pre-built file index. Searches are extremely fast (milliseconds) because they query an existing index rather than scanning files.

### Important: Does NOT Search Mail.app

Mail.app uses Core Spotlight, a separate private index that is NOT accessible via `mdfind`. To search emails in Mail.app, always use `search_emails` (AppleScript-based). This tool can find `.eml` files stored on disk (e.g., in OneDrive, Downloads), but not messages in Mail.app mailboxes.

### File and Document Search

This is the primary use case. Search by:
- `file_name` — file name pattern (partial match, case-insensitive)
- `query` — full-text content search across file contents
- `body` — alias for content text search
- `content_type` — filter by file type
- `days` — limit to recently modified files
- `directory` — restrict search to a specific directory

### Content Types

| Type           | What it matches                           |
|----------------|-------------------------------------------|
| `pdf`          | PDF documents                             |
| `image`        | All image formats (PNG, JPG, HEIC, etc.)  |
| `document`     | Text documents, Word, Pages, etc.         |
| `presentation` | Keynote, PowerPoint                       |
| `spreadsheet`  | Numbers, Excel                            |
| `email`        | .eml files on disk (NOT Mail.app inbox)   |

### Common Patterns

- **"find PDF named X"** -> `spotlight_search(file_name="X", content_type="pdf")`
- **"documents modified today"** -> `spotlight_search(content_type="document", days=1)`
- **"search files for X in Downloads"** -> `spotlight_search(query="X", directory="~/Downloads")`
- **"find images larger than..."** -> `spotlight_search(content_type="image", days=7)` (then check sizes in results)
- **"search all spreadsheets for budget"** -> `spotlight_search(query="budget", content_type="spreadsheet")`
- **"find recent presentations"** -> `spotlight_search(content_type="presentation", days=14)`

### Email-Related Parameters

The `sender`, `recipient`, `subject`, `unread`, `flagged`, and `has_attachments` parameters search Spotlight email metadata attributes. These only work for `.eml` files stored on disk (e.g., saved emails, OneDrive archives), NOT for Mail.app mailbox messages.

### Output Format

**For files:** Shows Name, Path, Type, Size, and Modified date.
**For emails (.eml):** Shows Subject, From, Date, Status, Message-ID, and Attachments (when metadata is available).
