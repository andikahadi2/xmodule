from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clipper.fonts import DEFAULT_SUBTITLE_FONT
from app.core.database import Base
from app.models._timestamps import utcnow


class ClipJob(Base):
    __tablename__ = "clip_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("clipper_projects.id"))
    source_file_path: Mapped[str] = mapped_column(String(1000))
    original_filename: Mapped[str] = mapped_column(String(500))
    mode: Mapped[str] = mapped_column(String(20), default="auto")
    segment_seconds: Mapped[int] = mapped_column(Integer, default=120)
    reformat_vertical: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_caption: Mapped[bool] = mapped_column(Boolean, default=True)
    subtitle_font: Mapped[str] = mapped_column(String(50), default=DEFAULT_SUBTITLE_FONT)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    error: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    project = relationship("Project", back_populates="jobs")
    clips = relationship("Clip", back_populates="job", cascade="all, delete-orphan")


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("clip_jobs.id"))
    index: Mapped[int] = mapped_column(Integer)
    start_seconds: Mapped[float]
    end_seconds: Mapped[float]
    file_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    subtitle_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    job = relationship("ClipJob", back_populates="clips")
