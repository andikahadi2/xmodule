from abc import ABC, abstractmethod


class AIProviderError(Exception):
    pass


class AIProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        """Return the model's text completion for prompt. Raises AIProviderError on failure."""
