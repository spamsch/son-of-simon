# Safari Browser Automation Implementation Plan

## Overview

Implement an ARIA-based browser automation system for Safari, inspired by OpenClaw's approach but adapted for macOS/Safari using AppleScript + JavaScript injection.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Agent                               │
│                   (uses tasks via registry)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Task Layer (Python)                           │
│         src/macbot/tasks/browser_automation.py                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │BrowserOpen  │ │BrowserSnap- │ │BrowserClick │ ...           │
│  │Task         │ │shotTask     │ │Task         │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Browser Module (Python)                         │
│              src/macbot/browser/__init__.py                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │SafariControl│ │SnapshotMgr  │ │RefResolver  │               │
│  │ler          │ │             │ │             │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Shell Scripts Layer                            │
│              macos-automation/browser/                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │navigate.sh  │ │snapshot.sh  │ │interact.sh  │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Safari + JavaScript                         │
│           AppleScript controls Safari                            │
│           JavaScript extracts ARIA tree & interacts              │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. JavaScript ARIA Snapshot Library (`macos-automation/browser/lib/aria-snapshot.js`)

Extracts accessibility tree from DOM and creates numbered refs:

```javascript
// Output format:
// [e1] button "Search"
// [e2] textbox "Email" value="user@example.com"
// [e3] link "Sign up"
//   [e4] heading "Welcome"
```

**Key features:**
- Extract ARIA roles from elements
- Generate stable refs (e1, e2, e3...)
- Include accessible names and values
- Track interactive vs structural elements
- Return JSON with refs map for resolution

### 2. Shell Scripts (`macos-automation/browser/`)

| Script | Purpose |
|--------|---------|
| `navigate.sh` | Open URL in Safari, wait for load |
| `snapshot.sh` | Get ARIA snapshot of current page |
| `click.sh` | Click element by ref |
| `type.sh` | Type text into element by ref |
| `select.sh` | Select option in dropdown |
| `scroll.sh` | Scroll element into view |
| `screenshot.sh` | Capture screenshot |
| `get-text.sh` | Get text content of element |
| `close-tab.sh` | Close current tab |
| `doctor.sh` | Check Safari prerequisites |

### 3. Python Browser Module (`src/macbot/browser/`)

```
src/macbot/browser/
├── __init__.py          # Public API exports
├── safari.py            # Safari control via scripts
├── snapshot.py          # Snapshot parsing and management
├── refs.py              # Ref storage and resolution
├── types.py             # Type definitions (dataclasses)
└── exceptions.py        # Custom exceptions
```

**Key classes:**

```python
@dataclass
class ElementRef:
    ref: str           # e.g., "e1"
    role: str          # e.g., "button"
    name: str | None   # e.g., "Search"
    value: str | None  # e.g., current input value

@dataclass
class Snapshot:
    text: str                      # Human-readable snapshot
    refs: dict[str, ElementRef]    # Ref -> element mapping
    timestamp: datetime
    url: str

class SafariBrowser:
    async def navigate(self, url: str) -> None
    async def snapshot(self, interactive_only: bool = True) -> Snapshot
    async def click(self, ref: str) -> None
    async def type(self, ref: str, text: str, submit: bool = False) -> None
    async def select(self, ref: str, value: str) -> None
    async def screenshot(self, path: str | None = None) -> bytes
    async def get_text(self, ref: str) -> str
    async def close(self) -> None
```

### 4. Task Layer (`src/macbot/tasks/browser_automation.py`)

Tasks for the react agent:

| Task | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_snapshot` | Get page snapshot with interactive elements |
| `browser_click` | Click element by ref from snapshot |
| `browser_type` | Type text into input field |
| `browser_select` | Select dropdown option |
| `browser_screenshot` | Take screenshot |
| `browser_get_text` | Get text content of element |
| `browser_close` | Close browser tab |

### 5. Doctor Command Updates

Add checks in `cli.py` doctor command:
- Safari "Allow JavaScript from Apple Events" enabled
- Safari Develop menu enabled
- Test JavaScript execution in Safari

## Implementation Steps

### Phase 1: JavaScript ARIA Library
1. Create `aria-snapshot.js` with DOM traversal
2. Implement role detection and ref generation
3. Test in Safari console
4. Create `snapshot.sh` wrapper script

### Phase 2: Basic Safari Control Scripts
1. Create `navigate.sh` (reuse existing pattern)
2. Create `click.sh` with ref resolution
3. Create `type.sh` with ref resolution
4. Create `screenshot.sh`

### Phase 3: Python Browser Module
1. Create `types.py` with dataclasses
2. Create `snapshot.py` for parsing snapshots
3. Create `refs.py` for ref management
4. Create `safari.py` orchestration class
5. Add `__init__.py` with public exports

### Phase 4: Task Integration
1. Create `browser_automation.py` with Task classes
2. Register tasks in `tasks/__init__.py`
3. Update doctor command with Safari checks

### Phase 5: Documentation & Testing
1. Add README.md with usage examples
2. Add docstrings throughout
3. Test with booking.com example

## File Structure (Final)

```
macos-automation/browser/
├── README.md
├── lib/
│   └── aria-snapshot.js      # Core JS library
├── navigate.sh
├── snapshot.sh
├── click.sh
├── type.sh
├── select.sh
├── scroll.sh
├── screenshot.sh
├── get-text.sh
├── close-tab.sh
└── doctor.sh

src/macbot/browser/
├── __init__.py
├── types.py
├── snapshot.py
├── refs.py
├── safari.py
└── exceptions.py

src/macbot/tasks/
├── browser_automation.py     # New file
└── __init__.py               # Updated
```

## Usage Example (for React Agent)

```python
# Agent workflow for booking.com:

# 1. Navigate to site
await browser_navigate(url="https://booking.com")

# 2. Get snapshot to see available elements
snapshot = await browser_snapshot()
# Returns:
# [e1] textbox "Where are you going?"
# [e2] button "Check-in date"
# [e3] button "Check-out date"
# [e4] button "Search"
# ...

# 3. Type destination
await browser_type(ref="e1", text="Berlin")

# 4. Click date picker
await browser_click(ref="e2")

# 5. Get new snapshot (UI changed)
snapshot = await browser_snapshot()
# Returns calendar elements...

# 6. Continue interacting...
```

## Prerequisites

1. **Safari Settings:**
   - Develop menu enabled (Safari > Settings > Advanced)
   - "Allow JavaScript from Apple Events" checked (Develop menu)

2. **No additional dependencies** - uses built-in macOS tools

## Notes

- Refs are regenerated on each snapshot (not persistent across pages)
- Agent should take fresh snapshot after any action that changes UI
- Snapshot includes only interactive elements by default (configurable)
- All operations are async for consistency with existing task system

## Lessons Learned: Booking.com Testing (Feb 2026)

### Challenges Encountered

1. **React Controlled Inputs**
   - Problem: Direct `el.value = text` doesn't trigger React's onChange handlers
   - Solution: Use native input value setter to bypass React's property override:
   ```javascript
   const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
   nativeSetter.call(el, text);
   el.dispatchEvent(new Event('input', { bubbles: true }));
   ```

2. **Synthetic Event Detection (Anti-Bot)**
   - Problem: Sites like Booking.com detect JavaScript `dispatchEvent()` calls
   - Solution: Use `cliclick` for physical mouse clicks:
   ```bash
   # physical-click.sh
   cliclick c:$CLICK_X,$CLICK_Y
   ```

3. **Complex Widget Interaction (Calendar Date Picker)**
   - Problem: Clicking calendar dates requires precise coordinates, tricky with multiple displays
   - Solution: Use URL parameters for direct search:
   ```
   https://www.booking.com/searchresults.html?ss=Paris&checkin=2026-03-15&checkout=2026-03-18
   ```

### Scripts Added for Anti-Bot Handling

| Script | Purpose |
|--------|---------|
| `physical-click.sh` | Real mouse click via cliclick (bypasses synthetic event detection) |
| `visual-snapshot.sh` | Screenshot with ref labels overlaid (for vision models) |
| `press-key.sh` | Simulate keyboard keys (escape, enter, etc.) |
| `dismiss-cookies.sh` | Auto-dismiss cookie consent banners |

### Recommended Workflow for Complex Sites

1. **Navigate** with URL parameters when possible (dates, filters)
2. **Inject ARIA library** on page load (`snapshot.sh --inject`)
3. **Use physical clicks** for autocomplete/dropdown selection
4. **Take visual snapshots** for vision model analysis when ARIA snapshot isn't enough
5. **Use URL parameters** for search/filter operations rather than UI interaction

### Dependencies

- `cliclick` - Install via `brew install cliclick` for physical mouse clicks
