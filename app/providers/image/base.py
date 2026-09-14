from abc import ABC, abstractmethod
from dataclasses import dataclass


class ImageProviderError(Exception):
    pass


@dataclass
class ImageResult:
    url: str
    source: str
    license_info: str | None = None


class ImageProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, count: int = 1) -> list[ImageResult]:
        """Return up to `count` images matching query. Raises ImageProviderError on failure."""
