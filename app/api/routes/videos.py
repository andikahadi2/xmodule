from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.content import Content
from app.providers.image import ImageProviderError
from app.providers.tts import TTSProviderError
from app.services import audio_service, media_service, video_service

router = APIRouter(prefix="/api/contents", tags=["videos"])


def _get_content_or_404(db: Session, content_id: int) -> Content:
    content = db.get(Content, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/{content_id}/generate-media", status_code=201)
def generate_media(content_id: int, db: Session = Depends(get_db)):
    content = _get_content_or_404(db, content_id)
    try:
        assets = media_service.generate_media(db, content)
    except ImageProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [{"id": a.id, "file_path": a.file_path, "provider": a.provider} for a in assets]


@router.post("/{content_id}/generate-audio", status_code=201)
async def generate_audio(content_id: int, db: Session = Depends(get_db)):
    content = _get_content_or_404(db, content_id)
    if not content.scripts:
        raise HTTPException(status_code=400, detail="Content has no script yet")
    try:
        asset = await audio_service.generate_audio(db, content, content.scripts[-1])
    except TTSProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"id": asset.id, "file_path": asset.file_path, "duration": asset.duration}


@router.post("/{content_id}/generate-video", status_code=201)
def generate_video(content_id: int, db: Session = Depends(get_db)):
    content = _get_content_or_404(db, content_id)
    try:
        video = video_service.generate_video(db, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if video.status == "failed":
        raise HTTPException(status_code=500, detail=video.error)
    return {"id": video.id, "file_path": video.file_path, "status": video.status, "duration": video.duration}
