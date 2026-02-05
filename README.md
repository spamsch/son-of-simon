<p align="center">
  <img src="assets/logo-observer.svg" alt="Son of Simon" width="200" height="200">
</p>

<h1 align="center">Son of Simon</h1>

<p align="center">
  <em>An LLM-powered agent for macOS automation. Give natural language commands, it figures out the rest.</em>
</p>

---

## Features

- **macOS Automation** - Control Mail, Calendar, Reminders, Notes, and Safari via natural language
- **Telegram Integration** - Send commands via text or voice, receive responses with conversation context
- **Multi-LLM Support** - OpenAI, Anthropic, Groq, Ollama, and 100+ providers via LiteLLM
- **Paperless-ngx Integration** - Search, upload, and download documents from your paperless instance
- **Scheduled Jobs** - Run automated tasks on intervals or cron schedules
- **Browser Automation** - ARIA-based web interaction with screenshots and element detection
- **Voice Commands** - Send voice messages via Telegram, automatically transcribed via Whisper

## Quick Start

```bash
# Install
pip install -e .

# Interactive setup wizard
macbot onboard

# Run a goal
macbot run "Check my emails and summarize urgent ones"

# Multiline prompt
macbot run -m

# Start service (Telegram + cron jobs)
macbot start
```

## Commands

| Command | Description |
|---------|-------------|
| `macbot run "<goal>"` | Run a natural language goal |
| `macbot run -m` | Run with multiline input (Ctrl+D to end) |
| `macbot chat` | Interactive conversation mode |
| `macbot start` | Start service (Telegram + cron) |
| `macbot stop` | Stop the service |
| `macbot status` | Check service status |
| `macbot doctor` | Verify setup and permissions |
| `macbot onboard` | Interactive setup wizard |
| `macbot tasks` | List available tasks |
| `macbot cron list` | List scheduled jobs |

## Configuration

Run `macbot onboard` for interactive setup, or create `~/.macbot/.env`:

```bash
# LLM Model (provider/model format)
MACBOT_MODEL=openai/gpt-4o
MACBOT_OPENAI_API_KEY=sk-...

# Or use Anthropic
# MACBOT_MODEL=anthropic/claude-sonnet-4-20250514
# MACBOT_ANTHROPIC_API_KEY=sk-ant-...

# Or use other providers (Groq, Ollama, etc.)
# MACBOT_MODEL=groq/llama3-70b-8192
# GROQ_API_KEY=gsk_...

# Telegram (optional)
MACBOT_TELEGRAM_BOT_TOKEN=123456:ABC...
MACBOT_TELEGRAM_CHAT_ID=your_chat_id

# Paperless-ngx (optional)
MACBOT_PAPERLESS_URL=http://localhost:8000
MACBOT_PAPERLESS_API_TOKEN=your_token

# Agent settings
MACBOT_MAX_ITERATIONS=100
```

## Available Tasks

**Mail** - `search_emails`, `send_email`, `move_email`, `mark_emails_read`, `download_attachments`

**Calendar** - `get_today_events`, `get_week_events`, `create_calendar_event`, `list_calendars`

**Reminders** - `create_reminder`, `complete_reminder`, `list_reminders`, `get_due_today_reminders`

**Notes** - `create_note`, `search_notes`, `list_notes`

**Safari** - `get_current_safari_page`, `open_url_in_safari`, `list_safari_tabs`, `extract_safari_links`

**Browser** - `browser_navigate`, `browser_click`, `browser_type`, `browser_screenshot`, `browser_snapshot`

**Paperless** - `paperless_search`, `paperless_upload`, `paperless_download`, `paperless_list_tags`

**Telegram** - `telegram_send`

**Web** - `web_search`, `web_fetch`

**Time Tracking** - `timer_start`, `timer_stop`, `timer_status`, `timer_report`

**Memory** - `memory_add_fact`, `memory_add_lesson`, `memory_set_preference`, `memory_list`

**System** - `get_system_info`, `read_file`, `write_file`, `run_shell_command`

## Scheduled Jobs

Create `jobs.yaml`:

```yaml
jobs:
  - name: "Morning Briefing"
    goal: |
      Give me a morning briefing:
      - Unread emails summary
      - Today's calendar
      - Reminders due today
    cron: "0 9 * * *"
    timezone: "Europe/Berlin"

  - name: "Email Check"
    goal: "Check for urgent emails and notify me via Telegram"
    interval: 300  # every 5 minutes
```

```bash
macbot cron import jobs.yaml
macbot start -d  # Start as daemon
```

## Telegram Usage

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Run `macbot onboard` to configure
3. Start service: `macbot start`
4. Send text or voice messages to your bot

Special commands in Telegram:
- `/reset`, `/clear`, `/new` - Start a fresh conversation

Conversation context is preserved between messages for natural back-and-forth chat.

## Examples

```bash
# Email management
macbot run "Find emails from Amazon this week and list any with tracking numbers"

# Calendar
macbot run "What meetings do I have tomorrow? Create reminders 15 min before each"

# Bookings
macbot run "Book a table at Restaurant Eichenhof for Saturday 7pm, 2 people"

# Paperless
macbot run "Search paperless for invoices from 2024"

# Browser automation
macbot run "Open google.com, search for 'weather', and take a screenshot"

# Time tracking
macbot run "Start a timer for client work"
macbot run "Stop the timer"
macbot run "Show my time report for this week"

# Complex workflows
macbot run "Check my emails, archive newsletters, and send me a Telegram summary"
```

## Architecture

```
~/.macbot/
├── .env              # Configuration
├── cron.json         # Scheduled jobs
├── memory.db         # Agent memory (processed emails, etc.)
├── knowledge.yaml    # Learned facts and preferences
├── time_tracking.db  # Time entries
└── service.log       # Service logs

src/macbot/
├── cli.py            # Command-line interface
├── config.py         # Settings management
├── service.py        # Unified service (cron + telegram)
├── core/
│   └── agent.py      # ReAct agent loop
├── providers/
│   └── litellm_provider.py  # Multi-LLM support
├── tasks/            # Task implementations
│   ├── macos_automation.py
│   ├── browser_automation.py
│   ├── paperless.py
│   ├── time_tracking.py
│   └── telegram.py
└── telegram/         # Telegram integration
```

## License

MIT License
