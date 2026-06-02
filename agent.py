"""Email agent — reads Gmail, drafts replies, creates calendar events."""

import argparse
import os
import json
import anthropic
from dotenv import load_dotenv

from auth import get_google_services
from tools.gmail import list_unread_emails, get_email_details, create_draft_reply, mark_as_read
from tools.calendar import get_upcoming_events, create_calendar_event
from tools.definitions import TOOLS

load_dotenv()

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You are an intelligent email assistant. Process unread emails and take appropriate action.

For each email:
1. Use get_email_details to read the full message.
2. Determine intent: scheduling request, question, action item, or no-reply needed.
3. For any email involving a meeting or scheduling request:
   a. Call get_upcoming_events to check the calendar.
   b. Call create_calendar_event to block the time.
   c. Call create_draft_reply to confirm the meeting to the sender.
4. For other emails that need a response, call create_draft_reply with a concise, professional reply.
5. For notifications, receipts, or newsletters, state why no reply is needed and skip drafting.

Always use create_draft_reply — never send emails directly.
Sign off using the account owner's name when available in the "to" address of prior emails."""


def _dispatch(tool_name: str, tool_input: dict, gmail, calendar, dry_run: bool) -> str:
    if dry_run and tool_name in ("create_draft_reply", "create_calendar_event"):
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
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def process_email(email_id: str, client: anthropic.Anthropic, gmail, calendar, dry_run: bool) -> None:
    print(f"\n  Email {email_id}")

    messages = [
        {
            "role": "user",
            "content": f"Process email ID: {email_id}",
        }
    ]

    # Cache system prompt and tools — saves tokens across the per-email loops
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
                    print(f"  [tool] {block.name}")
                    result = _dispatch(block.name, block.input, gmail, calendar, dry_run)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason
            break

    if not dry_run:
        mark_as_read(gmail, email_id)


def run(limit: int = 20, dry_run: bool = False) -> None:
    print("Email Agent starting" + (" [dry-run]" if dry_run else "") + "...")

    client = anthropic.Anthropic()
    gmail, calendar = get_google_services()
    print("Connected to Google services.")

    email_ids = list_unread_emails(gmail, max_results=limit)

    if not email_ids:
        print("No unread emails.")
        return

    print(f"Found {len(email_ids)} unread email(s).")

    for email_id in email_ids:
        try:
            process_email(email_id, client, gmail, calendar, dry_run)
        except Exception as exc:
            print(f"  [error] {email_id}: {exc}")

    print(f"\nDone. Processed {len(email_ids)} email(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI email agent")
    parser.add_argument("--limit", type=int, default=20, help="Max emails to process (default 20)")
    parser.add_argument("--dry-run", action="store_true", help="Read and analyse emails; skip drafts and calendar writes")
    args = parser.parse_args()

    run(limit=args.limit, dry_run=args.dry_run)
