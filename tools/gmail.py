import base64
from email.mime.text import MIMEText


def list_unread_emails(gmail_service, max_results: int = 20) -> list[str]:
    """Return message IDs for unread non-promotional emails."""
    result = gmail_service.users().messages().list(
        userId="me",
        q="is:unread -category:promotions -category:social",
        maxResults=max_results,
    ).execute()
    return [m["id"] for m in result.get("messages", [])]


def get_email_details(gmail_service, msg_id: str) -> dict:
    """Return a structured summary of an email."""
    message = gmail_service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

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
    gmail_service,
    to: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
) -> dict:
    """Create a Gmail draft. Returns the new draft ID."""
    subject_line = subject if subject.startswith("Re:") else f"Re: {subject}"

    mime_msg = MIMEText(body, "plain")
    mime_msg["to"] = to
    mime_msg["subject"] = subject_line

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
    draft_body: dict = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    draft = gmail_service.users().drafts().create(userId="me", body=draft_body).execute()
    return {"draft_id": draft["id"], "status": "Draft created — not sent"}


def label_email(gmail_service, msg_id: str, label_name: str) -> dict:
    """Add a named label to an email, creating the label in Gmail if needed."""
    label_id = _get_or_create_label(gmail_service, label_name)
    gmail_service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": [label_id]},
    ).execute()
    return {"status": f"Labeled '{label_name}'"}


def mark_as_read(gmail_service, msg_id: str) -> None:
    gmail_service.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def _get_or_create_label(gmail_service, name: str) -> str:
    """Return the Gmail label ID for `name`, creating it if it doesn't exist."""
    labels = gmail_service.users().labels().list(userId="me").execute()
    for label in labels.get("labels", []):
        if label["name"].lower() == name.lower():
            return label["id"]

    created = gmail_service.users().labels().create(
        userId="me",
        body={
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    return created["id"]


def _extract_body(payload: dict) -> str:
    """Walk the MIME tree and return the first plain-text body."""
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
