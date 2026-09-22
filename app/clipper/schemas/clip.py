from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    index: int
    start_seconds: float
    end_seconds: float
    file_path: str | None
    subtitle_path: str | None
    status: str
    error: str | None
    created_at: datetime


class ClipJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    original_filename: str
    mode: str
    segment_seconds: int
    reformat_vertical: bool
    auto_caption: bool
    subtitle_font: str
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime
    clips: list[ClipOut] = []


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class SegmentIn(BaseModel):
    start_seconds: float
    end_seconds: float
