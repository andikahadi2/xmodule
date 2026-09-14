import time

import httpx

from app.core.config import settings
from app.providers.ai.base import AIProvider, AIProviderError


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, timeout: float = 60.0, max_retries: int = 1):
        self.timeout = timeout
        self.max_retries = max_retries

    def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        url = f"{settings.ollama_base_url}/api/generate"

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()["response"]
            except (httpx.HTTPError, KeyError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise AIProviderError(f"Ollama request failed: {last_error}") from last_error
