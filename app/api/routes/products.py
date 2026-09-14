from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/api/products", tags=["products"])


def _get_product_or_404(db: Session, product_id: int):
    product = product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return product_service.list_products(db)


@router.post("", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    return product_service.create_product(db, data)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return _get_product_or_404(db, product_id)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    product = _get_product_or_404(db, product_id)
    return product_service.update_product(db, product, data)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = _get_product_or_404(db, product_id)
    product_service.delete_product(db, product)
