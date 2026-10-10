"""Calls an AI model through the OpenAI-compatible Chat Completions API.

Works with Google Gemini, Groq, OpenAI and others: just change LLM_BASE_URL and LLM_MODEL.
"""
from __future__ import annotations

import httpx


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 30.0):
        self.api_key = api_key
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.timeout = timeout

    async def chat(self, messages: list[dict]) -> str:
        payload = {"model": self.model, "messages": messages, "temperature": 0.6, "max_tokens": 350}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(self.url, json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise LLMError(f"network error: {e}") from e
        if r.status_code != 200:
            raise LLMError(f"AI service returned {r.status_code}: {r.text[:300]}")
        try:
            return r.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"unexpected response: {r.text[:300]}") from e