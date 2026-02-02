#!/bin/bash
# ==============================================================================
# common.sh - Shared utilities for macOS automation scripts
# ==============================================================================
# This library provides common functions used across all automation scripts.
# Source this file at the beginning of other scripts.
# ==============================================================================

# Colors for output (disabled if not a terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Print an error message and exit
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

# Print a warning message
warn() {
    echo -e "${YELLOW}Warning: $1${NC}" >&2
}

# Print an info message
info() {
    echo -e "${BLUE}$1${NC}"
}

# Print a success message
success() {
    echo -e "${GREEN}$1${NC}"
}

# Check if an app is running
is_app_running() {
    local app_name="$1"
    osascript -e "tell application \"System Events\" to (name of processes) contains \"$app_name\"" 2>/dev/null
}

# Launch an app if not running
ensure_app_running() {
    local app_name="$1"
    if [[ $(is_app_running "$app_name") != "true" ]]; then
        osascript -e "tell application \"$app_name\" to activate" 2>/dev/null
        sleep 1
    fi
}

# Format a date for AppleScript
format_date_for_applescript() {
    # Takes a date string and formats it for AppleScript
    # Usage: format_date_for_applescript "2026-01-30 14:00"
    local date_str="$1"
    date -j -f "%Y-%m-%d %H:%M" "$date_str" "+%B %d, %Y %I:%M %p" 2>/dev/null
}

# Get today's date formatted for AppleScript
get_today_applescript() {
    date "+%B %d, %Y"
}

# Escape special characters for AppleScript strings
escape_for_applescript() {
    local str="$1"
    # Escape backslashes first, then double quotes
    str="${str//\\/\\\\}"
    str="${str//\"/\\\"}"
    echo "$str"
}
