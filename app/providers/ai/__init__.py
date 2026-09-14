from app.providers.ai.base import AIProvider
from app.providers.ai.ollama import OllamaProvider
from app.providers.ai.openrouter import OpenRouterProvider

__all__ = ["AIProvider", "OllamaProvider", "OpenRouterProvider"]


def get_ai_provider(name: str) -> AIProvider:
    if name == "openrouter":
        return OpenRouterProvider()
    if name == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown AI provider: {name}")
