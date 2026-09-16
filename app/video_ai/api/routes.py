import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.video_ai.models.job import VideoAiJob
from app.video_ai.schemas.job import VideoAiJobOut
from app.video_ai.services import video_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video-ai", tags=["video-ai"])


class VideoAiJobCreate(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    clip_count: int = Field(default=10, ge=1, le=30)


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
    payload: VideoAiJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = video_ai_service.create_job(db, query=payload.query, clip_count=payload.clip_count)
    background_tasks.add_task(_process_job_in_background, job.id)
    return job


@router.get("/jobs", response_model=list[VideoAiJobOut])
def list_jobs(db: Session = Depends(get_db)):
    return list(db.scalars(select(VideoAiJob).order_by(VideoAiJob.created_at.desc())))


@router.get("/jobs/{job_id}", response_model=VideoAiJobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return _get_job_or_404(db, job_id)
