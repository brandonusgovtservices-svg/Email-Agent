from datetime import datetime, timedelta, timezone


def get_upcoming_events(calendar_service, days: int = 7) -> list[dict]:
    """Return simplified upcoming events for the next `days` days."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    result = calendar_service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=25,
    ).execute()

    events = []
    for item in result.get("items", []):
        start = item["start"].get("dateTime", item["start"].get("date"))
        end_time = item["end"].get("dateTime", item["end"].get("date"))
        events.append({
            "id": item["id"],
            "title": item.get("summary", "Untitled"),
            "start": start,
            "end": end_time,
            "attendees": [a["email"] for a in item.get("attendees", [])],
        })
    return events


def create_calendar_event(
    calendar_service,
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str | None = None,
    attendees: list[str] | None = None,
    tz: str = "America/New_York",
) -> dict:
    """Create a Google Calendar event. Returns event ID and link."""
    event: dict = {
        "summary": title,
        "start": {"dateTime": start_datetime, "timeZone": tz},
        "end": {"dateTime": end_datetime, "timeZone": tz},
    }
    if description:
        event["description"] = description
    if attendees:
        event["attendees"] = [{"email": a} for a in attendees]

    created = calendar_service.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="none",
    ).execute()

    return {
        "event_id": created["id"],
        "link": created.get("htmlLink", ""),
        "status": f'Event "{title}" created for {start_datetime}',
    }
