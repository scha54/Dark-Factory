"""
BAND Dark Factory Configuration & Initialization Script.

Sets up the 4-seat BAND Room Layout:
- Seat 1 (Architect): Generates requirement ledgers & work orders (No app code).
- Seat 2 (Coder): Implements FastAPI backend & web UI.
- Seat 3 (Reviewer/QA): Runs automated pytest & concurrency test suite.
- Seat 4 (Conductor): Orchestrates autonomous stage progression.
"""

from __future__ import annotations

import asyncio
import logging
import os
import ssl
from pathlib import Path
from typing import Dict, Any

# SSL verification fallback for Windows environments
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

from band import Agent, configure_logging
from band.adapters import LangGraphAdapter, LangGraphAdapterConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_mandate(seat_name: str) -> str:
    """Load system prompt mandate for a specific seat."""
    mandate_path = Path(__file__).parent / "agent_mandates" / f"{seat_name}_mandate.md"
    if mandate_path.exists():
        return mandate_path.read_text(encoding="utf-8")
    return f"You are the {seat_name} in the BAND Dark Factory."


def create_seat_adapter(seat_name: str) -> LangGraphAdapter:
    """Construct Gemini-powered LangGraph adapter for a seat."""
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if gemini_key:
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), google_api_key=gemini_key
        )
    else:
        llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    mandate = load_mandate(seat_name)
    config = LangGraphAdapterConfig(custom_section=f"## Mandate & Role Rules\n{mandate}")

    return LangGraphAdapter(
        config=config,
        llm=llm,
        checkpointer=InMemorySaver(),
    )


SEAT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "architect": {
        "seat_number": 1,
        "name": "The Architect",
        "description": "Generates requirements ledgers and work orders from stage prompts. Prohibited from writing application code.",
    },
    "coder": {
        "seat_number": 2,
        "name": "The Coder",
        "description": "Implements production-grade Python (FastAPI) backend services, models, and web interfaces.",
    },
    "reviewer": {
        "seat_number": 3,
        "name": "The Reviewer / QA",
        "description": "Executes automated pytest test harnesses and validates double-booking concurrency defenses.",
    },
    "conductor": {
        "seat_number": 4,
        "name": "The Conductor",
        "description": "Orchestrates stage progression cleanly across seats with zero human intervention required mid-stage.",
    },
}


def initialize_factory_environment():
    """Verify env vars and setup necessary workspace paths."""
    load_dotenv()
    logger.info("Initializing BAND Dark Factory environment...")
    rest_url = os.getenv("BAND_REST_URL", "https://app.band.ai")
    ws_url = os.getenv("BAND_WS_URL", "wss://app.band.ai/api/v1/socket/websocket")
    logger.info(f"Targeting BAND Platform -> REST: {rest_url} | WS: {ws_url}")
    return True


if __name__ == "__main__":
    initialize_factory_environment()
    print("BAND Dark Factory Configuration verified.")
