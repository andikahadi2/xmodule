from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    status: Mapped[str] = mapped_column(String(50), default="IDEA")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    product = relationship("Product")
    ideas = relationship("ContentIdea", back_populates="content", cascade="all, delete-orphan")
    scripts = relationship("ContentScript", back_populates="content", cascade="all, delete-orphan")
    media_assets = relationship("MediaAsset", back_populates="content", cascade="all, delete-orphan")
    audio_assets = relationship("AudioAsset", back_populates="content", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="content", cascade="all, delete-orphan")
