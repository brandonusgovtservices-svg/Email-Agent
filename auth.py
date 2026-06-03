import os
import json
import webbrowser
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request, AuthorizedSession

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def get_google_services():
    """Return (gmail_session, calendar_session) as AuthorizedSession objects.

    Uses requests transport to avoid httplib2 SSL issues in proxy environments.
    On first run, triggers browser OAuth flow and writes token.json.
    """
    creds = _load_or_refresh_credentials()
    return AuthorizedSession(creds), AuthorizedSession(creds)


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
            creds = _run_oauth_flow()

    return creds


def _run_oauth_flow() -> Credentials:
    """Run browser-based OAuth on local machines, or print a manual URL as fallback."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            "credentials.json not found. Download OAuth 2.0 credentials from "
            "Google Cloud Console (APIs & Services → Credentials) and place the "
            "file in this folder renamed to credentials.json."
        )

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    try:
        # Works on local Mac/Windows — opens a browser tab automatically
        creds = flow.run_local_server(port=0)
    except webbrowser.Error:
        # Headless / server environment — print URL for manual completion
        flow.redirect_uri = "http://localhost"
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        print("\n" + "=" * 60)
        print("MANUAL SIGN-IN REQUIRED")
        print("=" * 60)
        print("\nOpen this URL in your browser:\n")
        print(auth_url)
        print("\nAfter signing in, copy the full redirect URL from your")
        print("browser's address bar (starts with http://localhost?code=...)")
        print("and paste it below.\n")
        redirect_url = input("Paste redirect URL: ").strip()
        from urllib.parse import urlparse, parse_qs
        code = parse_qs(urlparse(redirect_url).query).get("code", [None])[0]
        if not code:
            raise ValueError("Could not find authorization code in the URL you pasted.")
        flow.fetch_token(code=code)
        creds = flow.credentials

    _save_credentials(creds)
    return creds


def _save_credentials(creds: Credentials) -> None:
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
