from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    price: float
    original_price: float | None = None
    affiliate_url: str
    image_url: str | None = None
    category: str | None = None
    commission: float | None = None
    rating: float | None = None
    sales_count: int | None = None
    source: str = "manual"
    status: str = "active"


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    original_price: float | None = None
    affiliate_url: str | None = None
    image_url: str | None = None
    category: str | None = None
    commission: float | None = None
    rating: float | None = None
    sales_count: int | None = None
    status: str | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
