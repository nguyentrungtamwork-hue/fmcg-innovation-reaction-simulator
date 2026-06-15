"""Thin wrapper around an OpenAI-compatible chat-completions endpoint.

Abstracted so we can swap providers (OpenAI, Anthropic via proxy, Qwen, local)
without touching service code. Phase 3 only needs the JSON-mode call.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import get_settings


class LLMNotConfigured(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        s = get_settings()
        self.api_key = api_key if api_key is not None else s.openai_api_key
        self.base_url = (base_url or s.openai_base_url).rstrip("/")
        self.model = model or s.openai_model
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def chat_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Call chat completions in JSON mode and return parsed JSON."""
        if not self.configured:
            raise LLMNotConfigured("OPENAI_API_KEY is not set")
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
