#!/bin/bash
# ==============================================================================
# list-calendars.sh - List all available calendars grouped by account
# ==============================================================================
# Description:
#   Lists all calendars available in Calendar.app, grouped by account (source),
#   showing name, writable status, and optional event counts.
#
# Usage:
#   ./list-calendars.sh
#   ./list-calendars.sh --with-counts
#   ./list-calendars.sh --account "Google"
#
# Options:
#   --with-counts       Include event counts for each calendar
#   --account <name>    Only show calendars from matching account
#
# Example:
#   ./list-calendars.sh
#   ./list-calendars.sh --with-counts --account "iCloud"
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

WITH_COUNTS=false
ACCOUNT_FILTER=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-counts)
            WITH_COUNTS=true
            shift
            ;;
        --account)
            ACCOUNT_FILTER="$2"
            shift 2
            ;;
        -h|--help)
            head -26 "$0" | tail -21
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Use Swift with EventKit to get account (source) information
swift -e '
import EventKit
import Foundation

let withCounts = '"$( [[ "$WITH_COUNTS" == "true" ]] && echo "true" || echo "false" )"'
let accountFilter = "'"$ACCOUNT_FILTER"'"
let store = EKEventStore()
let semaphore = DispatchSemaphore(value: 0)

store.requestFullAccessToEvents { granted, error in
    defer { semaphore.signal() }

    guard granted else {
        print("Error: Calendar access denied. Please grant access in System Settings > Privacy & Security > Calendars.")
        return
    }

    var calendars = store.calendars(for: .event)

    // Filter by account if specified
    if !accountFilter.isEmpty {
        calendars = calendars.filter {
            $0.source.title.localizedCaseInsensitiveContains(accountFilter)
        }
        if calendars.isEmpty {
            print("Error: No calendars found for account \"\(accountFilter)\".")
            return
        }
    }

    // Sort by account name, then calendar name
    calendars.sort {
        if $0.source.title != $1.source.title {
            return $0.source.title.localizedCompare($1.source.title) == .orderedAscending
        }
        return $0.title.localizedCompare($1.title) == .orderedAscending
    }

    print("=== CALENDARS ===\n")

    var currentSource = ""
    for cal in calendars {
        if cal.source.title != currentSource {
            currentSource = cal.source.title
            print("\u{1F4C1} Account: \(currentSource)")
        }

        let writable = cal.allowsContentModifications

        if withCounts {
            // Count events in past year to next year
            let now = Date()
            let cal2 = Calendar.current
            let start = cal2.date(byAdding: .year, value: -1, to: now)!
            let end = cal2.date(byAdding: .year, value: 1, to: now)!
            let predicate = store.predicateForEvents(withStart: start, end: end, calendars: [cal])
            let count = store.events(matching: predicate).count

            print("  \u{1F4C5} \(cal.title)")
            print("     Events: \(count)")
            if writable {
                print("     Writable: Yes")
            } else {
                print("     Writable: No (read-only)")
            }
        } else {
            if writable {
                print("  \u{1F4C5} \(cal.title)")
            } else {
                print("  \u{1F4C5} \(cal.title) (read-only)")
            }
        }
    }
}

semaphore.wait()
' 2>&1
