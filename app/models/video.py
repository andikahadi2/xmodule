from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    file_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    width: Mapped[int] = mapped_column(default=1080)
    height: Mapped[int] = mapped_column(default=1920)
    duration: Mapped[float | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    error: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    content = relationship("Content", back_populates="videos")
