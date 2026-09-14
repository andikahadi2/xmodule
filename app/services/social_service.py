from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models._timestamps import utcnow
from app.models.social_account import SocialAccount
from app.providers.social import get_social_provider


def _expiry_at(expires_in: int) -> datetime | None:
    # Stored naive (DB column has no timezone) so it compares cleanly against utcnow().replace(tzinfo=None).
    if not expires_in:
        return None
    return (utcnow() + timedelta(seconds=expires_in)).replace(tzinfo=None)


def list_accounts(db: Session) -> list[SocialAccount]:
    return list(db.scalars(select(SocialAccount).order_by(SocialAccount.created_at.desc())))


def get_account(db: Session, account_id: int) -> SocialAccount | None:
    return db.get(SocialAccount, account_id)


def get_authorize_url(platform: str, state: str, redirect_uri: str) -> str:
    provider = get_social_provider(platform)
    return provider.get_authorize_url(state, redirect_uri)


def _find_account(db: Session, platform: str, external_id: str) -> SocialAccount | None:
    return db.scalar(
        select(SocialAccount).where(
            SocialAccount.platform == platform, SocialAccount.external_id == external_id
        )
    )


def connect_account(db: Session, platform: str, code: str, redirect_uri: str) -> SocialAccount:
    provider = get_social_provider(platform)
    tokens = provider.exchange_code(code, redirect_uri)
    profile = provider.get_profile(tokens.access_token)

    existing = _find_account(db, platform, profile.external_id)
    account = existing or SocialAccount(platform=platform, external_id=profile.external_id)

    account.display_name = profile.display_name
    account.avatar_url = profile.avatar_url
    account.access_token = tokens.access_token
    account.refresh_token = tokens.refresh_token
    account.token_expires_at = _expiry_at(tokens.expires_in)
    account.scope = tokens.scope
    account.status = "connected"

    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        # Concurrent connect for the same (platform, external_id) raced us — the other
        # request already inserted the row; fall back to updating it instead of erroring out.
        db.rollback()
        account = _find_account(db, platform, profile.external_id)
        if account is None:
            raise
        account.display_name = profile.display_name
        account.avatar_url = profile.avatar_url
        account.access_token = tokens.access_token
        account.refresh_token = tokens.refresh_token
        account.token_expires_at = _expiry_at(tokens.expires_in)
        account.scope = tokens.scope
        account.status = "connected"
        db.commit()

    db.refresh(account)
    return account


def disconnect_account(db: Session, account: SocialAccount) -> None:
    db.delete(account)
    db.commit()


def _ensure_fresh_token(db: Session, account: SocialAccount) -> str:
    if account.token_expires_at and account.token_expires_at <= utcnow().replace(tzinfo=None) and account.refresh_token:
        provider = get_social_provider(account.platform)
        tokens = provider.refresh_tokens(account.refresh_token)
        account.access_token = tokens.access_token
        account.refresh_token = tokens.refresh_token or account.refresh_token
        account.token_expires_at = _expiry_at(tokens.expires_in)
        db.commit()
    return account.access_token


def publish_to_account(db: Session, account: SocialAccount, video_path: str, caption: str) -> str:
    provider = get_social_provider(account.platform)
    access_token = _ensure_fresh_token(db, account)
    return provider.upload_video(access_token, video_path, caption)
