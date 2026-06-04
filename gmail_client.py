import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import AGENT_PROCESSED_LABEL, GMAIL_SCOPES

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")


class GmailClient:
    def __init__(self):
        self.service = self._build_service()
        self._processed_label_id = self._ensure_label()

    def _build_service(self):
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    def _ensure_label(self) -> str:
        labels = self.service.users().labels().list(userId="me").execute()
        for label in labels.get("labels", []):
            if label["name"] == AGENT_PROCESSED_LABEL:
                return label["id"]
        result = self.service.users().labels().create(
            userId="me",
            body={"name": AGENT_PROCESSED_LABEL, "labelListVisibility": "labelHide"},
        ).execute()
        return result["id"]

    def search_threads(self, query: str) -> list[dict]:
        result = (
            self.service.users()
            .threads()
            .list(userId="me", q=query, maxResults=10)
            .execute()
        )
        return result.get("threads", [])

    def get_thread_content(self, thread_id: str) -> dict | None:
        thread = (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        messages = thread.get("messages", [])
        if not messages:
            return None
        msg = messages[-1]
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        return {
            "thread_id": thread_id,
            "message_id": msg["id"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "body": self._decode_body(msg["payload"]),
        }

    def _decode_body(self, payload: dict) -> str:
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        return ""

    def send_reply(self, original: dict, body: str):
        msg = MIMEMultipart()
        msg["To"] = original["from"]
        msg["Subject"] = f"Re: {original['subject']}"
        msg["In-Reply-To"] = original["message_id"]
        msg["References"] = original["message_id"]
        msg.attach(MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        self.service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": original["thread_id"]},
        ).execute()

    def mark_processed(self, thread_id: str):
        self.service.users().threads().modify(
            userId="me",
            id=thread_id,
            body={
                "addLabelIds": [self._processed_label_id],
                "removeLabelIds": ["UNREAD"],
            },
        ).execute()
