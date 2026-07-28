"""Email agent — reads Gmail, drafts replies, creates calendar events."""

import argparse
import json
import os
import time
import anthropic
from dotenv import load_dotenv

from auth import get_google_services
from tools.gmail import list_unread_emails, get_email_details, create_draft_reply, mark_as_read, label_email
from tools.calendar import get_upcoming_events, create_calendar_event
from tools.browser import browse_web
from tools.definitions import TOOLS

load_dotenv()

MODEL = "claude-opus-4-8"

SIGNATURE = """
Brandon Michael
US Government Services
571-528-8760
brandon@usgovtservices.com"""

SYSTEM_PROMPT = f"""You are Brandon Michael's personal email assistant at US Government Services. Your job is to process unread emails and take the right action for each one.

Brandon's signature (use at the end of every draft reply):
{SIGNATURE}

For each email:
1. Call get_email_details to read the full message.
2. Decide: is it a scheduling/meeting request, a question/action item, or something that needs no reply (newsletters, receipts, notifications)?
3. Label the email when relevant:
   - Call label_email with label "Scheduling" for any meeting, appointment, or calendar request
   - Call label_email with label "Urgent" for time-sensitive emails — think: ASAP language, hard deadlines, angry or escalating clients, government compliance notices
4. For scheduling emails:
   a. Call get_upcoming_events to check what's already on the calendar.
   b. Call create_calendar_event to block the time.
   c. Call create_draft_reply to confirm — keep it short and casual.
5. For other emails that need a response, call create_draft_reply with a casual, friendly reply. No corporate stiffness — use contractions, be direct, sound like a real person.
6. For no-reply emails, briefly say why you're skipping a draft.
7. If you need to look something up on the web to draft an accurate reply (e.g. a sender's company, a link mentioned in the email), call browse_web. It's read-only — never use it to log in, submit forms, or make purchases.

Tone rules: casual and warm, not formal. Short sentences. Don't start with "I hope this email finds you well." Sign off every draft with Brandon's signature above.
Always use create_draft_reply — never send emails directly."""


def _dispatch(tool_name: str, tool_input: dict, gmail, calendar, dry_run: bool) -> str:
    if dry_run and tool_name in ("create_draft_reply", "create_calendar_event", "label_email"):
        return json.dumps({"status": f"[dry-run] Would call {tool_name}", "input": tool_input})

    if tool_name == "get_email_details":
        return json.dumps(get_email_details(gmail, tool_input["email_id"]))
    elif tool_name == "get_upcoming_events":
        return json.dumps(get_upcoming_events(calendar, tool_input.get("days", 7)))
    elif tool_name == "create_calendar_event":
        tz = tool_input.get("timezone") or os.getenv("TIMEZONE", "America/New_York")
        return json.dumps(create_calendar_event(
            calendar,
            tool_input["title"],
            tool_input["start_datetime"],
            tool_input["end_datetime"],
            tool_input.get("description"),
            tool_input.get("attendees"),
            tz,
        ))
    elif tool_name == "create_draft_reply":
        return json.dumps(create_draft_reply(
            gmail,
            tool_input["to"],
            tool_input["subject"],
            tool_input["body"],
            tool_input.get("thread_id"),
        ))
    elif tool_name == "label_email":
        return json.dumps(label_email(gmail, tool_input["email_id"], tool_input["label"]))
    elif tool_name == "browse_web":
        return json.dumps(browse_web(tool_input["task"]))
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def process_email(email_id: str, client: anthropic.Anthropic, gmail, calendar, dry_run: bool) -> None:
    print(f"\n  Email {email_id}")

    messages = [{"role": "user", "content": f"Process email ID: {email_id}"}]

    cached_system = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=cached_system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print(f"  → {block.text}")
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    preview = {k: v for k, v in block.input.items() if k not in ("body",)}
                    print(f"  [tool] {block.name}({preview})")
                    result = _dispatch(block.name, block.input, gmail, calendar, dry_run)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    if not dry_run:
        mark_as_read(gmail, email_id)


def run(limit: int, dry_run: bool, client: anthropic.Anthropic, gmail, calendar) -> None:
    email_ids = list_unread_emails(gmail, max_results=limit)

    if not email_ids:
        print("  No unread emails.")
        return

    print(f"  Found {len(email_ids)} unread email(s).")

    for email_id in email_ids:
        try:
            process_email(email_id, client, gmail, calendar, dry_run)
        except Exception as exc:
            print(f"  [error] {email_id}: {exc}")

    print(f"\n  Done. Processed {len(email_ids)} email(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brandon's AI email agent")
    parser.add_argument("--limit", type=int, default=20, help="Max emails per run (default 20)")
    parser.add_argument("--dry-run", action="store_true", help="Analyse emails without writing drafts or events")
    parser.add_argument("--watch", action="store_true", help="Run continuously on a schedule")
    parser.add_argument("--interval", type=int, default=15, help="Minutes between checks in watch mode (default 15)")
    args = parser.parse_args()

    client = anthropic.Anthropic()
    gmail, calendar = get_google_services()
    print("Email Agent ready" + (" [dry-run]" if args.dry_run else "") + ".")

    if args.watch:
        print(f"Watch mode — checking every {args.interval} minutes. Ctrl+C to stop.\n")
        while True:
            print(f"[{time.strftime('%H:%M:%S')}] Checking emails...")
            run(args.limit, args.dry_run, client, gmail, calendar)
            print(f"Sleeping {args.interval}m...")
            time.sleep(args.interval * 60)
    else:
        run(args.limit, args.dry_run, client, gmail, calendar)
