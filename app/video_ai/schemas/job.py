from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoAiClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    index: int
    source_url: str
    license_info: str | None
    file_path: str | None
    status: str
    error: str | None
    created_at: datetime


class VideoAiJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    query: str
    clip_count: int
    status: str
    output_path: str | None
    music_path: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    clips: list[VideoAiClipOut] = []
