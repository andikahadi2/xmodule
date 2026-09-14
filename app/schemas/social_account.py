from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SocialAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    external_id: str
    display_name: str
    avatar_url: str | None
    status: str
    created_at: datetime
