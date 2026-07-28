# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Python email agent that uses Claude Opus (Anthropic SDK) as an agentic reasoning core to process Gmail messages, compose draft replies, and manage Google Calendar events. The agent never sends email directly — it only creates drafts for human review.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# One-time: download the Chromium build browser-use/Playwright drives
playwright install chromium

# First run — triggers Google OAuth browser flow, writes token.json
python agent.py

# Process up to N unread emails
python agent.py --limit 5

# Read and analyse emails without writing any drafts, labels, or calendar events
python agent.py --dry-run

# Run continuously, checking every 15 minutes
python agent.py --watch

# Watch mode with custom interval (minutes)
python agent.py --watch --interval 30
```

Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY` before running.

## Architecture

### Entry point: `agent.py`

Runs the main loop: fetches unread Gmail IDs → for each email, drives a Claude agentic tool-use loop until `stop_reason == "end_turn"` → marks email as read.

The agentic loop follows the standard Anthropic SDK pattern:
1. Send message to Claude with tools
2. On `tool_use` stop: dispatch each tool call, append `tool_result` blocks, loop
3. On `end_turn` stop: print Claude's summary, exit loop

Prompt caching (`cache_control: ephemeral`) is applied to the system prompt on every `messages.create` call to reduce token costs across the per-email loops.

`--watch` mode keeps the Google services and Anthropic client alive between polling cycles (no re-auth overhead).

### Auth: `auth.py`

Handles Google OAuth2 for both Gmail and Calendar APIs using a single `get_google_services()` call. Reads `credentials.json` (not committed), writes/refreshes `token.json` (not committed). Required scopes: `gmail.modify` and `calendar`.

### Tools layer

| File | Purpose |
|------|---------|
| `tools/gmail.py` | `list_unread_emails`, `get_email_details`, `create_draft_reply`, `label_email`, `mark_as_read` |
| `tools/calendar.py` | `get_upcoming_events`, `create_calendar_event` |
| `tools/browser.py` | `browse_web` — runs a [browser-use](https://github.com/browser-use/browser-use) sub-agent (headless Chromium via Playwright) to research something on the open web |
| `tools/definitions.py` | Tool JSON schemas passed to Claude's `tools` parameter |

The `_dispatch()` function in `agent.py` maps tool names from Claude's response to the Python functions above. `--dry-run` short-circuits `create_draft_reply`, `create_calendar_event`, and `label_email` in `_dispatch` without touching the LLM loop. `browse_web` is read-only, so it still runs in `--dry-run`.

### Agent behaviour

Claude is instructed to:
- **Label "Scheduling"** — any email involving a meeting, appointment, or calendar request
- **Label "Urgent"** — emails with ASAP language, hard deadlines, escalating clients, or compliance notices; labels are auto-created in Gmail on first use via `_get_or_create_label()`
- **Scheduling flow**: check calendar → create event → draft confirmation reply
- **Other emails**: draft a casual, direct reply signed with Brandon's full signature
- **No-reply emails** (receipts, newsletters): skip drafting, briefly explain why
- **Research** — when drafting needs outside information (a sender's company, a link in the email), call `browse_web`; it drives a real headless browser but is instructed to stay read-only (no logins, forms, or purchases). Sub-agent model is `claude-sonnet-4-5` by default, overridable via the `BROWSE_MODEL` env var.

### Scheduling behaviour

When Claude detects a scheduling request in an email it:
1. Calls `get_upcoming_events` to see existing calendar blocks
2. Calls `create_calendar_event` to add the meeting
3. Calls `create_draft_reply` to send a confirmation to the sender

The `TIMEZONE` env var (default `America/New_York`) is applied to all created calendar events.

## Google API Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Gmail API** and **Google Calendar API**
3. Create **OAuth 2.0 credentials** (application type: Desktop app)
4. Download the JSON file and save it as `credentials.json` in the project root
5. Run `python agent.py` — a browser window opens for consent, then `token.json` is created automatically
