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
from band import Agent, configure_logging
from band.config import load_agent_config
from band.core import AgentToolsProtocol, SimpleAdapter
from band.core.types import PlatformMessage

logger = logging.getLogger(__name__)


class EchoAdapter(SimpleAdapter[list]):
    """Smallest adapter Agent.create accepts. Official Band SDK setup verification adapter."""

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history: list,
        participants_msg: str | None,
        contacts_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        await tools.send_message(f"echo: {msg.content}")


async def verify_setup() -> None:
    load_dotenv()
    configure_logging(root_level="INFO")

    agent_id = os.getenv("TOM_AGENT_ID")
    api_key = os.getenv("TOM_API_KEY")

    if not agent_id or not api_key:
        agent_id, api_key = load_agent_config("tom_agent")

    logger.info("Loaded agent ID: %s", agent_id)
    agent = Agent.create(
        adapter=EchoAdapter(),
        agent_id=agent_id,
        api_key=api_key,
    )

    # start() makes the first authenticated call to the platform.
    await agent.start()
    logger.info("Connected as: %s", agent.agent_name)
    await agent.stop()
    logger.info("Setup verified successfully!")


if __name__ == "__main__":
    asyncio.run(verify_setup())
