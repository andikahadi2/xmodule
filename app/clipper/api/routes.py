import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clipper.models.clip import ClipJob
from app.clipper.schemas.clip import ClipJobOut
from app.clipper.services import clip_service
from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clipper", tags=["clipper"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


def _get_job_or_404(db: Session, job_id: int) -> ClipJob:
    job = db.get(ClipJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Clip job not found")
    return job


@router.post("/jobs", response_model=ClipJobOut, status_code=201)
def upload_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    segment_seconds: int = Form(120),
    reformat_vertical: bool = Form(False),
    auto_caption: bool = Form(True),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    uploads_dir = Path(settings.storage_path) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest = uploads_dir / f"{uuid.uuid4().hex}{ext}"
    with open(dest, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            f.write(chunk)

    job = clip_service.create_job(
        db,
        source_file_path=str(dest),
        original_filename=file.filename or dest.name,
        segment_seconds=segment_seconds,
        reformat_vertical=reformat_vertical,
        auto_caption=auto_caption,
    )

    background_tasks.add_task(_process_job_in_background, job.id)
    return job


def _process_job_in_background(job_id: int) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.get(ClipJob, job_id)
        if job is not None:
            clip_service.process_job(db, job)
    except Exception:
        logger.exception("Unhandled error processing clip job %s in background", job_id)
        db.rollback()
        job = db.get(ClipJob, job_id)
        if job is not None and job.status not in ("failed", "completed", "completed_with_errors"):
            job.status = "failed"
            job.error = "Internal error during processing; check server logs"
            db.commit()
    finally:
        db.close()


@router.get("/jobs", response_model=list[ClipJobOut])
def list_jobs(db: Session = Depends(get_db)):
    return list(db.scalars(select(ClipJob).order_by(ClipJob.created_at.desc())))


@router.get("/jobs/{job_id}", response_model=ClipJobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return _get_job_or_404(db, job_id)
