from app.providers.image.base import ImageProvider, ImageProviderError, ImageResult


class LocalImageProvider(ImageProvider):
    """Uses an already-known image URL (e.g. the product's own image_url). No network call."""

    name = "local"

    def __init__(self, image_url: str | None):
        self.image_url = image_url

    def search(self, query: str, count: int = 1) -> list[ImageResult]:
        if not self.image_url:
            raise ImageProviderError("No local image_url available")
        return [ImageResult(url=self.image_url, source="local", license_info="product-provided")]
