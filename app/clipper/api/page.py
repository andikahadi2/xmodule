from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clipper.api.routes import (
    ALLOWED_EXTENSIONS,
    UploadTooLargeError,
    _process_job_in_background,
    save_upload,
)
from app.clipper.fonts import DEFAULT_SUBTITLE_FONT, SUBTITLE_FONTS
from app.clipper.models.clip import ClipJob
from app.clipper.services import clip_service
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["clipper-page"])
templates = Jinja2Templates(directory="app/templates")


def _storage_url(file_path: str) -> str:
    relative = Path(file_path).relative_to(settings.storage_path).as_posix()
    return f"/storage-files/{relative}"


def _font_label(font_id: str) -> str:
    entry = SUBTITLE_FONTS.get(font_id)
    return entry["label"] if entry else font_id


templates.env.filters["storage_url"] = _storage_url
templates.env.filters["font_label"] = _font_label


@router.get("/clipper", response_class=HTMLResponse)
def clipper_page(request: Request):
    return templates.TemplateResponse(
        request,
        "clipper.html",
        {"active": "clipper", "subtitle_fonts": SUBTITLE_FONTS, "default_subtitle_font": DEFAULT_SUBTITLE_FONT},
    )


@router.get("/api/clipper/jobs/render", response_class=HTMLResponse)
def render_jobs(request: Request, db: Session = Depends(get_db)):
    jobs = list(db.scalars(select(ClipJob).order_by(ClipJob.created_at.desc())))
    return templates.TemplateResponse(request, "_clip_jobs.html", {"jobs": jobs})


@router.post("/api/clipper/jobs/upload", response_class=HTMLResponse)
def upload_job_html(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    segment_seconds: int = Form(120),
    reformat_vertical: bool = Form(False),
    auto_caption: bool = Form(True),
    subtitle_font: str = Form(DEFAULT_SUBTITLE_FONT),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return templates.TemplateResponse(
            request,
            "_clip_upload_error.html",
            {"message": f"Tipe file tidak didukung: {ext}"},
            status_code=400,
        )

    try:
        dest = save_upload(file, ext)
    except UploadTooLargeError as exc:
        return templates.TemplateResponse(
            request,
            "_clip_upload_error.html",
            {"message": str(exc)},
            status_code=413,
        )

    job = clip_service.create_job(
        db,
        source_file_path=str(dest),
        original_filename=file.filename or dest.name,
        segment_seconds=segment_seconds,
        reformat_vertical=reformat_vertical,
        auto_caption=auto_caption,
        subtitle_font=subtitle_font,
    )
    background_tasks.add_task(_process_job_in_background, job.id)

    return templates.TemplateResponse(request, "_clip_job_card.html", {"job": job})


@router.get("/api/clipper/jobs/{job_id}/render", response_class=HTMLResponse)
def render_job(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(ClipJob, job_id)
    if job is None:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "_clip_job_card.html", {"job": job})
