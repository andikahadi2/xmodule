import time

import httpx

from app.core.config import settings
from app.providers.ai.base import AIProvider, AIProviderError

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(AIProvider):
    name = "openrouter"

    def __init__(self, timeout: float = 30.0, max_retries: int = 1):
        self.timeout = timeout
        self.max_retries = max_retries

    def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        if not settings.openrouter_api_key:
            raise AIProviderError("OPENROUTER_API_KEY is not set")

        payload = {
            "model": settings.openrouter_model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.post(
                    OPENROUTER_URL, json=payload, headers=headers, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPError, KeyError, IndexError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise AIProviderError(f"OpenRouter request failed: {last_error}") from last_error
