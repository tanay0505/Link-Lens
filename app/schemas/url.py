from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None


class URLResponse(BaseModel):
    id: str
    original_url: str
    short_code: str
    custom_alias: Optional[str]
    is_active: bool
    click_count: int
    expires_at: Optional[datetime]
    created_at: datetime
    short_url: str = ""

    model_config = {"from_attributes": True}


class URLUpdate(BaseModel):
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    