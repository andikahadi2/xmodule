import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.clipper.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.models  # noqa: F401 ensure all tables are registered on Base.metadata
from app.core.database import Base
from app.models.social_account import SocialAccount
from app.providers.social.base import AccountProfile, OAuthTokens, SocialMediaProvider
from app.services import social_service

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


class FakeTikTokProvider(SocialMediaProvider):
    name = "tiktok"

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        return f"https://fake.tiktok/authorize?state={state}"

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        return OAuthTokens(
            access_token=f"access-{code}",
            refresh_token="refresh-1",
            expires_in=3600,
            scope="user.info.basic,video.upload",
            open_id="user-123",
        )

    def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        return OAuthTokens(
            access_token="access-refreshed",
            refresh_token=refresh_token,
            expires_in=3600,
            scope="user.info.basic,video.upload",
            open_id="user-123",
        )

    def get_profile(self, access_token: str) -> AccountProfile:
        return AccountProfile(external_id="user-123", display_name="Test Creator")

    def upload_video(self, access_token: str, video_path: str, caption: str) -> str:
        return "publish-abc"


@pytest.fixture
def db():
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


def test_connect_account_creates_new_record(db, monkeypatch):
    monkeypatch.setattr(social_service, "get_social_provider", lambda name: FakeTikTokProvider())

    account = social_service.connect_account(db, "tiktok", "auth-code-1", "http://localhost/callback")

    assert account.platform == "tiktok"
    assert account.external_id == "user-123"
    assert account.display_name == "Test Creator"
    assert account.access_token == "access-auth-code-1"
    assert account.status == "connected"


def test_connect_account_reconnect_updates_existing_record(db, monkeypatch):
    monkeypatch.setattr(social_service, "get_social_provider", lambda name: FakeTikTokProvider())

    first = social_service.connect_account(db, "tiktok", "code-a", "http://localhost/callback")
    second = social_service.connect_account(db, "tiktok", "code-b", "http://localhost/callback")

    assert first.id == second.id
    assert second.access_token == "access-code-b"
    accounts = social_service.list_accounts(db)
    assert len(accounts) == 1


def test_connect_account_survives_concurrent_insert_race(db, monkeypatch):
    monkeypatch.setattr(social_service, "get_social_provider", lambda name: FakeTikTokProvider())

    # Simulate another request winning the race and inserting the row first,
    # after our connect_account's own SELECT already ran (see IntegrityError fallback).
    original_find = social_service._find_account
    call_count = {"n": 0}

    def find_that_misses_once_then_hits(db_, platform, external_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            db_.add(SocialAccount(
                platform=platform,
                external_id=external_id,
                display_name="Racer",
                access_token="stale",
                scope="user.info.basic",
            ))
            db_.commit()
            return None
        return original_find(db_, platform, external_id)

    monkeypatch.setattr(social_service, "_find_account", find_that_misses_once_then_hits)

    account = social_service.connect_account(db, "tiktok", "code-a", "http://localhost/callback")

    assert account.access_token == "access-code-a"
    accounts = social_service.list_accounts(db)
    assert len(accounts) == 1


def test_publish_to_account_returns_publish_id(db, monkeypatch):
    monkeypatch.setattr(social_service, "get_social_provider", lambda name: FakeTikTokProvider())
    account = social_service.connect_account(db, "tiktok", "code-a", "http://localhost/callback")

    publish_id = social_service.publish_to_account(db, account, "/tmp/video.mp4", "caption text")

    assert publish_id == "publish-abc"
