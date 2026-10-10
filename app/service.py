"""The chatbot's brain, kept separate from the web framework so it is easy to test."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .llm import LLMClient, LLMError
from .prompt import WHATSAPP, build_messages, fallback_reply
from .ratelimit import RateLimiter
from .retrieval import KnowledgeBase

log = logging.getLogger("chatbot")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
MAX_MESSAGE_CHARS = 500

GREETING = ("Hi! 👋 I'm Osbert's assistant. Ask me about his skills, projects and services, "
            "or about Virtual Room Beddings & Comfort products and how to order.")
_GREETINGS = {"hi", "hello", "hey", "hallo", "hiya", "good morning", "good afternoon", "good evening",
              "morning", "oli ota", "agandi", "how are you", "hi there", "hello there", "yo", "sup"}


def load_dotenv(path: Path) -> None:
    """Reads KEY=value lines from a local .env file (for testing on your computer).
    Real environment variables, like the ones set on Render, always win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def is_greeting(message: str) -> bool:
    text = "".join(ch for ch in message.lower() if ch.isalnum() or ch == " ").strip()
    return text in _GREETINGS


class ChatService:
    def __init__(self, llm: LLMClient | None, kb: KnowledgeBase | None = None,
                 limiter: RateLimiter | None = None):
        self.kb = kb or KnowledgeBase(KNOWLEDGE_DIR)
        self.llm = llm
        self.limiter = limiter or RateLimiter()

    @classmethod
    def from_env(cls) -> "ChatService":
        load_dotenv(KNOWLEDGE_DIR.parent / ".env")
        key = os.getenv("LLM_API_KEY", "").strip()
        llm = None
        if key:
            llm = LLMClient(
                api_key=key,
                base_url=os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
                model=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            )
        else:
            log.warning("LLM_API_KEY not set: running in test mode (replies come straight from the knowledge files)")
        return cls(llm)

    async def answer(self, message: str, history: list[dict], client_id: str) -> dict:
        message = (message or "").strip()
        if not message:
            return {"reply": "Please type a question 🙂", "sources": []}
        if len(message) > MAX_MESSAGE_CHARS:
            return {"reply": f"That message is a bit long. Please keep it under {MAX_MESSAGE_CHARS} characters.", "sources": []}
        if not self.limiter.allow(client_id):
            return {"reply": f"You've sent a lot of messages. Please wait a few minutes, or chat on WhatsApp: {WHATSAPP}",
                    "sources": [], "limited": True}

        if is_greeting(message):
            return {"reply": GREETING, "sources": []}

        chunks = self.kb.search(message)
        sources = [c.title for c, _ in chunks]
        if self.llm is None:
            return {"reply": fallback_reply(chunks), "sources": sources, "mode": "test"}
        try:
            reply = await self.llm.chat(build_messages(message, history or [], chunks))
        except LLMError as e:
            log.error("AI call failed: %s", e)
            reply = fallback_reply(chunks)
        return {"reply": reply, "sources": sources}
