# Automating Apple Mail, Calendar, Reminders, Notes, and Safari on macOS via AppleScript

This document details the AppleScript automation capabilities of Apple's built-in Mail.app, Calendar.app, Reminders.app, Notes.app, and Safari on macOS. All five applications are **fully scriptable** and provide comprehensive programmatic access to email, calendar, task, notes, and web browsing data.

**Investigation Date**: January 29, 2026
**macOS Version**: Darwin 24.6.0
**Mail.app Version**: 16.0
**Calendar.app Version**: 15.0
**Reminders.app Version**: 7.0
**Notes.app Version**: 4.12.7
**Safari Version**: 18.6

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Mail.app Automation](#mailapp-automation)
   - [Accounts and Mailboxes](#accounts-and-mailboxes)
   - [Reading Messages](#reading-messages)
   - [Message Properties](#message-properties)
   - [Filtering and Searching](#filtering-and-searching)
   - [Attachments](#attachments)
   - [Modifying Messages](#modifying-messages)
   - [Sending Email](#sending-email)
3. [Calendar.app Automation](#calendarapp-automation)
   - [Calendars](#calendars)
   - [Reading Events](#reading-events)
   - [Event Properties](#event-properties)
   - [Creating Events](#creating-events)
   - [Modifying and Deleting Events](#modifying-and-deleting-events)
   - [Filtering Events](#filtering-events)
4. [Reminders.app Automation](#remindersapp-automation)
   - [Lists](#lists)
   - [Reading Reminders](#reading-reminders)
   - [Reminder Properties](#reminder-properties)
   - [Creating Reminders](#creating-reminders)
   - [Modifying and Completing Reminders](#modifying-and-completing-reminders)
   - [Filtering Reminders](#filtering-reminders)
5. [Notes.app Automation](#notesapp-automation)
   - [Accounts and Folders](#accounts-and-folders)
   - [Reading Notes](#reading-notes)
   - [Note Properties](#note-properties)
   - [Creating Notes](#creating-notes)
   - [Modifying and Deleting Notes](#modifying-and-deleting-notes)
   - [Searching Notes](#searching-notes)
   - [Attachments](#attachments-1)
6. [Safari Automation](#safari-automation)
   - [Windows and Tabs](#windows-and-tabs)
   - [Navigation](#navigation)
   - [Reading Page Content](#reading-page-content)
   - [JavaScript Execution](#javascript-execution)
   - [Reading List and Bookmarks](#reading-list-and-bookmarks)
   - [Web Scraping Example](#web-scraping-example)
7. [Comparison with Third-Party Apps](#comparison-with-third-party-apps)
8. [Quick Reference](#quick-reference)

---

## Executive Summary

| App | Scripting Support | Read | Write | Send/Create | Delete |
|-----|-------------------|------|-------|-------------|--------|
| **Mail.app** | Full | Yes | Yes | Yes | Yes |
| **Calendar.app** | Full | Yes | Yes | Yes | Yes |
| **Reminders.app** | Full | Yes | Yes | Yes | Yes |
| **Notes.app** | Full | Yes | Yes | Yes | Yes |
| **Safari** | Full | Yes | Yes | Yes | Yes |
| Microsoft Outlook (New) | Broken | No | No | No | No |
| BusyCal | Minimal | No | No | URL only | No |

**Key Finding**: Apple's native productivity suite (Mail.app, Calendar.app, Reminders.app, Notes.app, and Safari) provides complete AppleScript automation that third-party alternatives (New Outlook, BusyCal) do not offer. Since these apps can connect to the same accounts (Exchange, Google, iCloud), they serve as reliable automation endpoints regardless of which app you use for daily work. Safari adds web browsing automation, enabling web scraping, research automation, and integration with web-based services.

---

## Mail.app Automation

Mail.app provides full AppleScript access to all email functionality including reading, writing, sending, and managing messages.

### Accounts and Mailboxes

#### List All Accounts

```applescript
tell application "Mail"
    set allAccounts to every account
    repeat with a in allAccounts
        log name of a & " (" & (class of a as string) & ")"
    end repeat
end tell
```

**Sample Output**:
```
Account: waas.rent (account)
```

#### List Mailboxes for an Account

```applescript
tell application "Mail"
    set acct to account "waas.rent"
    set boxes to every mailbox of acct
    repeat with b in boxes
        log name of b
    end repeat
end tell
```

**Sample Output**:
```
Conversation History
Journal
Archive
Tasks
Notes
Inbox
Outbox
Drafts
Sent Items
Deleted Items
Junk Email
```

#### Access Special Mailboxes

```applescript
tell application "Mail"
    -- Global inbox (all accounts)
    set globalInbox to inbox

    -- Specific account's inbox
    set acctInbox to mailbox "Inbox" of account "waas.rent"

    -- Sent mailbox
    set sentBox to mailbox "Sent Items" of account "waas.rent"

    -- Drafts
    set draftsBox to mailbox "Drafts" of account "waas.rent"
end tell
```

### Reading Messages

#### List Inbox Messages

```applescript
tell application "Mail"
    set inboxMessages to messages of inbox
    set msgCount to count of inboxMessages

    repeat with i from 1 to 10
        set msg to item i of inboxMessages
        log subject of msg
        log "  From: " & sender of msg
        log "  Date: " & (date received of msg as string)
        log "  Read: " & read status of msg
    end repeat
end tell
```

**Sample Output**:
```
WG: Kündigung Austausch
  From: Jörg Rodehutskors <j.rodehutskors@ima-gt.de>
  Date: Thursday, 15. January 2026 at 17:27:08
  Read: true

waas board status
  From: Josip Puskar <puskarj@byte-lab.com>
  Date: Tuesday, 21. October 2025 at 16:21:16
  Read: true
```

#### Read Full Message Content

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox)

    log "Subject: " & subject of msg
    log "From: " & sender of msg
    log "To: " & (address of to recipient 1 of msg)
    log "Date: " & (date received of msg as string)
    log "Message ID: " & message id of msg
    log ""
    log "=== BODY ==="
    log content of msg
end tell
```

**Sample Output**:
```
Subject: WG: Kündigung Austausch
From: Jörg Rodehutskors <j.rodehutskors@ima-gt.de>
To: Simon@waas.rent
Date: Thursday, 15. January 2026 at 17:27:08
Message ID: FR2P281MB324524B8CAEF2761CA8EBC96C98CA@FR2P281MB3245.DEUP281.PROD.OUTLOOK.COM

=== BODY ===
Hi Simon,

leider erfahre ich erst jetzt von deiner Mail aus dem Dez an Katja, tut mir leid.
Katja ist noch länger krank und hat mir nun deine Info weitergeleitet.
Ja klar finden wir einen Weg, wenn wir helfen können, machen wir das!

Wann biste wieder hier, dann quatschen wir mal…

Viele Grüße
Jörg
```

### Message Properties

All available properties on a message object:

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `subject` | text | r/w | Subject line |
| `sender` | text | r | Sender's email and name |
| `content` | text | r | Plain text body |
| `date received` | date | r | When the message was received |
| `date sent` | date | r | When the message was sent |
| `read status` | boolean | r/w | Whether message has been read |
| `flagged status` | boolean | r/w | Whether message is flagged |
| `flag index` | integer | r/w | Flag color (0-7) |
| `junk mail status` | boolean | r/w | Whether marked as junk |
| `deleted status` | boolean | r/w | Whether marked for deletion |
| `was forwarded` | boolean | r | Whether message was forwarded |
| `was replied to` | boolean | r | Whether message was replied to |
| `message id` | text | r | Unique message identifier |
| `message size` | integer | r | Size in bytes |
| `all headers` | text | r | Raw email headers |
| `to recipients` | list | r | List of To recipients |
| `cc recipients` | list | r | List of CC recipients |
| `bcc recipients` | list | r | List of BCC recipients |
| `mail attachments` | list | r | List of attachments |

#### Get All Properties

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox)

    log "subject: " & subject of msg
    log "sender: " & sender of msg
    log "date received: " & (date received of msg as string)
    log "date sent: " & (date sent of msg as string)
    log "read status: " & read status of msg
    log "was forwarded: " & was forwarded of msg
    log "was replied to: " & was replied to of msg
    log "flagged status: " & flagged status of msg
    log "junk mail status: " & junk mail status of msg
    log "message size: " & message size of msg
    log "attachment count: " & (count of mail attachments of msg)
    log "to recipients: " & (count of to recipients of msg)
    log "cc recipients: " & (count of cc recipients of msg)
end tell
```

### Filtering and Searching

#### Filter Unread Messages

```applescript
tell application "Mail"
    set unreadMsgs to (messages of inbox whose read status is false)
    log "Unread count: " & (count of unreadMsgs)

    repeat with msg in unreadMsgs
        log subject of msg & " - " & sender of msg
    end repeat
end tell
```

#### Filter by Sender

```applescript
tell application "Mail"
    set msgsFromSender to (messages of inbox whose sender contains "example.com")
    repeat with msg in msgsFromSender
        log subject of msg
    end repeat
end tell
```

#### Filter by Subject

```applescript
tell application "Mail"
    set invoiceMsgs to (messages of inbox whose subject contains "Invoice")
    repeat with msg in invoiceMsgs
        log subject of msg & " | " & (date received of msg as string)
    end repeat
end tell
```

#### Filter by Date

```applescript
tell application "Mail"
    set cutoffDate to date "January 1, 2026"
    set recentMsgs to (messages of inbox whose date received > cutoffDate)
    log "Messages since Jan 1, 2026: " & (count of recentMsgs)
end tell
```

#### Combine Filters

```applescript
tell application "Mail"
    -- Unread messages containing "urgent" in subject
    set urgentUnread to (messages of inbox whose read status is false and subject contains "urgent")

    repeat with msg in urgentUnread
        log subject of msg
    end repeat
end tell
```

### Attachments

#### List Messages with Attachments

```applescript
tell application "Mail"
    set allMsgs to messages of inbox
    repeat with msg in allMsgs
        set attCount to count of mail attachments of msg
        if attCount > 0 then
            log "Subject: " & subject of msg
            log "  Attachments: " & attCount
            set atts to mail attachments of msg
            repeat with att in atts
                log "    - " & name of att
            end repeat
        end if
    end repeat
end tell
```

**Sample Output**:
```
Subject: WG: Kündigung Austausch
  Attachments: 5
    - image006.png
    - image005.jpg
    - image007.png
    - image008.png
    - image009.png
```

#### Attachment Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | text | Filename |
| `MIME type` | text | MIME content type |
| `file size` | integer | Size in bytes |
| `downloaded` | boolean | Whether fully downloaded |
| `id` | text | Unique identifier |

#### Save Attachment to Disk

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox whose (count of mail attachments) > 0)
    set att to item 1 of mail attachments of msg

    set savePath to ((path to downloads folder as text) & name of att)
    save att in file savePath
end tell
```

### Modifying Messages

#### Mark as Read/Unread

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox)

    -- Mark as read
    set read status of msg to true

    -- Mark as unread
    set read status of msg to false
end tell
```

#### Flag a Message

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox)

    -- Flag the message
    set flagged status of msg to true

    -- Set flag color (0-7)
    -- 0=red, 1=orange, 2=yellow, 3=green, 4=blue, 5=purple, 6=gray
    set flag index of msg to 0
end tell
```

#### Mark as Junk

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox)
    set junk mail status of msg to true
end tell
```

#### Delete a Message

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox)
    delete msg
end tell
```

#### Move Message to Another Mailbox

```applescript
tell application "Mail"
    set msg to item 1 of (messages of inbox)
    set targetBox to mailbox "Archive" of account "waas.rent"
    move msg to targetBox
end tell
```

### Sending Email

#### Create and Send a Simple Email

```applescript
tell application "Mail"
    set newMsg to make new outgoing message with properties {¬
        subject:"Test Email", ¬
        content:"Hello,\n\nThis is a test email.\n\nBest regards", ¬
        visible:true¬
    }

    tell newMsg
        make new to recipient at end of to recipients with properties {address:"recipient@example.com"}
    end tell

    -- Uncomment to send immediately:
    -- send newMsg
end tell
```

#### Send Email with CC and BCC

```applescript
tell application "Mail"
    set newMsg to make new outgoing message with properties {¬
        subject:"Team Update", ¬
        content:"Hi team,\n\nHere's the weekly update.\n\nBest"¬
    }

    tell newMsg
        make new to recipient at end of to recipients with properties {address:"team@example.com"}
        make new cc recipient at end of cc recipients with properties {address:"manager@example.com"}
        make new bcc recipient at end of bcc recipients with properties {address:"archive@example.com"}
    end tell

    send newMsg
end tell
```

#### Send Email with Attachment

```applescript
tell application "Mail"
    set newMsg to make new outgoing message with properties {¬
        subject:"Report Attached", ¬
        content:"Please find the report attached."¬
    }

    tell newMsg
        make new to recipient at end of to recipients with properties {address:"recipient@example.com"}
        make new attachment with properties {file name:"/Users/username/Documents/report.pdf"} at after last paragraph
    end tell

    send newMsg
end tell
```

#### Reply to a Message

```applescript
tell application "Mail"
    set originalMsg to item 1 of (messages of inbox)

    -- Opens reply window
    reply originalMsg with opening window

    -- Or reply all:
    -- reply originalMsg with opening window and reply to all
end tell
```

#### Forward a Message

```applescript
tell application "Mail"
    set originalMsg to item 1 of (messages of inbox)

    -- Opens forward window
    forward originalMsg with opening window
end tell
```

---

## Calendar.app Automation

Calendar.app provides full AppleScript access to calendars, events, and reminders.

### Calendars

#### List All Calendars

```applescript
tell application "Calendar"
    set allCals to every calendar
    repeat with c in allCals
        log name of c
    end repeat
end tell
```

**Sample Output**:
```
Home
Work
Privat
Birthdays
Deutsche Feiertage
Siri Suggestions
```

#### Calendar Properties

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `name` | text | r/w | Calendar name |
| `color` | RGB color | r/w | Calendar color |
| `description` | text | r/w | Calendar description |
| `writable` | boolean | r | Whether calendar can be modified |

#### Get Calendar by Name

```applescript
tell application "Calendar"
    set workCal to calendar "Work"
    log "Name: " & name of workCal
    log "Writable: " & writable of workCal
end tell
```

### Reading Events

#### List Events from a Calendar

```applescript
tell application "Calendar"
    set workCal to calendar "Work"
    set allEvents to every event of workCal

    repeat with evt in allEvents
        log summary of evt
        log "  Start: " & (start date of evt as string)
        log "  End: " & (end date of evt as string)
        log ""
    end repeat
end tell
```

**Sample Output**:
```
Team Meeting
  Start: Monday, 30. January 2026 at 10:00:00
  End: Monday, 30. January 2026 at 11:00:00

Project Review
  Start: Tuesday, 31. January 2026 at 14:00:00
  End: Tuesday, 31. January 2026 at 15:30:00
```

#### Get Event Count

```applescript
tell application "Calendar"
    repeat with c in every calendar
        set evtCount to count of events of c
        if evtCount > 0 then
            log (name of c) & ": " & evtCount & " events"
        end if
    end repeat
end tell
```

### Event Properties

All available properties on an event object:

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `summary` | text | r/w | Event title |
| `start date` | date | r/w | Start date and time |
| `end date` | date | r/w | End date and time |
| `allday event` | boolean | r/w | Whether it's an all-day event |
| `location` | text | r/w | Event location |
| `description` | text | r/w | Event notes/description |
| `url` | text | r/w | Associated URL |
| `uid` | text | r | Unique identifier |
| `status` | enum | r/w | none/cancelled/confirmed/tentative |
| `recurrence` | text | r/w | Recurrence rule (iCal format) |
| `excluded dates` | list | r/w | Dates excluded from recurrence |
| `sequence` | integer | r | Revision sequence number |
| `stamp date` | date | r | Last modification timestamp |

#### Get Full Event Details

```applescript
tell application "Calendar"
    set c to calendar "Privat"
    set evt to first event of c

    log "summary: " & summary of evt
    log "start date: " & (start date of evt as string)
    log "end date: " & (end date of evt as string)
    log "allday event: " & allday event of evt
    log "location: " & location of evt
    log "description: " & description of evt
    log "uid: " & uid of evt
    log "status: " & status of evt
    log "recurrence: " & recurrence of evt
end tell
```

**Sample Output**:
```
summary: Journey from Hannover Flughafen to Bielefeld Hbf
start date: Monday, 10. February 2014 at 00:06:00
end date: Monday, 10. February 2014 at 02:05:00
allday event: false
location: Hannover Flughafen
description: 1) S 5
    Dep 23:06 Hannover Flughafen, 2
    Arr 23:20 Hannover-Nordstadt, 2

2) S 1
    Dep 23:31 Hannover-Nordstadt, 1
    Arr 00:23 Minden(Westf), 12
uid: 4988F87B-F976-4E7E-960D-9022BD584277
status: none
recurrence: missing value
```

### Creating Events

#### Create a Simple Event

```applescript
tell application "Calendar"
    tell calendar "Work"
        make new event with properties {¬
            summary:"Team Meeting", ¬
            start date:date "January 30, 2026 2:00 PM", ¬
            end date:date "January 30, 2026 3:00 PM"¬
        }
    end tell
end tell
```

#### Create an All-Day Event

```applescript
tell application "Calendar"
    tell calendar "Work"
        make new event with properties {¬
            summary:"Company Holiday", ¬
            start date:date "February 14, 2026", ¬
            allday event:true¬
        }
    end tell
end tell
```

#### Create Event with Full Details

```applescript
tell application "Calendar"
    tell calendar "Work"
        make new event with properties {¬
            summary:"Project Kickoff", ¬
            start date:date "February 1, 2026 9:00 AM", ¬
            end date:date "February 1, 2026 10:30 AM", ¬
            location:"Conference Room A", ¬
            description:"Kickoff meeting for Q1 project.\n\nAgenda:\n1. Introductions\n2. Project overview\n3. Timeline review", ¬
            url:"https://example.com/project"¬
        }
    end tell
end tell
```

#### Create Recurring Event

```applescript
tell application "Calendar"
    tell calendar "Work"
        make new event with properties {¬
            summary:"Weekly Standup", ¬
            start date:date "February 3, 2026 9:00 AM", ¬
            end date:date "February 3, 2026 9:15 AM", ¬
            recurrence:"FREQ=WEEKLY;BYDAY=MO,WE,FR"¬
        }
    end tell
end tell
```

**Common Recurrence Rules**:
- Daily: `FREQ=DAILY`
- Weekly: `FREQ=WEEKLY`
- Weekly on specific days: `FREQ=WEEKLY;BYDAY=MO,WE,FR`
- Monthly: `FREQ=MONTHLY`
- Monthly on specific day: `FREQ=MONTHLY;BYMONTHDAY=15`
- Yearly: `FREQ=YEARLY`
- With end date: `FREQ=WEEKLY;UNTIL=20261231T235959Z`
- With count: `FREQ=DAILY;COUNT=10`

### Modifying and Deleting Events

#### Modify an Event

```applescript
tell application "Calendar"
    tell calendar "Work"
        set evt to first event whose summary is "Team Meeting"

        -- Update properties
        set summary of evt to "Updated Team Meeting"
        set location of evt to "Room 101"
        set start date of evt to date "January 30, 2026 3:00 PM"
        set end date of evt to date "January 30, 2026 4:00 PM"
    end tell
end tell
```

#### Delete an Event

```applescript
tell application "Calendar"
    tell calendar "Work"
        set evt to first event whose summary is "Cancelled Meeting"
        delete evt
    end tell
end tell
```

#### Delete All Events Matching Criteria

```applescript
tell application "Calendar"
    tell calendar "Work"
        set oldEvents to (every event whose start date < date "January 1, 2020")
        repeat with evt in oldEvents
            delete evt
        end repeat
    end tell
end tell
```

### Filtering Events

#### Events in Date Range

```applescript
tell application "Calendar"
    set startRange to date "February 1, 2026"
    set endRange to date "February 28, 2026"

    tell calendar "Work"
        set febEvents to (every event whose start date ≥ startRange and start date ≤ endRange)
        repeat with evt in febEvents
            log summary of evt & " - " & (start date of evt as string)
        end repeat
    end tell
end tell
```

#### Today's Events

```applescript
tell application "Calendar"
    set todayStart to current date
    set time of todayStart to 0

    set todayEnd to todayStart + (24 * 60 * 60)

    repeat with c in every calendar
        set todayEvents to (every event of c whose start date ≥ todayStart and start date < todayEnd)
        repeat with evt in todayEvents
            log (name of c) & ": " & summary of evt
        end repeat
    end repeat
end tell
```

#### Events at a Location

```applescript
tell application "Calendar"
    tell calendar "Work"
        set confRoomEvents to (every event whose location contains "Conference")
        repeat with evt in confRoomEvents
            log summary of evt & " @ " & location of evt
        end repeat
    end tell
end tell
```

#### All-Day Events

```applescript
tell application "Calendar"
    tell calendar "Work"
        set allDayEvents to (every event whose allday event is true)
        repeat with evt in allDayEvents
            log summary of evt & " - " & (start date of evt as string)
        end repeat
    end tell
end tell
```

---

## Reminders.app Automation

Reminders.app provides full AppleScript access to task lists, reminders, and their properties. It syncs with iCloud, Exchange, and other accounts, making it accessible across all Apple devices.

### Lists

#### List All Reminder Lists

```applescript
tell application "Reminders"
    set allLists to every list
    repeat with l in allLists
        log name of l
    end repeat
end tell
```

**Sample Output**:
```
Reminders
Shopping
Work Tasks
Personal
```

#### List Properties

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `name` | text | r/w | List name |
| `id` | text | r | Unique identifier |
| `container` | account | r | Parent account |
| `color` | text | r/w | List color |
| `emblem` | text | r/w | List icon name |

#### Get Default List

```applescript
tell application "Reminders"
    set defaultList to default list
    log "Default list: " & name of defaultList
end tell
```

#### Create a New List

```applescript
tell application "Reminders"
    make new list with properties {name:"Project Tasks"}
end tell
```

### Reading Reminders

#### List All Reminders in a List

```applescript
tell application "Reminders"
    set myList to list "Reminders"
    set allReminders to reminders of myList

    repeat with r in allReminders
        set output to name of r
        if completed of r then
            set output to output & " ✓"
        end if
        log output
    end repeat
end tell
```

**Sample Output**:
```
Call dentist
Buy groceries ✓
Review document
Submit report ✓
```

#### Get Reminder Count

```applescript
tell application "Reminders"
    repeat with l in every list
        set remCount to count of reminders of l
        set incompleteCount to count of (reminders of l whose completed is false)
        log (name of l) & ": " & incompleteCount & " incomplete / " & remCount & " total"
    end repeat
end tell
```

### Reminder Properties

All available properties on a reminder object:

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `name` | text | r/w | Reminder title |
| `id` | text | r | Unique identifier (URL format) |
| `body` | text | r/w | Notes/description |
| `completed` | boolean | r/w | Whether task is done |
| `completion date` | date | r/w | When it was completed |
| `due date` | date | r/w | Due date with time |
| `allday due date` | date | r/w | Due date without time |
| `remind me date` | date | r/w | When to show notification |
| `priority` | integer | r/w | 0=none, 1-4=high, 5=medium, 6-9=low |
| `flagged` | boolean | r/w | Whether reminder is flagged |
| `creation date` | date | r | When reminder was created |
| `modification date` | date | r | When reminder was last modified |
| `container` | list | r | Parent list |

#### Get Full Reminder Details

```applescript
tell application "Reminders"
    set r to first reminder of list "Reminders"

    log "name: " & name of r
    log "id: " & id of r
    log "completed: " & completed of r
    log "priority: " & priority of r
    log "flagged: " & flagged of r

    try
        log "due date: " & (due date of r as string)
    on error
        log "due date: (none)"
    end try

    try
        log "body: " & body of r
    on error
        log "body: (none)"
    end try

    log "creation date: " & (creation date of r as string)
    log "modification date: " & (modification date of r as string)
end tell
```

**Sample Output**:
```
name: Submit quarterly report
id: x-apple-reminder://ABC123-DEF456
completed: false
priority: 1
flagged: true
due date: Friday, 31. January 2026 at 17:00:00
body: Include sales figures and projections
creation date: Monday, 27. January 2026 at 09:00:00
modification date: Wednesday, 29. January 2026 at 14:30:00
```

### Creating Reminders

#### Create a Simple Reminder

```applescript
tell application "Reminders"
    tell list "Reminders"
        make new reminder with properties {name:"Call the bank"}
    end tell
end tell
```

#### Create Reminder with Due Date

```applescript
tell application "Reminders"
    tell list "Reminders"
        make new reminder with properties {¬
            name:"Submit report", ¬
            due date:date "January 31, 2026 5:00 PM"¬
        }
    end tell
end tell
```

#### Create Reminder with All Details

```applescript
tell application "Reminders"
    tell list "Work Tasks"
        make new reminder with properties {¬
            name:"Prepare presentation", ¬
            body:"Include Q4 results and Q1 projections. Remember to add charts.", ¬
            due date:date "February 3, 2026 9:00 AM", ¬
            remind me date:date "February 2, 2026 6:00 PM", ¬
            priority:1, ¬
            flagged:true¬
        }
    end tell
end tell
```

#### Create All-Day Reminder

```applescript
tell application "Reminders"
    tell list "Personal"
        make new reminder with properties {¬
            name:"Mom's birthday", ¬
            allday due date:date "March 15, 2026"¬
        }
    end tell
end tell
```

### Modifying and Completing Reminders

#### Mark Reminder as Complete

```applescript
tell application "Reminders"
    set r to first reminder of list "Reminders" whose name is "Call the bank"
    set completed of r to true
end tell
```

#### Update Reminder Properties

```applescript
tell application "Reminders"
    set r to first reminder of list "Reminders" whose name is "Submit report"

    -- Update various properties
    set name of r to "Submit quarterly report"
    set body of r to "Include sales figures"
    set priority of r to 1
    set flagged of r to true
    set due date of r to date "February 1, 2026 5:00 PM"
end tell
```

#### Move Reminder to Another List

```applescript
tell application "Reminders"
    set r to first reminder of list "Reminders" whose name is "Work task"
    set targetList to list "Work Tasks"
    move r to targetList
end tell
```

#### Delete a Reminder

```applescript
tell application "Reminders"
    set r to first reminder of list "Reminders" whose name is "Cancelled task"
    delete r
end tell
```

#### Bulk Complete Old Reminders

```applescript
tell application "Reminders"
    set cutoffDate to (current date) - (30 * 24 * 60 * 60) -- 30 days ago
    repeat with l in every list
        set oldReminders to (reminders of l whose due date < cutoffDate and completed is false)
        repeat with r in oldReminders
            set completed of r to true
        end repeat
    end repeat
end tell
```

### Filtering Reminders

#### Get Incomplete Reminders

```applescript
tell application "Reminders"
    set output to ""
    repeat with l in every list
        set incompleteReminders to (reminders of l whose completed is false)
        if (count of incompleteReminders) > 0 then
            set output to output & "📋 " & name of l & return
            repeat with r in incompleteReminders
                set output to output & "  □ " & name of r
                if flagged of r then
                    set output to output & " 🚩"
                end if
                set output to output & return
            end repeat
        end if
    end repeat
    return output
end tell
```

#### Get Reminders Due Today

```applescript
tell application "Reminders"
    set todayStart to current date
    set time of todayStart to 0
    set todayEnd to todayStart + (24 * 60 * 60)

    set output to "=== DUE TODAY ===" & return
    repeat with l in every list
        set todayReminders to (reminders of l whose due date ≥ todayStart and due date < todayEnd and completed is false)
        repeat with r in todayReminders
            set output to output & "• " & name of r & " (" & name of l & ")" & return
        end repeat
    end repeat
    return output
end tell
```

#### Get Overdue Reminders

```applescript
tell application "Reminders"
    set now to current date

    set output to "=== OVERDUE ===" & return
    repeat with l in every list
        set overdueReminders to (reminders of l whose due date < now and completed is false)
        repeat with r in overdueReminders
            set output to output & "⚠️ " & name of r
            set output to output & " (due: " & (due date of r as string) & ")" & return
        end repeat
    end repeat
    return output
end tell
```

#### Get Flagged Reminders

```applescript
tell application "Reminders"
    set output to "=== FLAGGED ===" & return
    repeat with l in every list
        set flaggedReminders to (reminders of l whose flagged is true and completed is false)
        repeat with r in flaggedReminders
            set output to output & "🚩 " & name of r & return
        end repeat
    end repeat
    return output
end tell
```

#### Get High Priority Reminders

```applescript
tell application "Reminders"
    -- Priority 1-4 is considered high
    set output to "=== HIGH PRIORITY ===" & return
    repeat with l in every list
        set highPriority to (reminders of l whose priority > 0 and priority < 5 and completed is false)
        repeat with r in highPriority
            set output to output & "❗ " & name of r & " (P" & priority of r & ")" & return
        end repeat
    end repeat
    return output
end tell
```

#### Get Recently Completed

```applescript
tell application "Reminders"
    set weekAgo to (current date) - (7 * 24 * 60 * 60)

    set output to "=== COMPLETED THIS WEEK ===" & return
    repeat with l in every list
        set recentlyCompleted to (reminders of l whose completed is true and completion date > weekAgo)
        repeat with r in recentlyCompleted
            set output to output & "✓ " & name of r & return
        end repeat
    end repeat
    return output
end tell
```

---

## Notes.app Automation

Notes.app provides full AppleScript access to notes, folders, and attachments. It syncs with iCloud and other accounts, making notes accessible across all Apple devices.

### Accounts and Folders

#### List All Accounts

```applescript
tell application "Notes"
    repeat with a in accounts
        log "Account: " & name of a
        log "  Default folder: " & name of default folder of a
    end repeat
end tell
```

**Sample Output**:
```
Account: iCloud
  Default folder: Notes
```

#### List All Folders

```applescript
tell application "Notes"
    repeat with f in folders
        log name of f
    end repeat
end tell
```

**Sample Output**:
```
Notes
Work
Personal
Archive
Recently Deleted
```

#### Folder Properties

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `name` | text | r/w | Folder name |
| `id` | text | r | Unique identifier |
| `container` | account | r | Parent account |
| `shared` | boolean | r | Whether folder is shared |

#### Create a New Folder

```applescript
tell application "Notes"
    tell account "iCloud"
        make new folder with properties {name:"Project Notes"}
    end tell
end tell
```

### Reading Notes

#### List All Notes in a Folder

```applescript
tell application "Notes"
    set myFolder to folder "Notes"
    repeat with n in notes of myFolder
        log name of n
    end repeat
end tell
```

#### Get Note Count by Folder

```applescript
tell application "Notes"
    repeat with f in folders
        set noteCount to count of notes of f
        if noteCount > 0 then
            log (name of f) & ": " & noteCount & " notes"
        end if
    end repeat
end tell
```

#### Read Note Content

Notes stores content in two formats:
- `body` — HTML formatted content (read/write)
- `plaintext` — Plain text content (read-only)

```applescript
tell application "Notes"
    set n to first note of folder "Notes"

    log "=== NOTE ==="
    log "Name: " & name of n
    log ""
    log "=== PLAINTEXT ==="
    log plaintext of n
    log ""
    log "=== HTML BODY ==="
    log body of n
end tell
```

**Sample Output**:
```
=== NOTE ===
Name: Meeting Notes

=== PLAINTEXT ===
Meeting Notes

Attendees: John, Sarah, Mike

Action Items:
- Review proposal
- Send follow-up email
- Schedule next meeting

=== HTML BODY ===
<div><h1>Meeting Notes</h1></div>
<div><br></div>
<div><b>Attendees:</b> John, Sarah, Mike</div>
<div><br></div>
<div><b>Action Items:</b></div>
<ul>
<li>Review proposal</li>
<li>Send follow-up email</li>
<li>Schedule next meeting</li>
</ul>
```

### Note Properties

All available properties on a note object:

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `name` | text | r/w | Note title (usually first line of body) |
| `id` | text | r | Unique identifier (URL format) |
| `body` | text | r/w | HTML content with formatting |
| `plaintext` | text | r | Plain text content (no formatting) |
| `creation date` | date | r | When note was created |
| `modification date` | date | r | When note was last modified |
| `container` | folder | r | Parent folder |
| `password protected` | boolean | r | Whether note is locked |
| `shared` | boolean | r | Whether note is shared |
| `attachments` | list | r | List of attachments |

#### Get Full Note Details

```applescript
tell application "Notes"
    set n to first note of folder "Notes"

    log "name: " & name of n
    log "id: " & id of n
    log "creation date: " & (creation date of n as string)
    log "modification date: " & (modification date of n as string)
    log "password protected: " & password protected of n
    log "shared: " & shared of n
    log "attachment count: " & (count of attachments of n)
    log "folder: " & name of container of n
end tell
```

### Creating Notes

#### Create a Simple Note

```applescript
tell application "Notes"
    tell folder "Notes"
        make new note with properties {name:"Quick Note", body:"This is a quick note."}
    end tell
end tell
```

#### Create Note with HTML Formatting

```applescript
tell application "Notes"
    tell folder "Notes"
        make new note with properties {¬
            name:"Formatted Note", ¬
            body:"<h1>Project Plan</h1>
<p>This is the project plan for Q1.</p>
<h2>Goals</h2>
<ul>
<li>Complete phase 1</li>
<li>Review with stakeholders</li>
<li>Begin phase 2</li>
</ul>
<h2>Timeline</h2>
<p><b>Start:</b> February 1<br>
<b>End:</b> March 31</p>"¬
        }
    end tell
end tell
```

#### Create Note in Specific Account/Folder

```applescript
tell application "Notes"
    tell account "iCloud"
        tell folder "Work"
            make new note with properties {¬
                name:"Meeting Notes - Jan 29", ¬
                body:"<div><b>Attendees:</b> Team</div><div><b>Topics:</b> Q1 Planning</div>"¬
            }
        end tell
    end tell
end tell
```

### Modifying and Deleting Notes

#### Update Note Content

```applescript
tell application "Notes"
    set n to first note of folder "Notes" whose name is "Quick Note"

    -- Update the body (replaces entire content)
    set body of n to "<h1>Updated Note</h1><p>This content has been updated via AppleScript.</p>"
end tell
```

#### Append to Note

Since `body` replaces the entire content, to append you must read, modify, and write back:

```applescript
tell application "Notes"
    set n to first note of folder "Notes" whose name is "Quick Note"

    -- Get current body and append
    set currentBody to body of n
    set newContent to currentBody & "<p><b>Update:</b> Added this line on " & (current date as string) & "</p>"
    set body of n to newContent
end tell
```

#### Move Note to Another Folder

```applescript
tell application "Notes"
    set n to first note of folder "Notes" whose name is "Archive This"
    set targetFolder to folder "Archive"
    move n to targetFolder
end tell
```

#### Delete a Note

```applescript
tell application "Notes"
    set n to first note of folder "Notes" whose name is "Delete Me"
    delete n
end tell
```

Note: Deleted notes go to "Recently Deleted" folder first.

### Searching Notes

#### Find Notes by Name

```applescript
tell application "Notes"
    set matchingNotes to every note whose name contains "Meeting"
    repeat with n in matchingNotes
        log name of n & " (in " & name of container of n & ")"
    end repeat
end tell
```

#### Find Notes by Content

```applescript
tell application "Notes"
    set output to ""
    repeat with f in folders
        repeat with n in notes of f
            if plaintext of n contains "project" then
                set output to output & name of n & return
            end if
        end repeat
    end repeat
    return output
end tell
```

#### Find Recently Modified Notes

```applescript
tell application "Notes"
    set weekAgo to (current date) - (7 * 24 * 60 * 60)

    set output to "=== MODIFIED THIS WEEK ===" & return
    repeat with f in folders
        if name of f is not "Recently Deleted" then
            set recentNotes to (notes of f whose modification date > weekAgo)
            repeat with n in recentNotes
                set output to output & "• " & name of n & return
                set output to output & "  Modified: " & (modification date of n as string) & return
            end repeat
        end if
    end repeat
    return output
end tell
```

#### Find Notes in Specific Folder

```applescript
tell application "Notes"
    tell folder "Work"
        set workNotes to every note whose name contains "Report"
        repeat with n in workNotes
            log name of n
        end repeat
    end tell
end tell
```

### Attachments

Notes can contain attachments (images, files, etc.). While you can read attachment metadata, creating attachments via AppleScript is limited.

#### List Attachments in a Note

```applescript
tell application "Notes"
    set n to first note of folder "Notes"
    set attCount to count of attachments of n

    if attCount > 0 then
        log "Attachments in '" & name of n & "':"
        repeat with att in attachments of n
            log "  Name: " & name of att
            log "  ID: " & id of att
            log "  Created: " & (creation date of att as string)
            try
                log "  URL: " & URL of att
            end try
            log ""
        end repeat
    else
        log "No attachments"
    end if
end tell
```

#### Attachment Properties

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `name` | text | r | Attachment filename |
| `id` | text | r | Unique identifier |
| `container` | note | r | Parent note |
| `content identifier` | text | r | Content-ID for HTML reference |
| `creation date` | date | r | When attachment was added |
| `modification date` | date | r | When attachment was modified |
| `URL` | text | r | For URL attachments, the web address |
| `shared` | boolean | r | Whether attachment is shared |

#### Find Notes with Attachments

```applescript
tell application "Notes"
    set output to "=== NOTES WITH ATTACHMENTS ===" & return
    repeat with f in folders
        repeat with n in notes of f
            set attCount to count of attachments of n
            if attCount > 0 then
                set output to output & "• " & name of n & " (" & attCount & " attachments)" & return
            end if
        end repeat
    end repeat
    return output
end tell
```

---

## Safari Automation

Safari provides full AppleScript access to web browsing, enabling navigation, content extraction, and even JavaScript execution. This makes it possible to automate web research, scrape websites, and integrate web content into workflows.

### Windows and Tabs

#### List All Windows and Tabs

```applescript
tell application "Safari"
    set output to ""
    repeat with w in windows
        set output to output & "Window: " & name of w & return
        repeat with t in tabs of w
            set output to output & "  Tab " & index of t & ": " & name of t & return
            set output to output & "    URL: " & URL of t & return
        end repeat
    end repeat
    return output
end tell
```

**Sample Output**:
```
Window: Apple
  Tab 1: Apple
    URL: https://www.apple.com/
  Tab 2: Google
    URL: https://www.google.com/
```

#### Get Current Tab

```applescript
tell application "Safari"
    tell front window
        set currentTab to current tab
        log "Name: " & name of currentTab
        log "URL: " & URL of currentTab
        log "Index: " & index of currentTab
        log "Visible: " & visible of currentTab
    end tell
end tell
```

#### Tab Properties

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `name` | text | r | Page title |
| `URL` | text | r/w | Current URL (set to navigate) |
| `index` | integer | r | Tab position (1-based) |
| `visible` | boolean | r | Whether tab is visible |
| `source` | text | r | Full HTML source of page |
| `text` | text | r | Extracted text content |

### Navigation

#### Open a URL in Current Tab

```applescript
tell application "Safari"
    activate
    set URL of current tab of front window to "https://www.example.com"
end tell
```

#### Create New Tab with URL

```applescript
tell application "Safari"
    tell front window
        set newTab to make new tab with properties {URL:"https://www.apple.com"}
    end tell
end tell
```

#### Create New Window with URL

```applescript
tell application "Safari"
    make new document with properties {URL:"https://www.example.com"}
end tell
```

#### Close a Tab

```applescript
tell application "Safari"
    tell front window
        close tab 2
    end tell
end tell
```

#### Close Current Tab

```applescript
tell application "Safari"
    tell front window
        close current tab
    end tell
end tell
```

### Reading Page Content

Safari provides two ways to read page content:

- `source` — Full HTML source code
- `text` — Extracted plain text (when available)

#### Get HTML Source

```applescript
tell application "Safari"
    tell current tab of front window
        set pageSource to source
        -- pageSource contains full HTML
        return pageSource
    end tell
end tell
```

#### Get Page Text

```applescript
tell application "Safari"
    tell current tab of front window
        set pageText to text
        return pageText
    end tell
end tell
```

Note: The `text` property may not always be available depending on the page content.

#### Wait for Page to Load

Safari doesn't have a built-in "wait for load" command. Use a polling approach:

```applescript
tell application "Safari"
    set URL of current tab of front window to "https://www.example.com"

    -- Wait for page to load (poll until source is available)
    set maxWait to 30 -- seconds
    set waited to 0
    repeat while waited < maxWait
        delay 0.5
        set waited to waited + 0.5
        try
            set pageSource to source of current tab of front window
            if length of pageSource > 1000 then exit repeat
        end try
    end repeat

    return source of current tab of front window
end tell
```

### JavaScript Execution

Safari can execute JavaScript in the context of the current page, enabling powerful DOM manipulation and data extraction.

**Important**: JavaScript execution must be enabled in Safari settings:
1. Safari → Settings → Advanced → "Show Develop menu in menu bar"
2. Develop menu → "Allow JavaScript from Apple Events"

#### Execute JavaScript

```applescript
tell application "Safari"
    tell current tab of front window
        set pageTitle to do JavaScript "document.title"
        return pageTitle
    end tell
end tell
```

#### Get All Links from Page

```applescript
tell application "Safari"
    tell current tab of front window
        set links to do JavaScript "Array.from(document.querySelectorAll('a')).map(a => a.href).join('\\n')"
        return links
    end tell
end tell
```

#### Get Text Content

```applescript
tell application "Safari"
    tell current tab of front window
        set bodyText to do JavaScript "document.body.innerText"
        return bodyText
    end tell
end tell
```

#### Click an Element

```applescript
tell application "Safari"
    tell current tab of front window
        do JavaScript "document.querySelector('button.submit').click()"
    end tell
end tell
```

#### Fill a Form Field

```applescript
tell application "Safari"
    tell current tab of front window
        do JavaScript "document.querySelector('input[name=\"email\"]').value = 'test@example.com'"
    end tell
end tell
```

#### Extract Structured Data

```applescript
tell application "Safari"
    tell current tab of front window
        set jsonData to do JavaScript "
            JSON.stringify(
                Array.from(document.querySelectorAll('article')).map(a => ({
                    title: a.querySelector('h2')?.innerText,
                    summary: a.querySelector('p')?.innerText
                }))
            )
        "
        return jsonData
    end tell
end tell
```

### Reading List and Bookmarks

#### Add to Reading List

```applescript
tell application "Safari"
    add reading list item "https://www.example.com/article" with title "Interesting Article" and preview text "This article discusses important topics."
end tell
```

#### Show Bookmarks

```applescript
tell application "Safari"
    show bookmarks
end tell
```

### Web Scraping Example

A complete example that loads a news website and extracts headlines:

#### Shell Script: Get News Headlines

```bash
#!/bin/bash
# get-news.sh - Extract headlines from a news website via Safari

SITE_URL="https://www.golem.de"

# Navigate to the site
osascript -e "tell application \"Safari\" to set URL of current tab of front window to \"$SITE_URL\""

# Wait for page to load
sleep 3

# Extract headlines from HTML source
osascript -e '
tell application "Safari"
    tell current tab of front window
        return source
    end tell
end tell
' | grep -o '<span class="go-teaser__title">[^<]*</span>' | \
    sed 's/<[^>]*>//g' | \
    head -5
```

**Sample Output**:
```
Bundeswehr ordert Hyperschall-Drohne - vielleicht
Kleine Änderung des Batterieaufbaus, große Wirkung
Teilen Russlands geht das Brot aus
```

#### AppleScript: Complete Web Scraper

```applescript
on scrapeWebsite(siteURL, waitSeconds)
    tell application "Safari"
        activate

        -- Navigate to URL
        set URL of current tab of front window to siteURL

        -- Wait for page to load
        delay waitSeconds

        -- Get page info
        tell current tab of front window
            set pageTitle to name
            set pageURL to URL
            set pageSource to source
        end tell

        return {title:pageTitle, url:pageURL, source:pageSource}
    end tell
end scrapeWebsite

-- Usage
set result to scrapeWebsite("https://www.example.com", 3)
log "Title: " & title of result
log "URL: " & url of result
log "Source length: " & (length of source of result) & " characters"
```

### Limitations and Considerations

1. **JavaScript Requires Permission**: The `do JavaScript` command requires explicit user permission in Safari settings.

2. **Same-Origin Policy**: JavaScript execution is subject to browser security restrictions.

3. **Dynamic Content**: Pages with heavy JavaScript may need longer wait times or multiple polls to fully load.

4. **Rate Limiting**: Rapid automated requests may trigger rate limiting or CAPTCHAs on some websites.

5. **No Headless Mode**: Safari must be running and visible; there's no headless automation mode.

6. **Authentication**: Accessing authenticated pages requires the user to be logged in within Safari.

---

## Comparison with Third-Party Apps

### Email: Mail.app vs Microsoft Outlook (New)

| Feature | Mail.app | New Outlook |
|---------|----------|-------------|
| List accounts | **Yes** | No |
| List mailboxes | **Yes** | Local only |
| Read messages | **Yes** | No |
| Read body content | **Yes** | No |
| Read attachments | **Yes** | No |
| Filter messages | **Yes** | No |
| Mark read/unread | **Yes** | No |
| Flag messages | **Yes** | No |
| Delete messages | **Yes** | No |
| Send email | **Yes** | No |
| Move messages | **Yes** | No |

**Recommendation**: Use Mail.app for email automation. You can add Exchange/Microsoft 365 accounts to Mail.app and get full scripting access.

### Calendar: Calendar.app vs BusyCal

| Feature | Calendar.app | BusyCal |
|---------|--------------|---------|
| List calendars | **Yes** | No |
| Read events | **Yes** | No |
| Event properties | **Yes** (all) | No |
| Create events | **Yes** | URL scheme only |
| Modify events | **Yes** | No |
| Delete events | **Yes** | No |
| Filter by date | **Yes** | No |
| Recurrence | **Yes** | No |

**Recommendation**: Use Calendar.app for calendar automation. BusyCal and Calendar.app share the same CalendarStore, so changes made via AppleScript in Calendar.app automatically appear in BusyCal.

---

## Quick Reference

### Mail.app One-Liners

```bash
# Get unread count
osascript -e 'tell application "Mail" to return count of (messages of inbox whose read status is false)'

# List unread subjects
osascript -e 'tell application "Mail" to return subject of (messages of inbox whose read status is false)'

# Get sender of first inbox message
osascript -e 'tell application "Mail" to return sender of item 1 of (messages of inbox)'

# Mark all inbox as read
osascript -e 'tell application "Mail" to set read status of every message of inbox to true'
```

### Calendar.app One-Liners

```bash
# List all calendar names
osascript -e 'tell application "Calendar" to return name of every calendar'

# Count events in a calendar
osascript -e 'tell application "Calendar" to return count of events of calendar "Work"'

# Get today's events
osascript -e '
tell application "Calendar"
    set d to current date
    set time of d to 0
    set d2 to d + 86400
    set output to ""
    repeat with c in calendars
        set evts to (events of c whose start date ≥ d and start date < d2)
        repeat with e in evts
            set output to output & summary of e & "\n"
        end repeat
    end repeat
    return output
end tell
'

# Create a quick event
osascript -e '
tell application "Calendar"
    tell calendar "Work"
        make new event with properties {summary:"Quick Meeting", start date:((current date) + 3600), end date:((current date) + 7200)}
    end tell
end tell
'
```

### Reminders.app One-Liners

```bash
# List all reminder lists
osascript -e 'tell application "Reminders" to return name of every list'

# Count incomplete reminders
osascript -e 'tell application "Reminders" to return count of (reminders whose completed is false)'

# List incomplete reminders
osascript -e 'tell application "Reminders" to return name of (reminders whose completed is false)'

# Create a quick reminder
osascript -e 'tell application "Reminders" to tell list "Reminders" to make new reminder with properties {name:"Quick task"}'

# Create reminder with due date (tomorrow)
osascript -e '
tell application "Reminders"
    tell list "Reminders"
        make new reminder with properties {name:"Follow up", due date:((current date) + 86400)}
    end tell
end tell
'

# Mark a reminder complete
osascript -e 'tell application "Reminders" to set completed of (first reminder whose name is "Task name") to true'

# Get overdue count
osascript -e '
tell application "Reminders"
    set now to current date
    return count of (reminders whose due date < now and completed is false)
end tell
'
```

### Notes.app One-Liners

```bash
# List all folder names
osascript -e 'tell application "Notes" to return name of every folder'

# Count all notes
osascript -e 'tell application "Notes" to return count of every note'

# List note names in a folder
osascript -e 'tell application "Notes" to return name of every note of folder "Notes"'

# Create a quick note
osascript -e 'tell application "Notes" to tell folder "Notes" to make new note with properties {name:"Quick Note", body:"Content here"}'

# Get plaintext of first note
osascript -e 'tell application "Notes" to return plaintext of first note of folder "Notes"'

# Find notes containing text
osascript -e '
tell application "Notes"
    set matches to ""
    repeat with n in every note
        if plaintext of n contains "search term" then
            set matches to matches & name of n & "\n"
        end if
    end repeat
    return matches
end tell
'

# Get recently modified notes (last 7 days)
osascript -e '
tell application "Notes"
    set weekAgo to (current date) - 604800
    set output to ""
    repeat with n in every note
        if modification date of n > weekAgo then
            set output to output & name of n & "\n"
        end if
    end repeat
    return output
end tell
'
```

### Safari One-Liners

```bash
# Get current tab URL
osascript -e 'tell application "Safari" to return URL of current tab of front window'

# Get current page title
osascript -e 'tell application "Safari" to return name of current tab of front window'

# Navigate to a URL
osascript -e 'tell application "Safari" to set URL of current tab of front window to "https://www.example.com"'

# Open URL in new tab
osascript -e 'tell application "Safari" to tell front window to make new tab with properties {URL:"https://www.apple.com"}'

# Get page source (first 500 chars)
osascript -e 'tell application "Safari" to return text 1 thru 500 of source of current tab of front window'

# List all open tabs
osascript -e '
tell application "Safari"
    set output to ""
    repeat with t in tabs of front window
        set output to output & name of t & "\n"
    end repeat
    return output
end tell
'

# Add to Reading List
osascript -e 'tell application "Safari" to add reading list item "https://example.com/article" with title "Read Later"'

# Close current tab
osascript -e 'tell application "Safari" to close current tab of front window'

# Execute JavaScript (requires permission)
osascript -e 'tell application "Safari" to tell current tab of front window to do JavaScript "document.title"'

# Get all links from page (requires JS permission)
osascript -e 'tell application "Safari" to tell current tab of front window to do JavaScript "Array.from(document.links).map(a => a.href).slice(0,10).join(\"\\n\")"'
```

### Shell Script: Web Scraper

```bash
#!/bin/bash
# web-scraper.sh - Load a URL and extract content via Safari

URL="${1:-https://www.example.com}"
WAIT="${2:-3}"

echo "Loading: $URL"

# Navigate
osascript -e "tell application \"Safari\"
    activate
    set URL of current tab of front window to \"$URL\"
end tell"

# Wait for load
sleep "$WAIT"

# Get info
echo ""
echo "=== PAGE INFO ==="
osascript -e '
tell application "Safari"
    tell current tab of front window
        set output to "Title: " & name & "\n"
        set output to output & "URL: " & URL & "\n"
        set output to output & "Source length: " & (length of source) & " chars"
        return output
    end tell
end tell
'
```

### Shell Script: Daily Email Summary

```bash
#!/bin/bash
# daily-email-summary.sh - Get a summary of today's emails

osascript <<'EOF'
tell application "Mail"
    set output to "=== EMAIL SUMMARY ===" & return & return

    -- Unread count
    set unreadCount to count of (messages of inbox whose read status is false)
    set output to output & "Unread messages: " & unreadCount & return & return

    -- Recent messages (last 24 hours)
    set yesterday to (current date) - (24 * 60 * 60)
    set recentMsgs to (messages of inbox whose date received > yesterday)
    set output to output & "Messages in last 24h: " & (count of recentMsgs) & return & return

    -- List unread
    if unreadCount > 0 then
        set output to output & "=== UNREAD ===" & return
        set unreadMsgs to (messages of inbox whose read status is false)
        repeat with msg in unreadMsgs
            set output to output & "• " & subject of msg & return
            set output to output & "  From: " & sender of msg & return
        end repeat
    end if

    return output
end tell
EOF
```

### Shell Script: Weekly Calendar Agenda

```bash
#!/bin/bash
# weekly-agenda.sh - Get events for the next 7 days

osascript <<'EOF'
tell application "Calendar"
    set startDate to current date
    set time of startDate to 0
    set endDate to startDate + (7 * 24 * 60 * 60)

    set output to "=== NEXT 7 DAYS ===" & return & return

    repeat with c in calendars
        set weekEvents to (events of c whose start date ≥ startDate and start date < endDate)
        if (count of weekEvents) > 0 then
            set output to output & "📅 " & name of c & return
            repeat with evt in weekEvents
                set evtDate to start date of evt
                set dateStr to (month of evtDate as integer) & "/" & (day of evtDate)
                set timeStr to ""
                if not allday event of evt then
                    set h to hours of evtDate
                    set m to minutes of evtDate
                    if m < 10 then set m to "0" & m
                    set timeStr to " " & h & ":" & m
                end if
                set output to output & "  " & dateStr & timeStr & " - " & summary of evt & return
            end repeat
            set output to output & return
        end if
    end repeat

    return output
end tell
EOF
```

### Shell Script: Notes Search and Summary

```bash
#!/bin/bash
# notes-summary.sh - Search and summarize notes

osascript <<'EOF'
tell application "Notes"
    set output to "=== NOTES SUMMARY ===" & return & return

    -- Count by folder
    set output to output & "📁 BY FOLDER" & return
    repeat with f in folders
        set noteCount to count of notes of f
        if noteCount > 0 and name of f is not "Recently Deleted" then
            set output to output & "  " & name of f & ": " & noteCount & " notes" & return
        end if
    end repeat
    set output to output & return

    -- Recently modified
    set weekAgo to (current date) - (7 * 24 * 60 * 60)
    set output to output & "📝 MODIFIED THIS WEEK" & return
    repeat with f in folders
        if name of f is not "Recently Deleted" then
            repeat with n in notes of f
                if modification date of n > weekAgo then
                    set output to output & "  • " & name of n & return
                end if
            end repeat
        end if
    end repeat
    set output to output & return

    -- Notes with attachments
    set output to output & "📎 WITH ATTACHMENTS" & return
    repeat with f in folders
        if name of f is not "Recently Deleted" then
            repeat with n in notes of f
                if (count of attachments of n) > 0 then
                    set output to output & "  • " & name of n & " (" & (count of attachments of n) & ")" & return
                end if
            end repeat
        end if
    end repeat

    return output
end tell
EOF
```

### Shell Script: Task Overview

```bash
#!/bin/bash
# task-overview.sh - Get overview of all reminders

osascript <<'EOF'
tell application "Reminders"
    set now to current date
    set output to "=== TASK OVERVIEW ===" & return & return

    -- Overdue
    set overdueList to (reminders whose due date < now and completed is false)
    set overdueCount to count of overdueList
    if overdueCount > 0 then
        set output to output & "⚠️ OVERDUE (" & overdueCount & ")" & return
        repeat with r in overdueList
            set output to output & "  • " & name of r & return
        end repeat
        set output to output & return
    end if

    -- Due Today
    set todayStart to now
    set time of todayStart to 0
    set todayEnd to todayStart + 86400
    set todayList to (reminders whose due date ≥ todayStart and due date < todayEnd and completed is false)
    if (count of todayList) > 0 then
        set output to output & "📅 DUE TODAY" & return
        repeat with r in todayList
            set output to output & "  • " & name of r & return
        end repeat
        set output to output & return
    end if

    -- Flagged
    set flaggedList to (reminders whose flagged is true and completed is false)
    if (count of flaggedList) > 0 then
        set output to output & "🚩 FLAGGED" & return
        repeat with r in flaggedList
            set output to output & "  • " & name of r & return
        end repeat
        set output to output & return
    end if

    -- Summary by list
    set output to output & "📋 BY LIST" & return
    repeat with l in lists
        set incompleteCount to count of (reminders of l whose completed is false)
        if incompleteCount > 0 then
            set output to output & "  " & name of l & ": " & incompleteCount & " tasks" & return
        end if
    end repeat

    return output
end tell
EOF
```

---

## Conclusion

Apple's Mail.app, Calendar.app, Reminders.app, Notes.app, and Safari provide comprehensive AppleScript automation that serves as a reliable foundation for productivity and web automation on macOS. Key benefits:

1. **Full Data Access**: Read and write all aspects of emails, events, tasks, notes, and web pages
2. **Account Agnostic**: Works with Exchange, Google, iCloud, and other account types
3. **Sync Compatible**: Changes sync to third-party apps (BusyCal) and services, and across all Apple devices
4. **Native Performance**: No external dependencies or API rate limits
5. **Privacy**: All processing happens locally on your Mac
6. **Complete Productivity Suite**: Email, calendar, tasks, notes, and web browsing together enable comprehensive workflow automation
7. **Web Integration**: Safari enables scraping websites, automating web research, and integrating online content

For automation workflows, these native apps are the recommended approach even if you prefer third-party apps for daily use. The combination of all five apps enables powerful cross-functional automation such as:

- Creating reminders from email action items
- Adding calendar events with linked task checklists
- Generating daily briefings combining emails, meetings, and due tasks
- Extracting meeting notes to Notes.app automatically
- Building a searchable knowledge base from email threads
- Automated follow-up workflows spanning all domains
- Creating project documentation that links emails, meetings, tasks, and notes
- Scraping websites for research and saving results to Notes
- Monitoring web pages for changes and sending email alerts
- Extracting information from URLs mentioned in emails
- Automating web-based workflows (form filling, data extraction)
