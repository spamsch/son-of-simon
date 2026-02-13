#!/bin/bash
# ==============================================================================
# get-week-events.sh - Get all events for the upcoming week
# ==============================================================================
# Description:
#   Retrieves all calendar events for the next 7 days (or custom range),
#   organized by day. Shows time, title, location, and calendar name.
#
# Usage:
#   ./get-week-events.sh
#   ./get-week-events.sh --days 14
#   ./get-week-events.sh --calendar "Work"
#   ./get-week-events.sh --account "Google" --calendar "Calendar"
#
# Options:
#   --days <n>          Number of days to look ahead (default: 7)
#   --calendar <name>   Only show events from the specified calendar
#   --account <name>    Only show events from calendars in matching account
#
# Example:
#   ./get-week-events.sh
#   ./get-week-events.sh --days 30 --calendar "Personal"
#   ./get-week-events.sh --account "iCloud"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
DAYS=7
CALENDAR_NAME=""
ACCOUNT_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --calendar)
            CALENDAR_NAME="$2"
            shift 2
            ;;
        --account)
            ACCOUNT_NAME="$2"
            shift 2
            ;;
        -h|--help)
            head -28 "$0" | tail -23
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Use Swift with EventKit for efficient date-based queries
swift -e '
import EventKit
import Foundation

let daysAhead = '"$DAYS"'
let calendarFilter = "'"$CALENDAR_NAME"'"
let accountFilter = "'"$ACCOUNT_NAME"'"
let store = EKEventStore()
let semaphore = DispatchSemaphore(value: 0)

store.requestFullAccessToEvents { granted, error in
    defer { semaphore.signal() }

    guard granted else {
        print("Error: Calendar access denied. Please grant access in System Settings > Privacy & Security > Calendars.")
        return
    }

    let calendar = Calendar.current
    let now = Date()
    let startDate = calendar.startOfDay(for: now)
    let endDate = calendar.date(byAdding: .day, value: daysAhead, to: startDate)!

    // Filter calendars by name and/or account
    var calendars: [EKCalendar]? = nil
    if !calendarFilter.isEmpty || !accountFilter.isEmpty {
        let allCalendars = store.calendars(for: .event)
        var matchingCalendars = allCalendars
        if !calendarFilter.isEmpty {
            matchingCalendars = matchingCalendars.filter { $0.title == calendarFilter }
        }
        if !accountFilter.isEmpty {
            matchingCalendars = matchingCalendars.filter {
                $0.source.title.localizedCaseInsensitiveContains(accountFilter)
            }
        }
        if matchingCalendars.isEmpty {
            let filterDesc = [
                calendarFilter.isEmpty ? nil : "calendar \"\(calendarFilter)\"",
                accountFilter.isEmpty ? nil : "account \"\(accountFilter)\""
            ].compactMap { $0 }.joined(separator: " in ")
            print("Error: No calendars found matching \(filterDesc).")
            return
        }
        calendars = matchingCalendars
    }

    let predicate = store.predicateForEvents(withStart: startDate, end: endDate, calendars: calendars)
    let events = store.events(matching: predicate).sorted { $0.startDate < $1.startDate }

    if events.isEmpty {
        print("No events scheduled for the next \(daysAhead) days.")
        return
    }

    print("=== NEXT \(daysAhead) DAYS ===\n")

    // Group events by day, then by calendar (include account for disambiguation)
    let dayFormatter = DateFormatter()
    dayFormatter.dateFormat = "EEEE, MMMM d"

    let timeFormatter = DateFormatter()
    timeFormatter.dateFormat = "h:mm a"

    var eventsByDay: [String: [EKEvent]] = [:]
    var dayOrder: [String] = []

    for event in events {
        let dayKey = dayFormatter.string(from: event.startDate)
        if eventsByDay[dayKey] == nil {
            eventsByDay[dayKey] = []
            dayOrder.append(dayKey)
        }
        eventsByDay[dayKey]!.append(event)
    }

    for dayKey in dayOrder {
        print("\u{1F4C6} \(dayKey)")

        guard let dayEvents = eventsByDay[dayKey] else { continue }

        // Group by calendar (with account) within each day
        var eventsByCalendar: [String: [EKEvent]] = [:]
        var calOrder: [String] = []
        for event in dayEvents {
            let calKey = "\(event.calendar.title) (\(event.calendar.source.title))"
            if eventsByCalendar[calKey] == nil {
                eventsByCalendar[calKey] = []
                calOrder.append(calKey)
            }
            eventsByCalendar[calKey]!.append(event)
        }

        for calKey in calOrder {
            guard let calEvents = eventsByCalendar[calKey] else { continue }
            print("  \u{1F4C5} \(calKey)")
            for event in calEvents {
                let timeStr: String
                if event.isAllDay {
                    timeStr = "All Day"
                } else {
                    timeStr = timeFormatter.string(from: event.startDate)
                }

                print("    \(timeStr) - \(event.title ?? "No title")")
                if let location = event.location, !location.isEmpty {
                    print("             Location: \(location)")
                }
            }
        }
        print("")
    }
}

semaphore.wait()
' 2>&1
