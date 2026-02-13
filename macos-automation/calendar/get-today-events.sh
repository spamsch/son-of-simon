#!/bin/bash
# ==============================================================================
# get-today-events.sh - Get all events scheduled for today
# ==============================================================================
# Description:
#   Retrieves all calendar events for today across all calendars or a specific
#   calendar. Shows event time, title, location, and calendar name.
#
# Usage:
#   ./get-today-events.sh
#   ./get-today-events.sh --calendar "Work"
#   ./get-today-events.sh --account "Google" --calendar "Calendar"
#
# Options:
#   --calendar <name>   Only show events from the specified calendar
#   --account <name>    Only show events from calendars in matching account
#
# Output:
#   A chronologically sorted list of today's events
#
# Example:
#   ./get-today-events.sh
#   ./get-today-events.sh --calendar "Personal"
#   ./get-today-events.sh --account "iCloud"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
CALENDAR_NAME=""
ACCOUNT_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --calendar)
            CALENDAR_NAME="$2"
            shift 2
            ;;
        --account)
            ACCOUNT_NAME="$2"
            shift 2
            ;;
        -h|--help)
            head -30 "$0" | tail -25
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
    let startOfDay = calendar.startOfDay(for: now)
    let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay)!

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

    let predicate = store.predicateForEvents(withStart: startOfDay, end: endOfDay, calendars: calendars)
    let events = store.events(matching: predicate).sorted { $0.startDate < $1.startDate }

    if events.isEmpty {
        if calendarFilter.isEmpty && accountFilter.isEmpty {
            print("No events scheduled for today.")
        } else {
            print("No events scheduled for today with the specified filters.")
        }
        return
    }

    print("=== TODAYS EVENTS ===\n")

    // Group events by calendar (include account for disambiguation)
    var eventsByCalendar: [(key: String, events: [EKEvent])] = []
    var calendarGroups: [String: [EKEvent]] = [:]
    var calendarOrder: [String] = []
    for event in events {
        let calKey = "\(event.calendar.title) (\(event.calendar.source.title))"
        if calendarGroups[calKey] == nil {
            calendarGroups[calKey] = []
            calendarOrder.append(calKey)
        }
        calendarGroups[calKey]!.append(event)
    }

    let timeFormatter = DateFormatter()
    timeFormatter.dateFormat = "h:mm a"

    for calKey in calendarOrder {
        guard let calEvents = calendarGroups[calKey] else { continue }
        print("\u{1F4C5} \(calKey)")
        for event in calEvents {
            let timeStr: String
            if event.isAllDay {
                timeStr = "All Day"
            } else {
                timeStr = timeFormatter.string(from: event.startDate)
            }

            print("  \(timeStr) - \(event.title ?? "No title")")
            if let location = event.location, !location.isEmpty {
                print("           Location: \(location)")
            }
        }
        print("")
    }
}

semaphore.wait()
' 2>&1
