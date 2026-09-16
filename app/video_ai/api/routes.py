import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.video_ai.models.job import VideoAiJob
from app.video_ai.schemas.job import VideoAiJobOut
from app.video_ai.services import video_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video-ai", tags=["video-ai"])

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac"}


def _save_uploaded_music(file: UploadFile) -> str:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {ext}")

    uploads_dir = Path(settings.storage_path) / "music" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest = uploads_dir / f"{uuid.uuid4().hex}{ext}"
    with open(dest, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            f.write(chunk)
    return str(dest)


def _get_job_or_404(db: Session, job_id: int) -> VideoAiJob:
    job = db.get(VideoAiJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Video AI job not found")
    return job


def _process_job_in_background(job_id: int) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.get(VideoAiJob, job_id)
        if job is not None:
            video_ai_service.process_job(db, job)
    except Exception:
        logger.exception("Unhandled error processing video AI job %s in background", job_id)
        db.rollback()
        job = db.get(VideoAiJob, job_id)
        if job is not None and job.status not in ("failed", "completed", "completed_with_errors"):
            job.status = "failed"
            job.error = "Internal error during processing; check server logs"
            db.commit()
    finally:
        db.close()


@router.post("/jobs", response_model=VideoAiJobOut, status_code=201)
def create_job(
    background_tasks: BackgroundTasks,
    query: str = Form(..., min_length=1, max_length=500),
    clip_count: int = Form(default=10, ge=1, le=30),
    music_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    uploaded_music_path = _save_uploaded_music(music_file) if music_file and music_file.filename else None
    job = video_ai_service.create_job(
        db, query=query, clip_count=clip_count, uploaded_music_path=uploaded_music_path
    )
    background_tasks.add_task(_process_job_in_background, job.id)
    return job


@router.get("/jobs", response_model=list[VideoAiJobOut])
def list_jobs(db: Session = Depends(get_db)):
    return list(db.scalars(select(VideoAiJob).order_by(VideoAiJob.created_at.desc())))


@router.get("/jobs/{job_id}", response_model=VideoAiJobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return _get_job_or_404(db, job_id)
