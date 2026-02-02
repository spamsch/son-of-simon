#!/bin/bash
# ==============================================================================
# open-url.sh - Open a URL in Safari
# ==============================================================================
# Description:
#   Opens a URL in Safari. Can open in current tab, new tab, or new window.
#   Optionally waits for page to load and returns page info.
#
# Usage:
#   ./open-url.sh "https://example.com"
#   ./open-url.sh "https://example.com" --new-tab
#   ./open-url.sh "https://example.com" --new-window
#   ./open-url.sh "https://example.com" --wait --get-title
#
# Options:
#   --new-tab       Open in a new tab (default)
#   --new-window    Open in a new window
#   --current       Open in current tab
#   --wait          Wait for page to load (default: 3 seconds)
#   --wait-time <s> Custom wait time in seconds
#   --get-title     Return the page title after loading
#   --background    Don't bring Safari to front
#
# Example:
#   ./open-url.sh "https://www.apple.com" --new-tab
#   ./open-url.sh "https://news.ycombinator.com" --wait --get-title
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
URL=""
MODE="new-tab"
WAIT=false
WAIT_TIME=3
GET_TITLE=false
BACKGROUND=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --new-tab)
            MODE="new-tab"
            shift
            ;;
        --new-window)
            MODE="new-window"
            shift
            ;;
        --current)
            MODE="current"
            shift
            ;;
        --wait)
            WAIT=true
            shift
            ;;
        --wait-time)
            WAIT=true
            WAIT_TIME="$2"
            shift 2
            ;;
        --get-title)
            GET_TITLE=true
            WAIT=true
            shift
            ;;
        --background)
            BACKGROUND=true
            shift
            ;;
        -h|--help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        -*)
            error_exit "Unknown option: $1"
            ;;
        *)
            URL="$1"
            shift
            ;;
    esac
done

# Validate
[[ -z "$URL" ]] && error_exit "URL is required"

# Add https if no protocol specified
if [[ ! "$URL" =~ ^https?:// ]]; then
    URL="https://$URL"
fi

osascript <<EOF
tell application "Safari"
    if not $BACKGROUND then
        activate
    end if

    if "$MODE" is "new-window" then
        make new document with properties {URL:"$URL"}
    else if "$MODE" is "new-tab" then
        if (count of windows) is 0 then
            make new document with properties {URL:"$URL"}
        else
            tell front window
                set newTab to make new tab with properties {URL:"$URL"}
                set current tab to newTab
            end tell
        end if
    else
        -- Current tab
        if (count of windows) is 0 then
            make new document with properties {URL:"$URL"}
        else
            set URL of current tab of front window to "$URL"
        end if
    end if

    if $WAIT then
        delay $WAIT_TIME
    end if

    if $GET_TITLE then
        if (count of windows) > 0 then
            return name of current tab of front window
        end if
    else
        return "Opened: $URL"
    end if
end tell
EOF
