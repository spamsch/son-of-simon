# Mindwtr Integration

Son of Simon integrates with [Mindwtr](https://mindwtr.com), a Getting Things Done (GTD) productivity app, through direct file access. No server or API required — Son of Simon reads and writes the Mindwtr sync file, and the desktop app refreshes automatically.

## How It Works

Mindwtr stores its data in a JSON file (`data.json`) and supports file-based sync via a shared folder. The desktop app watches this folder for changes and refreshes the UI within ~750ms.

Son of Simon reads and writes this file directly:

```
Son of Simon → writes ~/Sync/mindwtr/data.json → Mindwtr file watcher → UI refreshes
```

This means you can create, update, complete, and search tasks through natural language, and see changes appear live in the Mindwtr app.

## Setup

1. **Enable file-based sync** in the Mindwtr desktop app (Settings → Sync → File Sync) and note the sync folder path.

2. **Configure the data path** in `~/.macbot/.env`:

```bash
MACBOT_MINDWTR_DATA_PATH=~/Sync/mindwtr/data.json
```

The default path is `~/Sync/mindwtr/data.json`. Adjust if your sync folder is elsewhere.

3. **Verify** the integration:

```
> son run "show my mindwtr inbox"
```

## What You Can Do

### Task Management

| Action | Example |
|--------|---------|
| Add a task | "Add buy groceries to my mindwtr inbox" |
| Quick-add with metadata | "Add review invoice @work #finance /due:tomorrow /priority:high +Accounting" |
| List tasks | "Show me my next actions" |
| Filter by status | "What's in my inbox?" |
| Search | "Search my tasks for dentist" |
| Complete | "Mark the grocery task as done" |
| Update | "Move that task to the waiting list" |
| Delete | "Delete the old test task" |

### Project Management

| Action | Example |
|--------|---------|
| List projects | "Show me all my projects" |
| Create project | "Create a project called Home Renovation" |
| Update project | "Set Home Renovation to someday" |

### Tags & Contexts

| Action | Example |
|--------|---------|
| List all tags | "What tags am I using?" |
| Filter by context | "Show tasks @work" |
| Filter by tag | "Show tasks #urgent" |

### GTD Workflows

| Workflow | Example |
|----------|---------|
| Inbox processing | "Let's process my inbox" |
| Daily review | "What should I work on today?" |
| Weekly review | "Let me review everything" |

## Quick-Add Syntax

When creating tasks, you can use Mindwtr's quick-add syntax in a single string:

| Token | Meaning | Example |
|-------|---------|---------|
| `@word` | Context | `@home`, `@work`, `@errands` |
| `#word` | Tag | `#shopping`, `#finance`, `#urgent` |
| `/due:date` | Due date | `/due:tomorrow`, `/due:next monday`, `/due:2026-03-01` |
| `/priority:level` | Priority | `/priority:high` (low, medium, high, urgent) |
| `+Name` | Project | `+Accounting`, `+HomeReno` |
| `/note:text` | Description | `/note:remember to bring receipt` |

**Example:**

```
"Review invoice @work /due:tomorrow /priority:high #finance +Accounting"
```

Creates a task titled "Review invoice" with context @work, due tomorrow, high priority, tagged #finance, assigned to the Accounting project.

## Task Statuses

Mindwtr follows the GTD methodology:

| Status | Meaning |
|--------|---------|
| `inbox` | Newly captured, not yet processed |
| `todo` | Processed, ready to be done |
| `next` | Next actions — do these now |
| `in-progress` | Currently being worked on |
| `waiting` | Delegated or waiting for someone |
| `someday` | Deferred ideas, maybe later |
| `done` | Completed |
| `archived` | Old completed tasks |

## Recurring Tasks

Tasks with recurrence rules (daily, weekly, monthly, yearly) automatically spawn a new instance when completed. The next occurrence is calculated based on the recurrence strategy:

- **Strict** (default): based on the original due date
- **Fluid**: based on the completion date

## Available Tools

| Tool | Description |
|------|-------------|
| `mindwtr_list_tasks` | List/filter tasks by status, query, completion state |
| `mindwtr_add_task` | Create task with quick-add syntax or explicit fields |
| `mindwtr_get_task` | Get full task details by ID |
| `mindwtr_update_task` | Update title, status, priority, due date, tags, contexts |
| `mindwtr_complete_task` | Mark done (handles recurrence) |
| `mindwtr_archive_task` | Archive a task |
| `mindwtr_delete_task` | Soft-delete a task |
| `mindwtr_list_projects` | List all active projects |
| `mindwtr_create_project` | Create a new project |
| `mindwtr_update_project` | Update project title, status, area |
| `mindwtr_list_tags` | List all tags and contexts with usage counts |
| `mindwtr_search` | Search tasks and projects by text, @context, #tag |
