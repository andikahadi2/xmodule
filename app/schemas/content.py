from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContentIdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_id: int
    hook: str
    angle: str
    target_audience: str
    content_type: str
    estimated_duration: int
    ai_provider: str
    status: str
    created_at: datetime


class ContentScriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_id: int
    version: int
    script_text: str
    hook: str
    cta: str
    duration: int
    ai_provider: str
    ai_model: str
    status: str
    created_at: datetime


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    ideas: list[ContentIdeaOut] = []
    scripts: list[ContentScriptOut] = []
