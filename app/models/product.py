from datetime import datetime

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._timestamps import utcnow


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String, default=None)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2), default=None)
    affiliate_url: Mapped[str] = mapped_column(String(1000))
    image_url: Mapped[str | None] = mapped_column(String(1000), default=None)
    category: Mapped[str | None] = mapped_column(String(255), default=None)
    commission: Mapped[float | None] = mapped_column(Numeric(12, 2), default=None)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), default=None)
    sales_count: Mapped[int | None] = mapped_column(default=None)
    source: Mapped[str] = mapped_column(String(100), default="manual")
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
