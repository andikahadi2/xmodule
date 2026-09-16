from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.video_ai.api.routes import _process_job_in_background, _save_uploaded_music
from app.video_ai.models.job import VideoAiJob
from app.video_ai.services import video_ai_service

router = APIRouter(tags=["video-ai-page"])
templates = Jinja2Templates(directory="app/templates")


def _storage_url(file_path: str) -> str:
    relative = Path(file_path).relative_to(settings.storage_path).as_posix()
    return f"/storage-files/{relative}"


templates.env.filters["storage_url"] = _storage_url


@router.get("/video-ai", response_class=HTMLResponse)
def video_ai_page(request: Request):
    return templates.TemplateResponse(request, "video_ai.html", {"active": "video-ai"})


@router.get("/api/video-ai/jobs/render", response_class=HTMLResponse)
def render_jobs(request: Request, db: Session = Depends(get_db)):
    jobs = list(db.scalars(select(VideoAiJob).order_by(VideoAiJob.created_at.desc())))
    return templates.TemplateResponse(request, "_video_ai_jobs.html", {"jobs": jobs})


@router.post("/api/video-ai/jobs/create", response_class=HTMLResponse)
def create_job_html(
    request: Request,
    background_tasks: BackgroundTasks,
    query: str = Form(...),
    clip_count: int = Form(10),
    music_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    uploaded_music_path = _save_uploaded_music(music_file) if music_file and music_file.filename else None
    job = video_ai_service.create_job(
        db, query=query, clip_count=clip_count, uploaded_music_path=uploaded_music_path
    )
    background_tasks.add_task(_process_job_in_background, job.id)
    return templates.TemplateResponse(request, "_video_ai_job_card.html", {"job": job})


@router.get("/api/video-ai/jobs/{job_id}/render", response_class=HTMLResponse)
def render_job(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(VideoAiJob, job_id)
    if job is None:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "_video_ai_job_card.html", {"job": job})
