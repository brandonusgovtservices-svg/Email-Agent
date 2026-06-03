import base64
from email.mime.text import MIMEText

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def list_unread_emails(session, max_results: int = 20) -> list[str]:
    r = session.get(f"{BASE}/messages", params={
        "q": "is:unread -category:promotions -category:social",
        "maxResults": max_results,
    })
    r.raise_for_status()
    return [m["id"] for m in r.json().get("messages", [])]


def get_email_details(session, msg_id: str) -> dict:
    r = session.get(f"{BASE}/messages/{msg_id}", params={"format": "full"})
    r.raise_for_status()
    message = r.json()

    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
    body = _extract_body(message["payload"])

    return {
        "id": msg_id,
        "thread_id": message["threadId"],
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
        "body": body[:4000],
        "snippet": message.get("snippet", ""),
    }


def create_draft_reply(
    session,
    to: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
) -> dict:
    subject_line = subject if subject.startswith("Re:") else f"Re: {subject}"
    mime_msg = MIMEText(body, "plain")
    mime_msg["to"] = to
    mime_msg["subject"] = subject_line

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
    payload: dict = {"message": {"raw": raw}}
    if thread_id:
        payload["message"]["threadId"] = thread_id

    r = session.post(f"{BASE}/drafts", json=payload)
    r.raise_for_status()
    draft = r.json()
    return {"draft_id": draft["id"], "status": "Draft created — not sent"}


def label_email(session, msg_id: str, label_name: str) -> dict:
    label_id = _get_or_create_label(session, label_name)
    r = session.post(
        f"{BASE}/messages/{msg_id}/modify",
        json={"addLabelIds": [label_id]},
    )
    r.raise_for_status()
    return {"status": f"Labeled '{label_name}'"}


def mark_as_read(session, msg_id: str) -> None:
    session.post(
        f"{BASE}/messages/{msg_id}/modify",
        json={"removeLabelIds": ["UNREAD"]},
    ).raise_for_status()


def _get_or_create_label(session, name: str) -> str:
    r = session.get(f"{BASE}/labels")
    r.raise_for_status()
    for label in r.json().get("labels", []):
        if label["name"].lower() == name.lower():
            return label["id"]

    r = session.post(f"{BASE}/labels", json={
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    })
    r.raise_for_status()
    return r.json()["id"]


def _extract_body(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            text = _extract_body(part)
            if text:
                return text
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""
