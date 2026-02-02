#!/bin/bash
# ==============================================================================
# list-tabs.sh - List all open Safari tabs
# ==============================================================================
# Description:
#   Lists all open tabs across all Safari windows, showing window number,
#   tab index, title, and URL.
#
# Usage:
#   ./list-tabs.sh
#   ./list-tabs.sh --urls-only
#   ./list-tabs.sh --window 1
#
# Options:
#   --urls-only     Only output URLs (useful for piping)
#   --titles-only   Only output titles
#   --window <n>    Only show tabs from window n
#   --json          Output in JSON format
#
# Example:
#   ./list-tabs.sh
#   ./list-tabs.sh --urls-only | grep github
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
URLS_ONLY=false
TITLES_ONLY=false
WINDOW=""
JSON_OUTPUT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --urls-only)
            URLS_ONLY=true
            shift
            ;;
        --titles-only)
            TITLES_ONLY=true
            shift
            ;;
        --window)
            WINDOW="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
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

if [[ "$JSON_OUTPUT" == "true" ]]; then
    osascript <<EOF
tell application "Safari"
    if (count of windows) is 0 then
        return "[]"
    end if

    set jsonOutput to "["
    set first to true

    repeat with w from 1 to count of windows
        if "$WINDOW" is "" or "$WINDOW" is (w as string) then
            repeat with t in tabs of window w
                if not first then
                    set jsonOutput to jsonOutput & ","
                end if
                set first to false

                set tabTitle to name of t
                set tabURL to URL of t
                set tabIndex to index of t

                -- Escape quotes in title
                set AppleScript's text item delimiters to "\""
                set titleParts to text items of tabTitle
                set AppleScript's text item delimiters to "\\\""
                set tabTitle to titleParts as text
                set AppleScript's text item delimiters to ""

                set jsonOutput to jsonOutput & return & "  {"
                set jsonOutput to jsonOutput & "\"window\": " & w & ", "
                set jsonOutput to jsonOutput & "\"tab\": " & tabIndex & ", "
                set jsonOutput to jsonOutput & "\"title\": \"" & tabTitle & "\", "
                set jsonOutput to jsonOutput & "\"url\": \"" & tabURL & "\"}"
            end repeat
        end if
    end repeat

    set jsonOutput to jsonOutput & return & "]"
    return jsonOutput
end tell
EOF
elif [[ "$URLS_ONLY" == "true" ]]; then
    osascript <<EOF
tell application "Safari"
    if (count of windows) is 0 then
        return ""
    end if

    set output to ""
    repeat with w from 1 to count of windows
        if "$WINDOW" is "" or "$WINDOW" is (w as string) then
            repeat with t in tabs of window w
                set output to output & URL of t & return
            end repeat
        end if
    end repeat
    return output
end tell
EOF
elif [[ "$TITLES_ONLY" == "true" ]]; then
    osascript <<EOF
tell application "Safari"
    if (count of windows) is 0 then
        return ""
    end if

    set output to ""
    repeat with w from 1 to count of windows
        if "$WINDOW" is "" or "$WINDOW" is (w as string) then
            repeat with t in tabs of window w
                set output to output & name of t & return
            end repeat
        end if
    end repeat
    return output
end tell
EOF
else
    osascript <<EOF
tell application "Safari"
    if (count of windows) is 0 then
        return "No Safari windows open."
    end if

    set output to "=== SAFARI TABS ===" & return & return
    set totalTabs to 0

    repeat with w from 1 to count of windows
        if "$WINDOW" is "" or "$WINDOW" is (w as string) then
            set output to output & "Window " & w & ":" & return

            repeat with t in tabs of window w
                set totalTabs to totalTabs + 1
                set tabName to name of t
                set tabURL to URL of t
                set tabIndex to index of t

                -- Mark current tab
                set marker to "  "
                if t is current tab of window w then
                    set marker to "► "
                end if

                set output to output & marker & tabIndex & ". " & tabName & return
                set output to output & "      " & tabURL & return
            end repeat

            set output to output & return
        end if
    end repeat

    set output to output & "Total: " & totalTabs & " tab(s)"
    return output
end tell
EOF
fi
