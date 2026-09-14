from app.providers.social.base import (
    AccountProfile,
    OAuthTokens,
    SocialMediaProvider,
    SocialMediaProviderError,
)
from app.providers.social.tiktok import TikTokProvider

__all__ = [
    "SocialMediaProvider",
    "SocialMediaProviderError",
    "OAuthTokens",
    "AccountProfile",
    "TikTokProvider",
]


def get_social_provider(name: str) -> SocialMediaProvider:
    if name == "tiktok":
        return TikTokProvider()
    raise ValueError(f"Unknown social media provider: {name}")
