import ipaddress
import socket
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import Content
from app.models.media import MediaAsset
from app.providers.image import ImageProviderError, LocalImageProvider, PexelsProvider


class UnsafeUrlError(ImageProviderError):
    pass


def _assert_safe_host(url: str) -> None:
    """Block SSRF: refuse non-http(s) schemes and any host resolving to a
    private/loopback/link-local IP. This is checked before each request AND
    each redirect hop, since a public hostname can still resolve to an
    internal address (DNS rebinding / misconfigured internal DNS)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Refusing to fetch non-http(s) URL: {url}")
    if not parsed.hostname:
        raise UnsafeUrlError(f"URL has no hostname: {url}")

    try:
        addr_info = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host {parsed.hostname}: {exc}") from exc

    for *_rest, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeUrlError(f"Refusing to fetch URL resolving to a non-public address: {url} -> {ip}")


def _download(url: str, dest: Path, timeout: float = 20.0, max_redirects: int = 5) -> None:
    current_url = url
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            _assert_safe_host(current_url)
            resp = client.get(current_url)
            if resp.is_redirect:
                current_url = str(resp.next_request.url)
                continue
            resp.raise_for_status()
            with open(dest, "wb") as f:
                f.write(resp.content)
            return
    raise UnsafeUrlError(f"Too many redirects fetching {url}")


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
