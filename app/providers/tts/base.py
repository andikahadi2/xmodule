from abc import ABC, abstractmethod


class TTSProviderError(Exception):
    pass


class TTSProvider(ABC):
    name: str

    @abstractmethod
    async def synthesize(self, text: str, output_path: str, *, voice: str, language: str) -> float:
        """Write audio for `text` to output_path. Returns duration in seconds. Raises TTSProviderError on failure."""
