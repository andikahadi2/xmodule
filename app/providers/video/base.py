from abc import ABC, abstractmethod
from dataclasses import dataclass


class VideoProviderError(Exception):
    pass


@dataclass
class VideoResult:
    url: str
    source: str
    duration: float
    license_info: str | None = None


class VideoProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, count: int = 1) -> list[VideoResult]:
        """Return up to `count` videos matching query. Raises VideoProviderError on failure."""
