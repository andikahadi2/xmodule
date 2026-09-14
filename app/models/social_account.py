from datetime import datetime

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._timestamps import utcnow


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_social_accounts_platform_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(1000), default=None)
    # ponytail: tokens stored plaintext for MVP; add column-level encryption before handling real user accounts beyond your own
    access_token: Mapped[str] = mapped_column(String(2000))
    refresh_token: Mapped[str | None] = mapped_column(String(2000), default=None)
    token_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    scope: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="connected")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
