import time

import httpx

from app.core.config import settings
from app.providers.video.base import VideoProvider, VideoProviderError, VideoResult

PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"


def _pick_video_file(video: dict) -> dict | None:
    files = [f for f in video.get("video_files", []) if f.get("link")]
    if not files:
        return None
    portrait = [f for f in files if (f.get("height") or 0) > (f.get("width") or 0)]
    candidates = portrait or files
    candidates.sort(key=lambda f: f.get("height") or 0)
    for f in candidates:
        if (f.get("height") or 0) >= 720:
            return f
    return candidates[-1]


class PexelsVideoProvider(VideoProvider):
    name = "pexels"

    def __init__(self, timeout: float = 20.0, max_retries: int = 1):
        self.timeout = timeout
        self.max_retries = max_retries

    def search(self, query: str, count: int = 1) -> list[VideoResult]:
        if not settings.pexels_api_key:
            raise VideoProviderError("PEXELS_API_KEY is not set")

        headers = {"Authorization": settings.pexels_api_key}
        params = {"query": query, "per_page": count, "orientation": "portrait"}

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.get(
                    PEXELS_VIDEO_SEARCH_URL, headers=headers, params=params, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                results = []
                for video in data.get("videos", []):
                    file = _pick_video_file(video)
                    if file is None:
                        continue
                    results.append(
                        VideoResult(
                            url=file["link"],
                            source="pexels",
                            duration=float(video.get("duration") or 0),
                            license_info=f"https://www.pexels.com/video/{video['id']}/ (Pexels License, author: {video.get('user', {}).get('name', 'unknown')})",
                        )
                    )
                return results
            except (httpx.HTTPError, KeyError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise VideoProviderError(f"Pexels video request failed: {last_error}") from last_error
