from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._timestamps import utcnow


class Project(Base):
    __tablename__ = "clipper_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    jobs = relationship("ClipJob", back_populates="project")
