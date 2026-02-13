#!/bin/bash
# ==============================================================================
# create-event.sh - Create a new calendar event
# ==============================================================================
# Description:
#   Creates a new event in the specified calendar with title, date/time,
#   location, and optional description. Supports account-based calendar
#   disambiguation when multiple calendars share the same name.
#
# Usage:
#   ./create-event.sh --calendar "Work" --title "Meeting" --start "2026-01-30 14:00" --end "2026-01-30 15:00"
#   ./create-event.sh --account "Google" --calendar "Calendar" --title "Sync" --start "2026-02-03 10:00"
#   ./create-event.sh --calendar "Work" --title "Holiday" --date "2026-02-14" --all-day
#   ./create-event.sh --calendar "Work" --title "Standup" --start "2026-02-03 09:00" --duration 15
#
# Options:
#   --calendar <name>    Calendar name (required)
#   --account <name>     Account name to disambiguate calendars (optional)
#   --title <text>       Event title (required)
#   --start <datetime>   Start date/time as "YYYY-MM-DD HH:MM" (required unless --all-day)
#   --end <datetime>     End date/time as "YYYY-MM-DD HH:MM"
#   --duration <mins>    Duration in minutes (alternative to --end)
#   --date <date>        Date for all-day events as "YYYY-MM-DD"
#   --all-day            Create an all-day event
#   --location <text>    Event location (optional)
#   --notes <text>       Event description/notes (optional)
#
# Example:
#   ./create-event.sh --account "Google" --calendar "Calendar" --title "Team Meeting" \
#       --start "2026-01-30 14:00" --end "2026-01-30 15:00" \
#       --location "Conference Room A"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
CALENDAR=""
ACCOUNT=""
TITLE=""
START=""
END=""
DURATION=""
DATE=""
ALL_DAY=false
LOCATION=""
NOTES=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --calendar)
            CALENDAR="$2"
            shift 2
            ;;
        --account)
            ACCOUNT="$2"
            shift 2
            ;;
        --title)
            TITLE="$2"
            shift 2
            ;;
        --start)
            START="$2"
            shift 2
            ;;
        --end)
            END="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --date)
            DATE="$2"
            shift 2
            ;;
        --all-day)
            ALL_DAY=true
            shift
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --notes)
            NOTES="$2"
            shift 2
            ;;
        -h|--help)
            head -39 "$0" | tail -34
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Validate required fields
[[ -z "$CALENDAR" ]] && error_exit "--calendar is required"
[[ -z "$TITLE" ]] && error_exit "--title is required"

if [[ "$ALL_DAY" == "true" ]]; then
    [[ -z "$DATE" ]] && error_exit "--date is required for all-day events"
    # Validate date format
    date -j -f "%Y-%m-%d" "$DATE" "+%Y-%m-%d" >/dev/null 2>&1 || error_exit "Invalid date format. Use YYYY-MM-DD"
else
    [[ -z "$START" ]] && error_exit "--start is required for timed events"
    # Validate start format
    date -j -f "%Y-%m-%d %H:%M" "$START" "+%s" >/dev/null 2>&1 || error_exit "Invalid start format. Use 'YYYY-MM-DD HH:MM'"

    # Calculate end time if not provided
    if [[ -z "$END" ]]; then
        START_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "$START" "+%s")
        if [[ -n "$DURATION" ]]; then
            END_EPOCH=$((START_EPOCH + DURATION * 60))
        else
            # Default to 1 hour duration
            END_EPOCH=$((START_EPOCH + 3600))
        fi
        END=$(date -j -f "%s" "$END_EPOCH" "+%Y-%m-%d %H:%M")
    else
        date -j -f "%Y-%m-%d %H:%M" "$END" "+%s" >/dev/null 2>&1 || error_exit "Invalid end format. Use 'YYYY-MM-DD HH:MM'"
    fi
fi

# Escape double quotes and backslashes for Swift string literals
escape_for_swift() {
    local str="$1"
    str="${str//\\/\\\\}"
    str="${str//\"/\\\"}"
    echo "$str"
}

TITLE_ESC=$(escape_for_swift "$TITLE")
LOCATION_ESC=$(escape_for_swift "$LOCATION")
NOTES_ESC=$(escape_for_swift "$NOTES")
CALENDAR_ESC=$(escape_for_swift "$CALENDAR")
ACCOUNT_ESC=$(escape_for_swift "$ACCOUNT")

# Use Swift with EventKit for account-aware calendar lookup
swift -e '
import EventKit
import Foundation

let calendarName = "'"$CALENDAR_ESC"'"
let accountFilter = "'"$ACCOUNT_ESC"'"
let eventTitle = "'"$TITLE_ESC"'"
let locationStr = "'"$LOCATION_ESC"'"
let notesStr = "'"$NOTES_ESC"'"
let isAllDayEvent = '"$( [[ "$ALL_DAY" == "true" ]] && echo "true" || echo "false" )"'
let dateStr = "'"$DATE"'"
let startStr = "'"$START"'"
let endStr = "'"$END"'"
let store = EKEventStore()
let semaphore = DispatchSemaphore(value: 0)

store.requestFullAccessToEvents { granted, error in
    defer { semaphore.signal() }

    guard granted else {
        print("Error: Calendar access denied. Please grant access in System Settings > Privacy & Security > Calendars.")
        return
    }

    // Find the target calendar
    let allCalendars = store.calendars(for: .event)
    let matching: [EKCalendar]

    if !accountFilter.isEmpty {
        matching = allCalendars.filter {
            $0.title == calendarName &&
            $0.source.title.localizedCaseInsensitiveContains(accountFilter)
        }
    } else {
        matching = allCalendars.filter { $0.title == calendarName }
    }

    guard let targetCalendar = matching.first else {
        if !accountFilter.isEmpty {
            print("Error: Calendar \"\(calendarName)\" not found in account \"\(accountFilter)\".")
        } else {
            print("Error: Calendar \"\(calendarName)\" not found.")
        }
        return
    }

    guard targetCalendar.allowsContentModifications else {
        print("Error: Calendar \"\(calendarName)\" is read-only.")
        return
    }

    // Create the event
    let event = EKEvent(eventStore: store)
    event.calendar = targetCalendar
    event.title = eventTitle

    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")

    if isAllDayEvent {
        formatter.dateFormat = "yyyy-MM-dd"
        guard let date = formatter.date(from: dateStr) else {
            print("Error: Invalid date format.")
            return
        }
        event.startDate = date
        event.endDate = Calendar.current.date(byAdding: .day, value: 1, to: date)!
        event.isAllDay = true
    } else {
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        guard let start = formatter.date(from: startStr) else {
            print("Error: Invalid start datetime format.")
            return
        }
        guard let end = formatter.date(from: endStr) else {
            print("Error: Invalid end datetime format.")
            return
        }
        event.startDate = start
        event.endDate = end
    }

    if !locationStr.isEmpty {
        event.location = locationStr
    }
    if !notesStr.isEmpty {
        event.notes = notesStr
    }

    do {
        try store.save(event, span: .thisEvent)
        let calInfo = !accountFilter.isEmpty ? "\(calendarName) (\(targetCalendar.source.title))" : calendarName
        if isAllDayEvent {
            print("Created all-day event: \(eventTitle) on \(dateStr) in \(calInfo)")
        } else {
            print("Created event: \(eventTitle) on \(startStr) in \(calInfo)")
        }
    } catch {
        print("Error creating event: \(error.localizedDescription)")
    }
}

semaphore.wait()
' 2>&1
