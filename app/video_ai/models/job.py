from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class VideoAiJob(Base):
    __tablename__ = "video_ai_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(500))
    clip_count: Mapped[int] = mapped_column(Integer, default=10)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    output_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    music_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    error: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    clips = relationship("VideoAiClip", back_populates="job", cascade="all, delete-orphan")


class VideoAiClip(Base):
    __tablename__ = "video_ai_clips"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("video_ai_jobs.id"))
    index: Mapped[int] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(String(1000))
    license_info: Mapped[str | None] = mapped_column(String(1000), default=None)
    file_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    job = relationship("VideoAiJob", back_populates="clips")
