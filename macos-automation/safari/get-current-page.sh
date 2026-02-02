#!/bin/bash
# ==============================================================================
# get-current-page.sh - Get information about the current Safari tab
# ==============================================================================
# Description:
#   Retrieves information about the currently active Safari tab including
#   URL, title, and optionally the page content.
#
# Usage:
#   ./get-current-page.sh
#   ./get-current-page.sh --with-text
#   ./get-current-page.sh --with-source
#
# Options:
#   --with-text     Include extracted text content from the page
#   --with-source   Include HTML source (first 5000 chars)
#   --json          Output in JSON format
#
# Example:
#   ./get-current-page.sh
#   ./get-current-page.sh --with-text
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

WITH_TEXT=false
WITH_SOURCE=false
JSON_OUTPUT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-text)
            WITH_TEXT=true
            shift
            ;;
        --with-source)
            WITH_SOURCE=true
            shift
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
        return "{\"error\": \"No Safari windows open\"}"
    end if

    tell front window
        set currentTab to current tab
        set pageTitle to name of currentTab
        set pageURL to URL of currentTab

        set jsonOutput to "{" & return
        set jsonOutput to jsonOutput & "  \"title\": \"" & pageTitle & "\"," & return
        set jsonOutput to jsonOutput & "  \"url\": \"" & pageURL & "\""

        if $WITH_TEXT then
            try
                set pageText to do JavaScript "document.body.innerText.substring(0, 2000)" in currentTab
                -- Escape for JSON
                set pageText to my replaceText(pageText, "\"", "\\\"")
                set pageText to my replaceText(pageText, return, "\\n")
                set jsonOutput to jsonOutput & "," & return
                set jsonOutput to jsonOutput & "  \"text\": \"" & pageText & "\""
            end try
        end if

        set jsonOutput to jsonOutput & return & "}"
        return jsonOutput
    end tell
end tell

on replaceText(theText, searchString, replacementString)
    set AppleScript's text item delimiters to searchString
    set theItems to text items of theText
    set AppleScript's text item delimiters to replacementString
    set theText to theItems as text
    set AppleScript's text item delimiters to ""
    return theText
end replaceText
EOF
else
    osascript <<EOF
tell application "Safari"
    if (count of windows) is 0 then
        return "No Safari windows open."
    end if

    tell front window
        set currentTab to current tab
        set output to "=== CURRENT PAGE ===" & return & return
        set output to output & "Title: " & name of currentTab & return
        set output to output & "URL: " & URL of currentTab & return
        set output to output & "Tab Index: " & index of currentTab & return

        if $WITH_TEXT then
            set output to output & return & "=== PAGE TEXT ===" & return
            try
                set pageText to do JavaScript "document.body.innerText.substring(0, 3000)" in currentTab
                set output to output & pageText & return
                if length of pageText >= 3000 then
                    set output to output & "... (truncated)" & return
                end if
            on error
                set output to output & "(JavaScript execution not permitted or page not fully loaded)" & return
            end try
        end if

        if $WITH_SOURCE then
            set output to output & return & "=== HTML SOURCE (first 5000 chars) ===" & return
            set pageSource to source of currentTab
            if length of pageSource > 5000 then
                set output to output & (text 1 thru 5000 of pageSource) & return
                set output to output & "... (truncated)" & return
            else
                set output to output & pageSource & return
            end if
        end if

        return output
    end tell
end tell
EOF
fi
