from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class ContentScript(Base):
    __tablename__ = "content_scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    version: Mapped[int] = mapped_column(default=1)
    script_text: Mapped[str] = mapped_column(String)
    hook: Mapped[str] = mapped_column(String(500))
    cta: Mapped[str] = mapped_column(String(500))
    duration: Mapped[int]
    ai_provider: Mapped[str] = mapped_column(String(50))
    ai_model: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="generated")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    content = relationship("Content", back_populates="scripts")
