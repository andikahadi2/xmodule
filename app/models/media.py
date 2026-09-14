from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    provider: Mapped[str] = mapped_column(String(50))
    query: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    source_url: Mapped[str] = mapped_column(String(1000))
    license_info: Mapped[str | None] = mapped_column(String(1000), default=None)
    status: Mapped[str] = mapped_column(String(50), default="ready")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    content = relationship("Content", back_populates="media_assets")
