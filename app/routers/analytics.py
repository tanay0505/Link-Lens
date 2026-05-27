from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.analytics import AnalyticsSummary, TimelineEntry
from app.services.analytics_service import (
    get_url_summary, get_click_timeline, get_top_referrers
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/{short_code}/summary", response_model=AnalyticsSummary)
async def summary(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return await get_url_summary(short_code, current_user["sub"], db)


@router.get("/{short_code}/timeline", response_model=list[TimelineEntry])
async def timeline(
    short_code: str,
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return await get_click_timeline(short_code, current_user["sub"], days, db)


@router.get("/{short_code}/referrers")
async def referrers(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return await get_top_referrers(short_code, current_user["sub"], db)