import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clipper.fonts import DEFAULT_SUBTITLE_FONT
from app.clipper.models.clip import ClipJob
from app.clipper.schemas.clip import ClipJobOut, ProjectOut, SegmentIn
from app.clipper.services import clip_service, project_service
from app.core.config import settings
from app.core.database import get_db
from app.utils import ffmpeg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clipper", tags=["clipper"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


class UploadTooLargeError(Exception):
    pass


def _get_job_or_404(db: Session, job_id: int) -> ClipJob:
    job = db.get(ClipJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Clip job not found")
    return job


def save_upload(file: UploadFile, ext: str) -> Path:
    """Stream an uploaded file to storage/uploads, aborting if it exceeds
    MAX_UPLOAD_BYTES. Raises UploadTooLargeError instead of letting an
    unbounded upload fill the disk."""
    uploads_dir = Path(settings.storage_path) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest = uploads_dir / f"{uuid.uuid4().hex}{ext}"

    total = 0
    try:
        with open(dest, "wb") as f:
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise UploadTooLargeError(
                        f"File exceeds max upload size of {settings.max_upload_size_mb}MB"
                    )
                f.write(chunk)
    except UploadTooLargeError:
        dest.unlink(missing_ok=True)
        raise
    return dest


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return project_service.list_projects(db)


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(name: str = Form(...), db: Session = Depends(get_db)):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")
    return project_service.create_project(db, name)


@router.post("/jobs", response_model=ClipJobOut, status_code=201)
def upload_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: int = Form(...),
    mode: str = Form("auto"),
    segment_seconds: int = Form(120),
    reformat_vertical: bool = Form(False),
    auto_caption: bool = Form(True),
    subtitle_font: str = Form(DEFAULT_SUBTITLE_FONT),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    if mode not in ("auto", "manual"):
        raise HTTPException(status_code=400, detail="mode must be 'auto' or 'manual'")
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        dest = save_upload(file, ext)
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    job = clip_service.create_job(
        db,
        project_id=project_id,
        source_file_path=str(dest),
        original_filename=file.filename or dest.name,
        mode=mode,
        segment_seconds=segment_seconds,
        reformat_vertical=reformat_vertical,
        auto_caption=auto_caption,
        subtitle_font=subtitle_font,
    )

    if mode == "auto":
        background_tasks.add_task(_process_job_in_background, job.id)
    return job


@router.get("/jobs/{job_id}/duration")
def get_job_duration(job_id: int, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    try:
        duration = ffmpeg.probe_duration_seconds(job.source_file_path)
    except ffmpeg.FFmpegError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"duration_seconds": duration}


@router.put("/jobs/{job_id}/segments", response_model=ClipJobOut)
def put_job_segments(job_id: int, segments: list[SegmentIn], db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    if job.mode != "manual":
        raise HTTPException(status_code=400, detail="Segments can only be set on a manual-mode job")
    if job.status != "draft":
        raise HTTPException(status_code=400, detail=f"Job already processed (status '{job.status}')")
    if not segments:
        raise HTTPException(status_code=400, detail="At least one segment is required")
    for s in segments:
        if s.end_seconds <= s.start_seconds:
            raise HTTPException(status_code=400, detail="Each segment's end_seconds must be after start_seconds")

    return clip_service.save_manual_segments(db, job, [(s.start_seconds, s.end_seconds) for s in segments])


@router.post("/jobs/{job_id}/process", response_model=ClipJobOut, status_code=202)
def process_manual_job(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    if job.mode != "manual":
        raise HTTPException(status_code=400, detail="Only manual-mode jobs are processed via this endpoint")
    if job.status != "draft":
        raise HTTPException(status_code=400, detail=f"Job already processed (status '{job.status}')")
    if not job.clips:
        raise HTTPException(status_code=400, detail="Add at least one segment before processing")

    background_tasks.add_task(_process_manual_job_in_background, job.id)
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


def _process_manual_job_in_background(job_id: int) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.get(ClipJob, job_id)
        if job is not None:
            clip_service.process_manual_job(db, job)
    except Exception:
        logger.exception("Unhandled error processing manual clip job %s in background", job_id)
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


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    clip_service.delete_job(db, job)
