"""Jerry the mouse agent (LangGraph)."""

from __future__ import annotations

import asyncio
import logging
import os
import ssl

# Handle SSL verification on systems with missing/expired CA certificates for both HTTPS and WebSockets
_orig_create_default_context = ssl.create_default_context


def _unverified_create_default_context(*args, **kwargs):
    ctx = _orig_create_default_context(*args, **kwargs)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


ssl.create_default_context = _unverified_create_default_context
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver

from characters import generate_jerry_prompt

from band import Agent
from band.adapters import LangGraphAdapter, LangGraphAdapterConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    llm = (
        ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), google_api_key=gemini_key)
        if gemini_key
        else ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    )

    # Create adapter with Jerry's character prompt
    adapter = LangGraphAdapter(
        LangGraphAdapterConfig(custom_section=generate_jerry_prompt("Jerry")),
        llm=llm,
        checkpointer=InMemorySaver(),
    )

    logger.info("Jerry is cozy in his hole, watching for Tom...")
    agent_id = os.getenv("JERRY_AGENT_ID")
    api_key = os.getenv("JERRY_API_KEY")

    if agent_id and api_key:
        agent_cm = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
    else:
        agent_cm = Agent.from_config("jerry_agent", adapter=adapter)

    async with agent_cm as agent:
        await agent.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
