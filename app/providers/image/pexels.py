import httpx

from app.core.config import settings
from app.providers.image.base import ImageProvider, ImageProviderError, ImageResult

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


class PexelsProvider(ImageProvider):
    name = "pexels"

    def __init__(self, timeout: float = 15.0, max_retries: int = 1):
        self.timeout = timeout
        self.max_retries = max_retries

    def search(self, query: str, count: int = 1) -> list[ImageResult]:
        if not settings.pexels_api_key:
            raise ImageProviderError("PEXELS_API_KEY is not set")

        headers = {"Authorization": settings.pexels_api_key}
        params = {"query": query, "per_page": count, "orientation": "portrait"}

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.get(
                    PEXELS_SEARCH_URL, headers=headers, params=params, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                return [
                    ImageResult(
                        url=photo["src"]["large"],
                        source="pexels",
                        license_info=f"https://www.pexels.com/photo/{photo['id']}/ (Pexels License, photographer: {photo.get('photographer', 'unknown')})",
                    )
                    for photo in data.get("photos", [])
                ]
            except (httpx.HTTPError, KeyError) as exc:
                last_error = exc

        raise ImageProviderError(f"Pexels request failed: {last_error}") from last_error
