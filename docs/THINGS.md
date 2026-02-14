# Things3 Integration

Son of Simon integrates with [Things3](https://culturedcode.com/things/) by Cultured Code, a native macOS task manager, through AppleScript automation. No configuration required — if Things3 is installed and Automation permission is granted, it works out of the box.

## How It Works

Things3 has a rich AppleScript dictionary. Son of Simon wraps AppleScript commands in shell scripts and calls them through the agent's tool system.

```
Son of Simon → shell script → osascript (AppleScript) → Things3.app
```

Changes appear instantly in Things3 since they go through the app's own scripting interface.

## Setup

1. **Install Things3** from the [Mac App Store](https://apps.apple.com/app/things-3/id904280696) or [Cultured Code](https://culturedcode.com/things/).

2. **Grant Automation permission** — the first time Son of Simon tries to control Things3, macOS will prompt for permission. Click "OK".

3. **Verify** the integration:

```
> son run "show my Things today list"
```

No environment variables or configuration files are needed.

## What You Can Do

### Viewing To-Dos

| Action | Example |
|--------|---------|
| See Today list | "Show my Things today list" |
| See Inbox | "What's in my Things inbox?" |
| List by project | "Show to-dos in the Work project" |
| List by tag | "Show to-dos tagged urgent" |
| Search | "Search Things for dentist appointment" |

### Creating To-Dos

| Action | Example |
|--------|---------|
| Simple to-do | "Add a to-do to buy milk" |
| With due date | "Add a to-do to submit report due Friday" |
| With project | "Add a to-do to review docs in the Work project" |
| With tags | "Add a to-do to call mom tagged personal, family" |
| Scheduled | "Add a to-do to review inbox for today" |
| With notes | "Add a to-do to prepare presentation with notes: include Q4 metrics" |

### Managing To-Dos

| Action | Example |
|--------|---------|
| Complete | "Mark the milk to-do as done" |
| Move to Today | "Move that to-do to Today" |
| Move to project | "Move that to-do to the Work project" |
| Update due date | "Change the due date to next Monday" |
| Update notes | "Add notes to that to-do: remember to check section 3" |
| Cancel | "Cancel the old meeting to-do" |

### Projects

| Action | Example |
|--------|---------|
| List projects | "Show my Things projects" |
| Project with counts | "Show projects with to-do counts" |
| Create project | "Create a project called Home Renovation" |
| Create with details | "Create a project called Q1 Report due March 31 tagged work" |

### Tags

| Action | Example |
|--------|---------|
| List tags | "What tags do I have in Things?" |
| Tags with counts | "Show my tags with counts" |

## Built-in Lists

Things3 has these built-in lists that you can reference by name:

| List | Description |
|------|-------------|
| **Inbox** | Unprocessed items — brain dump destination |
| **Today** | To-dos to focus on today |
| **Upcoming** | Scheduled for future dates |
| **Anytime** | Available to do anytime (no specific schedule) |
| **Someday** | Ideas for later, not yet committed |
| **Logbook** | Completed to-dos (read-only history) |
| **Trash** | Deleted items |

## Scheduling vs Due Dates

Things3 distinguishes between _when_ to work on something and _when_ it's due:

- **Schedule** ("today", "tomorrow", "someday") controls when the to-do appears in your lists
- **Due date** is the actual deadline

Example: "Schedule this for tomorrow but it's due Friday" sets the to-do to appear tomorrow with a Friday deadline.

## Available Tools

| Tool | Description |
|------|-------------|
| `show_things_today` | Show the Today list |
| `show_things_inbox` | Show the Inbox |
| `list_things_todos` | List to-dos with filters (list, project, tag, status) |
| `search_things_todos` | Search to-dos by name or notes text |
| `create_things_todo` | Create a to-do with name, notes, due date, tags, project, schedule |
| `complete_things_todo` | Mark to-do(s) as complete by name, pattern, or ID |
| `update_things_todo` | Update to-do properties (name, notes, due, tags, project, status) |
| `move_things_todo` | Move to-do to a built-in list or project |
| `list_things_projects` | List projects with optional to-do counts |
| `create_things_project` | Create a project with notes, due date, tags, area |
| `list_things_tags` | List all tags with optional usage counts |
