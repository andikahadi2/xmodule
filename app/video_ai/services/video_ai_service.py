import random
import uuid
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.providers.video import PexelsVideoProvider, VideoProviderError
from app.utils import ffmpeg
from app.video_ai.models.job import VideoAiClip, VideoAiJob

CLIP_SECONDS = 4.0
MUSIC_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac"}


def _pick_background_music() -> str | None:
    music_dir = Path(settings.storage_path) / "music"
    tracks = [p for p in music_dir.glob("*") if p.suffix.lower() in MUSIC_EXTENSIONS]
    if not tracks:
        return None
    return str(random.choice(tracks))


def _download(url: str, dest: Path, timeout: float = 30.0) -> None:
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)


def create_job(db: Session, query: str, clip_count: int = 10) -> VideoAiJob:
    job = VideoAiJob(query=query, clip_count=clip_count, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def process_job(db: Session, job: VideoAiJob) -> VideoAiJob:
    try:
        results = PexelsVideoProvider().search(job.query, count=job.clip_count)
    except VideoProviderError as exc:
        job.status = "failed"
        job.error = str(exc)
        db.commit()
        db.refresh(job)
        return job

    if not results:
        job.status = "failed"
        job.error = f"No stock footage found for query: {job.query}"
        db.commit()
        db.refresh(job)
        return job

    raw_dir = Path(settings.storage_path) / "temp"
    raw_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = Path(settings.storage_path) / "video_ai_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    videos_dir = Path(settings.storage_path) / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    job.status = "processing"
    db.commit()

    ready_paths: list[str] = []
    for i, result in enumerate(results):
        clip = VideoAiClip(
            job_id=job.id,
            index=i,
            source_url=result.url,
            license_info=result.license_info,
            status="processing",
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)

        raw_path = raw_dir / f"videoai{job.id}_{i}_{uuid.uuid4().hex}.mp4"
        normalized_path = clips_dir / f"videoai{job.id}_{i}.mp4"
        try:
            _download(result.url, raw_path)
            ffmpeg.extract_segment(
                str(raw_path),
                str(normalized_path),
                start_seconds=0,
                duration_seconds=min(CLIP_SECONDS, result.duration or CLIP_SECONDS),
                reformat_vertical=True,
                width=settings.default_video_width,
                height=settings.default_video_height,
            )
            clip.file_path = str(normalized_path)
            clip.status = "ready"
            ready_paths.append(str(normalized_path))
        except (httpx.HTTPError, ffmpeg.FFmpegError) as exc:
            clip.status = "failed"
            clip.error = str(exc)
        finally:
            raw_path.unlink(missing_ok=True)

        db.commit()

    if not ready_paths:
        job.status = "failed"
        job.error = "All clip downloads/processing failed"
        db.commit()
        db.refresh(job)
        return job

    music_path = _pick_background_music()
    output_path = videos_dir / f"videoai{job.id}_{uuid.uuid4().hex}.mp4"
    try:
        ffmpeg.concat_video_clips(ready_paths, str(output_path), audio_path=music_path)
    except ffmpeg.FFmpegError as exc:
        job.status = "failed"
        job.error = str(exc)
        db.commit()
        db.refresh(job)
        return job

    job.output_path = str(output_path)
    job.music_path = music_path
    job.status = "completed" if len(ready_paths) == len(results) else "completed_with_errors"
    db.commit()
    db.refresh(job)
    return job
