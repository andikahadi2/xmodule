from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    hook: Mapped[str] = mapped_column(String(500))
    angle: Mapped[str] = mapped_column(String(500))
    target_audience: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(50))
    estimated_duration: Mapped[int] = mapped_column(default=30)
    ai_provider: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="generated")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    content = relationship("Content", back_populates="ideas")
