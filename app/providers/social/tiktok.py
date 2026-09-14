import time
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.providers.social.base import (
    AccountProfile,
    OAuthTokens,
    SocialMediaProvider,
    SocialMediaProviderError,
)

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USERINFO_URL = "https://open.tiktokapis.com/v2/user/info/"
INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"

SCOPES = "user.info.basic,video.upload"


class TikTokProvider(SocialMediaProvider):
    """Uses TikTok's official Content Posting API (Inbox/Draft mode — no auto-publish)."""

    name = "tiktok"

    def __init__(self, timeout: float = 30.0, max_retries: int = 1):
        self.timeout = timeout
        self.max_retries = max_retries

    def _client_credentials(self) -> tuple[str, str]:
        if not settings.tiktok_client_key or not settings.tiktok_client_secret:
            raise SocialMediaProviderError("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET is not set")
        return settings.tiktok_client_key, settings.tiktok_client_secret

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        client_key, _ = self._client_credentials()
        params = {
            "client_key": client_key,
            "response_type": "code",
            "scope": SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    def _post_form(self, url: str, data: dict, headers: dict | None = None) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.post(url, data=data, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
        raise SocialMediaProviderError(f"TikTok request to {url} failed: {last_error}") from last_error

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        client_key, client_secret = self._client_credentials()
        data = self._post_form(
            TOKEN_URL,
            {
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if "access_token" not in data:
            raise SocialMediaProviderError(f"TikTok token exchange failed: {data}")
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 0),
            scope=data.get("scope", SCOPES),
            open_id=data.get("open_id"),
        )

    def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        client_key, client_secret = self._client_credentials()
        data = self._post_form(
            TOKEN_URL,
            {
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if "access_token" not in data:
            raise SocialMediaProviderError(f"TikTok token refresh failed: {data}")
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_in=data.get("expires_in", 0),
            scope=data.get("scope", SCOPES),
            open_id=data.get("open_id"),
        )

    def get_profile(self, access_token: str) -> AccountProfile:
        try:
            resp = httpx.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "open_id,display_name,avatar_url"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()["data"]["user"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise SocialMediaProviderError(f"TikTok get_profile failed: {exc}") from exc

        return AccountProfile(
            external_id=data["open_id"],
            display_name=data.get("display_name", "TikTok User"),
            avatar_url=data.get("avatar_url"),
        )

    def upload_video(self, access_token: str, video_path: str, caption: str) -> str:
        import os

        file_size = os.path.getsize(video_path)
        try:
            resp = httpx.post(
                INBOX_INIT_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                        "chunk_size": file_size,
                        "total_chunk_count": 1,
                    }
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            upload_url = data["data"]["upload_url"]
            publish_id = data["data"]["publish_id"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise SocialMediaProviderError(f"TikTok inbox init failed: {exc}") from exc

        try:
            with open(video_path, "rb") as f:
                video_bytes = f.read()
            upload_resp = httpx.put(
                upload_url,
                content=video_bytes,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                },
                timeout=self.timeout * 4,
            )
            upload_resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise SocialMediaProviderError(f"TikTok video upload failed: {exc}") from exc

        return publish_id
