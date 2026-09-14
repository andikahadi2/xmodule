from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.product import ProductCreate
from app.services import product_service

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"active": "home"})


@router.get("/affiliate", response_class=HTMLResponse)
def affiliate_dashboard(request: Request, db: Session = Depends(get_db)):
    products = product_service.list_products(db)
    return templates.TemplateResponse(
        request, "products.html", {"products": products, "active": "affiliate"}
    )


@router.post("/products", response_class=HTMLResponse)
def add_product(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    affiliate_url: str = Form(...),
    description: str = Form(""),
    category: str = Form(""),
    db: Session = Depends(get_db),
):
    product_service.create_product(
        db,
        ProductCreate(
            name=name,
            price=price,
            affiliate_url=affiliate_url,
            description=description or None,
            category=category or None,
        ),
    )
    products = product_service.list_products(db)
    return templates.TemplateResponse(
        request, "_product_rows.html", {"products": products}
    )


@router.delete("/products/{product_id}", response_class=HTMLResponse)
def remove_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = product_service.get_product(db, product_id)
    if product is not None:
        product_service.delete_product(db, product)
    products = product_service.list_products(db)
    return templates.TemplateResponse(
        request, "_product_rows.html", {"products": products}
    )
