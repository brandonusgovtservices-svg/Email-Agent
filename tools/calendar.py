from datetime import datetime, timedelta, timezone

BASE = "https://www.googleapis.com/calendar/v3"


def get_upcoming_events(session, days: int = 7) -> list[dict]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    r = session.get(f"{BASE}/calendars/primary/events", params={
        "timeMin": now.isoformat(),
        "timeMax": end.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 25,
    })
    r.raise_for_status()

    events = []
    for item in r.json().get("items", []):
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
    session,
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str | None = None,
    attendees: list[str] | None = None,
    tz: str = "America/New_York",
) -> dict:
    event: dict = {
        "summary": title,
        "start": {"dateTime": start_datetime, "timeZone": tz},
        "end": {"dateTime": end_datetime, "timeZone": tz},
    }
    if description:
        event["description"] = description
    if attendees:
        event["attendees"] = [{"email": a} for a in attendees]

    r = session.post(
        f"{BASE}/calendars/primary/events",
        json=event,
        params={"sendUpdates": "none"},
    )
    r.raise_for_status()
    created = r.json()
    return {
        "event_id": created["id"],
        "link": created.get("htmlLink", ""),
        "status": f'Event "{title}" created for {start_datetime}',
    }
