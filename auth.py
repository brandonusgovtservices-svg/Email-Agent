import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request, AuthorizedSession

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"


def get_google_services():
    """Return (gmail_session, calendar_session) as AuthorizedSession objects.

    Uses requests transport to avoid httplib2 SSL issues in proxy environments.
    On first run, triggers browser OAuth flow or manual code exchange.
    """
    creds = _load_or_refresh_credentials()

    gmail_session = AuthorizedSession(creds)
    calendar_session = AuthorizedSession(creds)
    return gmail_session, calendar_session


def _load_or_refresh_credentials() -> Credentials:
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            t = json.load(f)
        creds = Credentials(
            token=t.get("token"),
            refresh_token=t.get("refresh_token"),
            token_uri=t.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=t.get("client_id"),
            client_secret=t.get("client_secret"),
            scopes=t.get("scopes"),
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_credentials(creds)
        else:
            raise RuntimeError(
                "token.json is missing or invalid. "
                "Run the OAuth flow to generate it."
            )

    return creds


def _save_credentials(creds: Credentials) -> None:
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
