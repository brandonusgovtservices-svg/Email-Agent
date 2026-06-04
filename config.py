import os

ROBINHOOD_MCP_URL = "https://agent.robinhood.com/mcp/trading"
CLAUDE_MODEL = "claude-sonnet-4-6"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
TRADING_EMAIL_QUERY = os.getenv("TRADING_EMAIL_QUERY", "is:unread subject:TRADE label:inbox")
AGENT_PROCESSED_LABEL = "agent-processed"
MAX_AGENT_TURNS = 20
