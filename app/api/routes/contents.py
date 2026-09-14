from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.content import Content
from app.providers.ai.base import AIProviderError
from app.schemas.content import ContentIdeaOut, ContentOut, ContentScriptOut
from app.services import content_service, product_service, script_service

router = APIRouter(prefix="/api/contents", tags=["contents"])


def _get_content_or_404(db: Session, content_id: int) -> Content:
    content = db.get(Content, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.get("", response_model=list[ContentOut])
def list_contents(db: Session = Depends(get_db)):
    return list(db.scalars(select(Content).order_by(Content.created_at.desc())))


@router.get("/{content_id}", response_model=ContentOut)
def get_content(content_id: int, db: Session = Depends(get_db)):
    return _get_content_or_404(db, content_id)


@router.post("/generate-ideas/{product_id}", response_model=ContentOut, status_code=201)
def generate_ideas(product_id: int, db: Session = Depends(get_db)):
    product = product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        return content_service.generate_content_ideas(db, product)
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{content_id}/generate-script", response_model=ContentScriptOut, status_code=201)
def generate_script(content_id: int, db: Session = Depends(get_db)):
    content = _get_content_or_404(db, content_id)
    selected_idea = next((i for i in content.ideas if i.status == "selected"), None)
    if selected_idea is None:
        raise HTTPException(status_code=400, detail="Content has no selected idea")
    try:
        return script_service.generate_script(db, content, selected_idea)
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
