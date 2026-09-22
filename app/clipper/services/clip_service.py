import math
from pathlib import Path

from sqlalchemy.orm import Session

from app.clipper.fonts import DEFAULT_SUBTITLE_FONT, FONTS_DIR, font_family
from app.clipper.models.clip import Clip, ClipJob
from app.clipper.services.caption_service import transcribe_to_srt
from app.core.config import settings
from app.utils import ffmpeg


def create_job(
    db: Session,
    project_id: int,
    source_file_path: str,
    original_filename: str,
    mode: str = "auto",
    segment_seconds: int = 120,
    reformat_vertical: bool = False,
    auto_caption: bool = True,
    subtitle_font: str = DEFAULT_SUBTITLE_FONT,
) -> ClipJob:
    job = ClipJob(
        project_id=project_id,
        source_file_path=source_file_path,
        original_filename=original_filename,
        mode=mode,
        segment_seconds=segment_seconds,
        reformat_vertical=reformat_vertical,
        auto_caption=auto_caption,
        subtitle_font=subtitle_font,
        status="uploaded" if mode == "auto" else "draft",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def save_manual_segments(db: Session, job: ClipJob, segments: list[tuple[float, float]]) -> ClipJob:
    """Replace a manual job's planned segments with the given (start, end) list.
    Only valid while the job hasn't been processed yet (status "draft")."""
    for clip in list(job.clips):
        db.delete(clip)
    db.flush()

    for i, (start, end) in enumerate(segments):
        db.add(Clip(job_id=job.id, index=i, start_seconds=start, end_seconds=end, status="planned"))

    db.commit()
    db.refresh(job)
    return job


def _render_clip(job: ClipJob, clip: Clip, clips_dir: Path, temp_dir: Path) -> None:
    """Render one Clip's [start_seconds, end_seconds) segment from the job's
    source video to clip.file_path, transcribing a subtitle first if the job
    has auto_caption on. Sets clip.status/.error/.file_path/.subtitle_path;
    does not commit."""
    length = clip.end_seconds - clip.start_seconds
    try:
        subtitle_path: str | None = None
        output_path = clips_dir / f"job{job.id}_clip{clip.index}.mp4"
        raw_segment_path = temp_dir / f"job{job.id}_clip{clip.index}_raw.mp4"

        ffmpeg.extract_segment(
            job.source_file_path,
            str(raw_segment_path),
            start_seconds=clip.start_seconds,
            duration_seconds=length,
            reformat_vertical=False,
            subtitle_path=None,
        )

        if job.auto_caption:
            srt_text = transcribe_to_srt(str(raw_segment_path))
            if srt_text.strip():
                subtitle_path = temp_dir / f"job{job.id}_clip{clip.index}.srt"
                subtitle_path.write_text(srt_text, encoding="utf-8")
                subtitle_path = str(subtitle_path)

        ffmpeg.extract_segment(
            str(raw_segment_path),
            str(output_path),
            start_seconds=0,
            duration_seconds=length,
            reformat_vertical=job.reformat_vertical,
            subtitle_path=subtitle_path,
            subtitle_font_family=font_family(job.subtitle_font) if subtitle_path else None,
            subtitle_fonts_dir=str(FONTS_DIR) if subtitle_path else None,
            width=settings.default_video_width,
            height=settings.default_video_height,
        )
        raw_segment_path.unlink(missing_ok=True)

        clip.file_path = str(output_path)
        clip.subtitle_path = subtitle_path
        clip.status = "ready"
    except ffmpeg.FFmpegError as exc:
        clip.status = "failed"
        clip.error = str(exc)
    except Exception as exc:
        clip.status = "failed"
        clip.error = f"Unexpected error: {exc}"


def process_job(db: Session, job: ClipJob) -> ClipJob:
    """Auto mode: split the source video into fixed-length segments and render
    each one."""
    try:
        total_duration = ffmpeg.probe_duration_seconds(job.source_file_path)
    except ffmpeg.FFmpegError as exc:
        job.status = "failed"
        job.error = str(exc)
        db.commit()
        db.refresh(job)
        return job

    num_segments = max(math.ceil(total_duration / job.segment_seconds), 1)

    clips_dir = Path(settings.storage_path) / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(settings.storage_path) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    job.status = "processing"
    db.commit()

    for i in range(num_segments):
        start = i * job.segment_seconds
        length = min(job.segment_seconds, total_duration - start)

        clip = Clip(job_id=job.id, index=i, start_seconds=start, end_seconds=start + length, status="processing")
        db.add(clip)
        db.commit()
        db.refresh(clip)

        _render_clip(job, clip, clips_dir, temp_dir)
        db.commit()

    any_failed = any(c.status == "failed" for c in job.clips)
    job.status = "completed_with_errors" if any_failed else "completed"
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job: ClipJob) -> None:
    """Delete a job's row (cascades to its Clip rows) and every file it owns
    on disk: the uploaded source video, each rendered clip, and each subtitle."""
    paths = [Path(job.source_file_path)]
    for clip in job.clips:
        if clip.file_path:
            paths.append(Path(clip.file_path))
        if clip.subtitle_path:
            paths.append(Path(clip.subtitle_path))

    db.delete(job)
    db.commit()

    for path in paths:
        path.unlink(missing_ok=True)


def process_manual_job(db: Session, job: ClipJob) -> ClipJob:
    """Manual mode: render the segments the user already planned via
    save_manual_segments (Clip rows with status "planned")."""
    if not job.clips:
        job.status = "failed"
        job.error = "No segments defined; add at least one segment before processing"
        db.commit()
        db.refresh(job)
        return job

    clips_dir = Path(settings.storage_path) / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(settings.storage_path) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    job.status = "processing"
    db.commit()

    for clip in sorted(job.clips, key=lambda c: c.index):
        clip.status = "processing"
        db.commit()
        _render_clip(job, clip, clips_dir, temp_dir)
        db.commit()

    any_failed = any(c.status == "failed" for c in job.clips)
    job.status = "completed_with_errors" if any_failed else "completed"
    db.commit()
    db.refresh(job)
    return job
