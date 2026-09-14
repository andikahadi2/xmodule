from abc import ABC, abstractmethod
from dataclasses import dataclass


class SocialMediaProviderError(Exception):
    pass


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str
    open_id: str | None = None


@dataclass
class AccountProfile:
    external_id: str
    display_name: str
    avatar_url: str | None = None


class SocialMediaProvider(ABC):
    name: str

    @abstractmethod
    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """Return the URL to redirect the user to for OAuth consent."""

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange an OAuth authorization code for tokens."""

    @abstractmethod
    def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token."""

    @abstractmethod
    def get_profile(self, access_token: str) -> AccountProfile:
        """Fetch the connected account's basic profile info."""

    @abstractmethod
    def upload_video(self, access_token: str, video_path: str, caption: str) -> str:
        """Upload a video to the account (draft/inbox, not auto-published). Returns a publish_id."""
