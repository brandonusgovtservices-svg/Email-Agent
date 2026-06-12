"""Robinhood MCP trading agent — parses email instructions and executes equities trades."""

import asyncio
import json
import os

from anthropic import AsyncAnthropic
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ROBINHOOD_MCP_URL = "https://agent.robinhood.com/mcp/trading"
CLAUDE_MODEL = "claude-sonnet-4-6"
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
TRADING_EMAIL_QUERY = os.getenv("TRADING_EMAIL_QUERY", "is:unread subject:TRADE label:inbox")
MAX_AGENT_TURNS = 20

SYSTEM_PROMPT = """You are an AI trading agent that processes email trading instructions and executes trades on Robinhood.

When given an email containing trading instructions, you should:
1. Parse the instruction carefully: stock symbol, action (BUY/SELL), and quantity or dollar amount.
2. Check the current portfolio state and available buying power using the Robinhood tools.
3. Validate the trade is feasible given account limits and available funds.
4. Execute the trade if it is unambiguous and within safe limits.
5. Summarize what was done — or clearly explain why the trade was not executed.

Rules:
- If the instruction is ambiguous, do NOT execute any trade.
- Never exceed available buying power.
- Only trade equities (stocks) during beta — no options, crypto, futures, or event contracts.
- Always confirm order details before placing (preview first if the tool supports it).

End your response with a concise plain-text summary suitable for an email reply."""


class TradingAgent:
    def __init__(self):
        self.claude = AsyncAnthropic()
        self.token = os.environ["ROBINHOOD_MCP_TOKEN"]

    async def run(self):
        from gmail_client import GmailClient

        gmail = GmailClient()
        while True:
            try:
                threads = gmail.search_threads(TRADING_EMAIL_QUERY)
                if threads:
                    print(f"[trading] {len(threads)} pending instruction(s)")
                for thread in threads:
                    await self._handle_thread(thread, gmail)
            except Exception as exc:
                print(f"[trading error] {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _handle_thread(self, thread: dict, gmail):
        thread_id = thread["id"]
        email = gmail.get_thread_content(thread_id)
        if not email:
            return
        print(f"[trading] processing: {email['subject']}")
        try:
            result = await self.process_email(email)
            gmail.send_reply(email, result)
        except Exception as exc:
            gmail.send_reply(
                email,
                f"Your trading instruction could not be processed.\n\nError: {exc}",
            )
        finally:
            gmail.mark_processed(thread_id)

    async def process_email(self, email: dict) -> str:
        async with streamablehttp_client(
            ROBINHOOD_MCP_URL,
            headers={"Authorization": f"Bearer {self.token}"},
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                tools = [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema,
                    }
                    for t in tools_response.tools
                ]
                return await self._agent_loop(email, session, tools)

    async def _agent_loop(self, email: dict, session: ClientSession, tools: list) -> str:
        messages = [
            {
                "role": "user",
                "content": (
                    f"Process this trading instruction email:\n\n"
                    f"From: {email['from']}\n"
                    f"Subject: {email['subject']}\n\n"
                    f"{email['body']}"
                ),
            }
        ]

        for _ in range(MAX_AGENT_TURNS):
            response = await self.claude.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                return _extract_text(response.content)
            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                call_result = await session.call_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": _serialize_content(call_result.content),
                        "is_error": call_result.isError,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        return _extract_text(messages[-1].get("content", []))


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.text for b in content if hasattr(b, "text"))
    return str(content)


def _serialize_content(content) -> str:
    if not content:
        return ""
    return "\n".join(item.text if hasattr(item, "text") else str(item) for item in content)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()
    if not os.getenv("ROBINHOOD_MCP_TOKEN"):
        print("ROBINHOOD_MCP_TOKEN is required. See .env.example.")
        sys.exit(1)
    asyncio.run(TradingAgent().run())
