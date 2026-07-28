"""Web browsing tool — runs a browser-use sub-agent to research something on the open web."""

import asyncio
import os

from browser_use import Agent, BrowserProfile
from browser_use.llm.anthropic.chat import ChatAnthropic

BROWSE_MODEL = os.getenv("BROWSE_MODEL", "claude-sonnet-4-5")
MAX_STEPS = 25


def browse_web(task: str) -> dict:
    async def _run():
        agent = Agent(
            task=task,
            llm=ChatAnthropic(model=BROWSE_MODEL),
            browser_profile=BrowserProfile(headless=True),
        )
        return await agent.run(max_steps=MAX_STEPS)

    history = asyncio.run(_run())

    return {
        "result": history.final_result() or "",
        "success": history.is_successful(),
        "visited_urls": history.urls(),
    }
