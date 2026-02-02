#!/bin/bash
# ==============================================================================
# extract-links.sh - Extract links from the current Safari page
# ==============================================================================
# Description:
#   Extracts all links from the current Safari page. Can filter by domain,
#   pattern, or link text. Requires JavaScript permission in Safari.
#
# Prerequisites:
#   Safari > Settings > Advanced > "Show Develop menu in menu bar"
#   Develop > "Allow JavaScript from Apple Events"
#
# Usage:
#   ./extract-links.sh
#   ./extract-links.sh --domain "example.com"
#   ./extract-links.sh --pattern "/article/"
#   ./extract-links.sh --with-text
#   ./extract-links.sh --limit 20
#
# Options:
#   --domain <domain>   Only show links to this domain
#   --pattern <text>    Only show links containing this pattern
#   --with-text         Include link text alongside URLs
#   --external          Only show external links (different domain)
#   --limit <n>         Limit number of links (default: 100)
#
# Example:
#   ./extract-links.sh --domain "github.com"
#   ./extract-links.sh --external --limit 50
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
DOMAIN=""
PATTERN=""
WITH_TEXT=false
EXTERNAL=false
LIMIT=100

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --pattern)
            PATTERN="$2"
            shift 2
            ;;
        --with-text)
            WITH_TEXT=true
            shift
            ;;
        --external)
            EXTERNAL=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            head -34 "$0" | tail -29
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Build JavaScript based on options
if [[ "$WITH_TEXT" == "true" ]]; then
    JS_EXTRACT="Array.from(document.querySelectorAll('a[href]')).map(a => ({url: a.href, text: a.innerText.trim().substring(0, 100)}))"
else
    JS_EXTRACT="Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
fi

osascript <<EOF
tell application "Safari"
    if (count of windows) is 0 then
        return "No Safari windows open."
    end if

    tell front window
        set currentTab to current tab
        set pageURL to URL of currentTab

        set output to "=== LINKS FROM: " & name of currentTab & " ===" & return
        set output to output & "Page URL: " & pageURL & return & return

        try
            if $WITH_TEXT then
                set linksJSON to do JavaScript "JSON.stringify($JS_EXTRACT)" in currentTab
                -- Parse and filter in AppleScript (simplified)
                set output to output & "Links with text:" & return & return

                set jsCode to "
                    const links = $JS_EXTRACT;
                    const domain = '$DOMAIN';
                    const pattern = '$PATTERN';
                    const external = $EXTERNAL;
                    const limit = $LIMIT;
                    const pageHost = new URL('" & pageURL & "').hostname;

                    let filtered = links.filter(l => {
                        if (!l.url.startsWith('http')) return false;
                        if (domain && !l.url.includes(domain)) return false;
                        if (pattern && !l.url.includes(pattern)) return false;
                        if (external) {
                            try {
                                const linkHost = new URL(l.url).hostname;
                                if (linkHost === pageHost) return false;
                            } catch { return false; }
                        }
                        return true;
                    });

                    filtered = filtered.slice(0, limit);

                    filtered.map(l => l.text ? l.text + '\\n  ' + l.url : l.url).join('\\n\\n');
                "
                set result to do JavaScript jsCode in currentTab
                set output to output & result
            else
                set jsCode to "
                    const links = $JS_EXTRACT;
                    const domain = '$DOMAIN';
                    const pattern = '$PATTERN';
                    const external = $EXTERNAL;
                    const limit = $LIMIT;
                    const pageHost = new URL('" & pageURL & "').hostname;

                    let filtered = links.filter(l => {
                        if (!l.startsWith('http')) return false;
                        if (domain && !l.includes(domain)) return false;
                        if (pattern && !l.includes(pattern)) return false;
                        if (external) {
                            try {
                                const linkHost = new URL(l).hostname;
                                if (linkHost === pageHost) return false;
                            } catch { return false; }
                        }
                        return true;
                    });

                    // Remove duplicates
                    filtered = [...new Set(filtered)];
                    filtered = filtered.slice(0, limit);

                    filtered.join('\\n');
                "
                set result to do JavaScript jsCode in currentTab
                set output to output & result
            end if

            return output

        on error errMsg
            return "Error: JavaScript execution failed. " & return & ¬
                "Make sure 'Allow JavaScript from Apple Events' is enabled in Safari's Develop menu." & return & ¬
                "Error: " & errMsg
        end try
    end tell
end tell
EOF
