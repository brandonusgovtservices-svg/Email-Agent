import asyncio
import json
import os

from anthropic import AsyncAnthropic
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config import (
    CLAUDE_MODEL,
    MAX_AGENT_TURNS,
    POLL_INTERVAL_SECONDS,
    ROBINHOOD_MCP_URL,
    TRADING_EMAIL_QUERY,
)
from gmail_client import GmailClient

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


class EmailTradingAgent:
    def __init__(self):
        self.claude = AsyncAnthropic()
        self.gmail = GmailClient()
        self.robinhood_token = os.environ["ROBINHOOD_MCP_TOKEN"]

    async def run(self):
        while True:
            try:
                await self.process_pending_emails()
            except Exception as exc:
                print(f"[error] {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def process_pending_emails(self):
        threads = self.gmail.search_threads(TRADING_EMAIL_QUERY)
        if not threads:
            return
        print(f"[info] {len(threads)} pending trading instruction(s)")
        for thread in threads:
            await self._handle_thread(thread)

    async def _handle_thread(self, thread: dict):
        thread_id = thread["id"]
        email = self.gmail.get_thread_content(thread_id)
        if not email:
            return
        print(f"[info] processing thread {thread_id}: {email['subject']}")
        try:
            result = await self._run_trading_agent(email)
            self.gmail.send_reply(email, result)
        except Exception as exc:
            print(f"[error] thread {thread_id}: {exc}")
            self.gmail.send_reply(
                email,
                f"Your trading instruction could not be processed.\n\nError: {exc}",
            )
        finally:
            self.gmail.mark_processed(thread_id)

    async def _run_trading_agent(self, email: dict) -> str:
        async with streamablehttp_client(
            ROBINHOOD_MCP_URL,
            headers={"Authorization": f"Bearer {self.robinhood_token}"},
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

    async def _agent_loop(
        self, email: dict, session: ClientSession, tools: list
    ) -> str:
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
                        "content": _serialize_mcp_content(call_result.content),
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


def _serialize_mcp_content(content) -> str:
    if not content:
        return ""
    parts = []
    for item in content:
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts)
