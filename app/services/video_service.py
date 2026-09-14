import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import Content
from app.models.video import Video
from app.utils import ffmpeg
from app.utils.subtitle import generate_srt


def generate_video(db: Session, content: Content) -> Video:
    if not content.media_assets:
        raise ValueError("Content has no media assets; run generate_media first")
    if not content.audio_assets:
        raise ValueError("Content has no audio assets; run generate_audio first")
    if not content.scripts:
        raise ValueError("Content has no script; run generate_script first")

    audio = content.audio_assets[-1]
    script = content.scripts[-1]
    image_paths = [asset.file_path for asset in content.media_assets]

    videos_dir = Path(settings.storage_path) / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(settings.storage_path) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    video = Video(content_id=content.id, status="processing", width=settings.default_video_width, height=settings.default_video_height)
    db.add(video)
    db.commit()
    db.refresh(video)

    subtitle_path = temp_dir / f"{content.id}_{uuid.uuid4().hex}.srt"
    srt_content = generate_srt(script.script_text, audio.duration)
    subtitle_path.write_text(srt_content, encoding="utf-8")

    output_path = videos_dir / f"{content.id}_{uuid.uuid4().hex}.mp4"

    try:
        ffmpeg.build_vertical_video(
            image_paths=image_paths,
            audio_path=audio.file_path,
            subtitle_path=str(subtitle_path),
            output_path=str(output_path),
            duration=audio.duration,
            width=settings.default_video_width,
            height=settings.default_video_height,
        )
    except ffmpeg.FFmpegError as exc:
        video.status = "failed"
        video.error = str(exc)
        db.commit()
        db.refresh(video)
        return video

    video.file_path = str(output_path)
    video.duration = audio.duration
    video.status = "ready"
    content.status = "VIDEO_GENERATED"
    db.commit()
    db.refresh(video)
    return video
