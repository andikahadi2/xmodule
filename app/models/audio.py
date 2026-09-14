from datetime import datetime

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class AudioAsset(Base):
    __tablename__ = "audio_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    provider: Mapped[str] = mapped_column(String(50))
    voice: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(20))
    file_path: Mapped[str] = mapped_column(String(1000))
    duration: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="ready")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    content = relationship("Content", back_populates="audio_assets")
