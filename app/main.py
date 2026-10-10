"""FastAPI web server for the portfolio chatbot.

Run locally:   uvicorn app.main:app --reload
Then open:     http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .service import ChatService

app = FastAPI(title="KOS Portfolio Chatbot", version="1.0.0")

# Only your website may call this API from a browser.
origins = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS",
    "https://kamukamaosbertl.github.io,http://127.0.0.1:5500,http://localhost:5500",
).split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"])

service = ChatService.from_env()


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=1000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[Turn] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []


def client_ip(request: Request) -> str:
    # Render / most hosts put the real visitor IP first in X-Forwarded-For
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@app.get("/")
def root():
    return {"status": "ok", "message": "KOS chatbot API. POST /chat to talk to it."}


@app.get("/health")
def health():
    return {"status": "ok", "ai": service.llm is not None, "knowledge_sections": len(service.kb.chunks)}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    result = await service.answer(body.message, [t.model_dump() for t in body.history], client_ip(request))
    return ChatResponse(reply=result["reply"], sources=result.get("sources", []))
