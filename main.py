import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def check_env():
    required = ["ANTHROPIC_API_KEY", "ROBINHOOD_MCP_TOKEN"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in the values.")
        sys.exit(1)
    if not os.path.exists(os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")):
        print("Gmail credentials.json not found.")
        print("Download OAuth credentials from Google Cloud Console and set GMAIL_CREDENTIALS_PATH.")
        sys.exit(1)


async def main():
    check_env()
    from agent import EmailTradingAgent

    agent = EmailTradingAgent()
    print("Email Trading Agent started — polling for trading instructions...")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
