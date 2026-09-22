from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clipper.api.routes import (
    ALLOWED_EXTENSIONS,
    UploadTooLargeError,
    _process_job_in_background,
    _process_manual_job_in_background,
    save_upload,
)
from app.clipper.fonts import DEFAULT_SUBTITLE_FONT, SUBTITLE_FONTS
from app.clipper.models.clip import ClipJob
from app.clipper.services import clip_service, project_service
from app.core.config import settings
from app.core.database import get_db
from app.utils import ffmpeg

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
def clipper_page(request: Request, db: Session = Depends(get_db)):
    projects = project_service.list_projects(db)
    return templates.TemplateResponse(
        request,
        "clipper.html",
        {
            "active": "clipper",
            "subtitle_fonts": SUBTITLE_FONTS,
            "default_subtitle_font": DEFAULT_SUBTITLE_FONT,
            "projects": projects,
        },
    )


@router.get("/clipper/projects/new", response_class=HTMLResponse)
def new_project_page(request: Request):
    return templates.TemplateResponse(request, "clipper_new_project.html", {"active": "clipper"})


@router.post("/clipper/projects/new")
def create_project_page(name: str = Form(...), db: Session = Depends(get_db)):
    name = name.strip()
    if name:
        project_service.create_project(db, name)
    return RedirectResponse(url="/clipper", status_code=303)


@router.get("/clipper/history", response_class=HTMLResponse)
def clipper_history_page(request: Request):
    return templates.TemplateResponse(request, "clipper_history.html", {"active": "clipper-history"})


@router.get("/api/clipper/jobs/render", response_class=HTMLResponse)
def render_jobs(request: Request, db: Session = Depends(get_db)):
    jobs = list(db.scalars(select(ClipJob).order_by(ClipJob.created_at.desc())))
    return templates.TemplateResponse(request, "_clip_jobs.html", {"jobs": jobs})


@router.post("/api/clipper/jobs/upload", response_class=HTMLResponse)
def upload_job_html(
    request: Request,
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
        return templates.TemplateResponse(
            request,
            "_clip_upload_error.html",
            {"message": f"Tipe file tidak didukung: {ext}"},
            status_code=400,
        )
    if mode not in ("auto", "manual"):
        return templates.TemplateResponse(
            request, "_clip_upload_error.html", {"message": "Mode tidak valid"}, status_code=400
        )
    if project_service.get_project(db, project_id) is None:
        return templates.TemplateResponse(
            request, "_clip_upload_error.html", {"message": "Project tidak ditemukan"}, status_code=404
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
        project_id=project_id,
        source_file_path=str(dest),
        original_filename=file.filename or dest.name,
        mode=mode,
        segment_seconds=segment_seconds,
        reformat_vertical=reformat_vertical,
        auto_caption=auto_caption,
        subtitle_font=subtitle_font,
    )

    if mode == "manual":
        return Response(status_code=200, headers={"HX-Redirect": f"/clipper/jobs/{job.id}/edit"})

    background_tasks.add_task(_process_job_in_background, job.id)
    return Response(status_code=200, headers={"HX-Redirect": "/clipper/history"})


@router.get("/api/clipper/jobs/{job_id}/render", response_class=HTMLResponse)
def render_job(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(ClipJob, job_id)
    if job is None:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "_clip_job_row.html", {"job": job})


@router.delete("/api/clipper/jobs/{job_id}/delete", response_class=HTMLResponse)
def delete_job_html(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ClipJob, job_id)
    if job is None:
        return HTMLResponse("", status_code=404)
    clip_service.delete_job(db, job)
    return HTMLResponse("")


@router.get("/clipper/jobs/{job_id}/edit", response_class=HTMLResponse)
def edit_job_page(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(ClipJob, job_id)
    if job is None or job.mode != "manual" or job.status != "draft":
        return HTMLResponse("Job tidak ditemukan atau sudah diproses.", status_code=404)
    try:
        duration = ffmpeg.probe_duration_seconds(job.source_file_path)
    except ffmpeg.FFmpegError as exc:
        return HTMLResponse(f"Gagal membaca video sumber: {exc}", status_code=502)
    return templates.TemplateResponse(
        request, "clipper_edit.html", {"active": "clipper", "job": job, "duration": duration}
    )


@router.post("/api/clipper/jobs/{job_id}/segments", response_class=HTMLResponse)
async def save_job_segments_html(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(ClipJob, job_id)
    if job is None:
        return HTMLResponse("Job tidak ditemukan.", status_code=404)
    if job.mode != "manual" or job.status != "draft":
        return HTMLResponse("Segmen hanya bisa diatur sebelum job diproses.", status_code=400)

    try:
        duration = ffmpeg.probe_duration_seconds(job.source_file_path)
    except ffmpeg.FFmpegError as exc:
        return HTMLResponse(f"Gagal membaca video sumber: {exc}", status_code=502)

    form = await request.form()
    starts = form.getlist("start_seconds")
    ends = form.getlist("end_seconds")
    segments: list[tuple[float, float]] = []
    for raw_start, raw_end in zip(starts, ends):
        try:
            start, end = float(raw_start), float(raw_end)
        except ValueError:
            continue
        if end > start:
            segments.append((start, end))

    error = None
    if not segments:
        error = "Tambahkan minimal satu segmen yang valid (akhir harus setelah awal)."
    else:
        job = clip_service.save_manual_segments(db, job, segments)

    return templates.TemplateResponse(
        request,
        "_clip_edit_segments.html",
        {"job": job, "duration": duration, "error": error},
    )


@router.post("/api/clipper/jobs/{job_id}/process-manual", response_class=HTMLResponse)
def process_manual_job_html(
    request: Request, job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    job = db.get(ClipJob, job_id)
    if job is None:
        return HTMLResponse("Job tidak ditemukan.", status_code=404)
    if job.mode != "manual" or job.status != "draft":
        return HTMLResponse("Job sudah diproses.", status_code=400)
    if not job.clips:
        return HTMLResponse("Tambahkan minimal satu segmen sebelum memproses.", status_code=400)

    background_tasks.add_task(_process_manual_job_in_background, job.id)
    return HTMLResponse(
        '<div style="color: var(--success); font-size: 13px;">Diproses di background. '
        '<a href="/clipper/history">Lihat di History →</a></div>'
    )
