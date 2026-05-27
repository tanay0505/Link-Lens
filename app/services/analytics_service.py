from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.url import URL
from app.models.analytics import Click
from datetime import datetime, timedelta


async def get_url_summary(
    short_code: str,
    user_id: str,
    db: AsyncSession
) -> dict:
    # Verify URL belongs to user
    result = await db.execute(
        select(URL).where(
            URL.short_code == short_code,
            URL.user_id == user_id
        )
    )
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found or not yours"
        )

    # Total clicks
    total = await db.execute(
        select(func.count(Click.id)).where(Click.url_id == url.id)
    )
    total_clicks = total.scalar()

    # Unique countries
    countries = await db.execute(
        select(func.count(func.distinct(Click.country)))
        .where(Click.url_id == url.id)
    )
    unique_countries = countries.scalar()

    # Top country
    top_country_result = await db.execute(
        select(Click.country, func.count(Click.country).label("cnt"))
        .where(Click.url_id == url.id)
        .group_by(Click.country)
        .order_by(func.count(Click.country).desc())
        .limit(1)
    )
    top_country_row = top_country_result.first()
    top_country = top_country_row[0] if top_country_row else None

    # Device breakdown
    desktop = await db.execute(
        select(func.count(Click.id)).where(
            Click.url_id == url.id,
            Click.device_type == "desktop"
        )
    )
    mobile = await db.execute(
        select(func.count(Click.id)).where(
            Click.url_id == url.id,
            Click.device_type == "mobile"
        )
    )

    return {
        "total_clicks": total_clicks,
        "unique_countries": unique_countries,
        "top_country": top_country,
        "desktop_clicks": desktop.scalar(),
        "mobile_clicks": mobile.scalar()
    }


async def get_click_timeline(
    short_code: str,
    user_id: str,
    days: int,
    db: AsyncSession
) -> list[dict]:
    # Verify URL belongs to user
    result = await db.execute(
        select(URL).where(
            URL.short_code == short_code,
            URL.user_id == user_id
        )
    )
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found or not yours"
        )

    # Clicks per day for last N days
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(Click.clicked_at).label("date"),
            func.count(Click.id).label("clicks")
        )
        .where(
            Click.url_id == url.id,
            Click.clicked_at >= since
        )
        .group_by(func.date(Click.clicked_at))
        .order_by(func.date(Click.clicked_at))
    )
    rows = result.all()

    # Fill in missing dates with 0
    timeline = []
    for i in range(days):
        day = (datetime.utcnow() - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        clicks = next((r.clicks for r in rows if str(r.date) == day), 0)
        timeline.append({"date": day, "clicks": clicks})

    return timeline


async def get_top_referrers(
    short_code: str,
    user_id: str,
    db: AsyncSession
) -> list[dict]:
    # Verify URL belongs to user
    result = await db.execute(
        select(URL).where(
            URL.short_code == short_code,
            URL.user_id == user_id
        )
    )
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found or not yours"
        )

    result = await db.execute(
        select(Click.referer, func.count(Click.id).label("cnt"))
        .where(Click.url_id == url.id)
        .group_by(Click.referer)
        .order_by(func.count(Click.id).desc())
        .limit(10)
    )
    rows = result.all()
    return [{"referer": r.referer or "direct", "clicks": r.cnt} for r in rows]