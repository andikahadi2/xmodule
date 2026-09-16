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
    source_file_path: str,
    original_filename: str,
    segment_seconds: int = 120,
    reformat_vertical: bool = False,
    auto_caption: bool = True,
    subtitle_font: str = DEFAULT_SUBTITLE_FONT,
) -> ClipJob:
    job = ClipJob(
        source_file_path=source_file_path,
        original_filename=original_filename,
        segment_seconds=segment_seconds,
        reformat_vertical=reformat_vertical,
        auto_caption=auto_caption,
        subtitle_font=subtitle_font,
        status="uploaded",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def process_job(db: Session, job: ClipJob) -> ClipJob:
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

        try:
            subtitle_path: str | None = None
            output_path = clips_dir / f"job{job.id}_clip{i}.mp4"
            raw_segment_path = temp_dir / f"job{job.id}_clip{i}_raw.mp4"

            ffmpeg.extract_segment(
                job.source_file_path,
                str(raw_segment_path),
                start_seconds=start,
                duration_seconds=length,
                reformat_vertical=False,
                subtitle_path=None,
            )

            if job.auto_caption:
                srt_text = transcribe_to_srt(str(raw_segment_path))
                subtitle_path = temp_dir / f"job{job.id}_clip{i}.srt"
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

        db.commit()

    any_failed = any(c.status == "failed" for c in job.clips)
    job.status = "completed_with_errors" if any_failed else "completed"
    db.commit()
    db.refresh(job)
    return job
