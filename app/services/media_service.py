import uuid
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import Content
from app.models.media import MediaAsset
from app.providers.image import ImageProviderError, LocalImageProvider, PexelsProvider


def _download(url: str, dest: Path, timeout: float = 20.0) -> None:
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)


DEFAULT_IMAGE_COUNT = 4


def generate_media(db: Session, content: Content, count: int = DEFAULT_IMAGE_COUNT) -> list[MediaAsset]:
    product = content.product
    query = product.category or product.name

    results = []
    if product.image_url:
        results.extend(LocalImageProvider(product.image_url).search(query, count=1))

    remaining = count - len(results)
    if remaining > 0:
        try:
            results.extend(PexelsProvider().search(query, count=remaining))
        except ImageProviderError:
            if not results:
                raise

    if not results:
        raise ImageProviderError("No images available for this product")

    images_dir = Path(settings.storage_path) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    assets = []
    for result in results:
        filename = f"{content.id}_{uuid.uuid4().hex}.jpg"
        dest = images_dir / filename
        _download(result.url, dest)

        asset = MediaAsset(
            content_id=content.id,
            provider=result.source,
            query=query,
            file_path=str(dest),
            source_url=result.url,
            license_info=result.license_info,
        )
        db.add(asset)
        assets.append(asset)

    content.status = "ASSETS_GENERATED"
    db.commit()
    for asset in assets:
        db.refresh(asset)
    return assets
