from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ClickResponse(BaseModel):
    id: str
    url_id: str
    clicked_at: datetime
    country: Optional[str]
    device_type: Optional[str]
    referer: Optional[str]

    model_config = {"from_attributes": True}


class AnalyticsSummary(BaseModel):
    total_clicks: int
    unique_countries: int
    top_country: Optional[str]
    desktop_clicks: int
    mobile_clicks: int


class TimelineEntry(BaseModel):
    date: str
    clicks: int