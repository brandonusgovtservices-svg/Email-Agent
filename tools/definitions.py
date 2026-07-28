TOOLS = [
    {
        "name": "get_email_details",
        "description": (
            "Fetch the full content of an email by its ID, including sender, "
            "recipient, subject, date, and body text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "Gmail message ID"},
            },
            "required": ["email_id"],
        },
    },
    {
        "name": "label_email",
        "description": (
            "Add a label to an email for organisation. "
            "Use 'Scheduling' for meeting/appointment/calendar emails. "
            "Use 'Urgent' for time-sensitive emails (hard deadlines, ASAP language, escalations, compliance notices)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "Gmail message ID"},
                "label": {
                    "type": "string",
                    "enum": ["Scheduling", "Urgent"],
                    "description": "Label to apply",
                },
            },
            "required": ["email_id", "label"],
        },
    },
    {
        "name": "get_upcoming_events",
        "description": (
            "Retrieve upcoming Google Calendar events to check existing schedule "
            "and availability before scheduling new meetings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "How many days ahead to look (default 7)",
                },
            },
        },
    },
    {
        "name": "create_calendar_event",
        "description": (
            "Create a new Google Calendar event. Use when an email contains a "
            "meeting request or confirmed scheduling information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "start_datetime": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format, e.g. 2025-06-10T14:00:00",
                },
                "end_datetime": {
                    "type": "string",
                    "description": "End time in ISO 8601 format",
                },
                "description": {"type": "string", "description": "Event notes or agenda"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Attendee email addresses",
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone (e.g. America/New_York). Defaults to America/New_York.",
                },
            },
            "required": ["title", "start_datetime", "end_datetime"],
        },
    },
    {
        "name": "create_draft_reply",
        "description": (
            "Compose and save a reply as a Gmail draft. The draft is NOT sent — "
            "Brandon reviews and sends manually."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Subject line"},
                "body": {"type": "string", "description": "Full email body text"},
                "thread_id": {
                    "type": "string",
                    "description": "Gmail thread ID so the draft is in the same thread",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "browse_web",
        "description": (
            "Browse the open web to research something relevant to an email — e.g. look up "
            "a sender's company, check a link mentioned in a message, or find publicly "
            "available information needed to draft an accurate reply. Read-only: never use "
            "this to log in, submit forms, or complete purchases."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "Plain-language description of what to find, including a URL if known "
                        "(e.g. 'Go to acmecorp.com and summarize what the company does')."
                    ),
                },
            },
            "required": ["task"],
        },
    },
]
