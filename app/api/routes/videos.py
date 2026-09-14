import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.content import Content
from app.models.video import Video
from app.providers.image import ImageProviderError
from app.providers.social.base import SocialMediaProviderError
from app.providers.tts import TTSProviderError
from app.services import audio_service, media_service, social_service, video_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contents", tags=["videos"])


def _get_content_or_404(db: Session, content_id: int) -> Content:
    content = db.get(Content, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


def _get_video_or_404(db: Session, video_id: int) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


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


@router.post("/{content_id}/generate-video", status_code=202)
def generate_video(content_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    content = _get_content_or_404(db, content_id)
    try:
        video = video_service.create_pending_video(db, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(_render_video_in_background, video.id)
    return {"id": video.id, "file_path": video.file_path, "status": video.status, "duration": video.duration}


def _render_video_in_background(video_id: int) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video is not None:
            video_service.render_video(db, video)
    except Exception:
        logger.exception("Unhandled error rendering video %s in background", video_id)
        db.rollback()
        video = db.get(Video, video_id)
        if video is not None and video.status == "processing":
            video.status = "failed"
            video.error = "Internal error during render; check server logs"
            db.commit()
    finally:
        db.close()


@router.get("/videos/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = _get_video_or_404(db, video_id)
    return {
        "id": video.id,
        "content_id": video.content_id,
        "file_path": video.file_path,
        "status": video.status,
        "error": video.error,
        "duration": video.duration,
    }


@router.post("/videos/{video_id}/approve")
def approve_video(video_id: int, db: Session = Depends(get_db)):
    video = _get_video_or_404(db, video_id)
    if video.status != "ready":
        raise HTTPException(status_code=400, detail=f"Video must be 'ready' to approve, currently '{video.status}'")
    video.status = "approved"
    db.commit()
    db.refresh(video)
    return {"id": video.id, "status": video.status}


@router.post("/videos/{video_id}/publish/{account_id}")
def publish_video(video_id: int, account_id: int, db: Session = Depends(get_db)):
    video = _get_video_or_404(db, video_id)
    if video.status != "approved":
        raise HTTPException(status_code=400, detail="Video must be approved before publishing")
    if not video.file_path:
        raise HTTPException(status_code=500, detail="Approved video has no file_path; this should not happen")

    account = social_service.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")

    script = video.content.scripts[-1] if video.content.scripts else None
    caption = script.cta if script else ""

    try:
        publish_id = social_service.publish_to_account(db, account, video.file_path, caption)
    except SocialMediaProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    video.status = "published"
    db.commit()
    db.refresh(video)
    return {"id": video.id, "status": video.status, "publish_id": publish_id}
