from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, Request, BackgroundTasks
from redis.asyncio import Redis

from app.models.url import URL
from app.models.analytics import Click
from app.schemas.url import URLCreate, URLUpdate
from app.utils.short_code import generate_short_code
from app.config import settings


# ── Create Short URL ────────────────────────────────────────
async def create_short_url(
    data: URLCreate,
    user_id: str,
    db: AsyncSession
) -> URL:
    original_url = str(data.original_url)

    # Handle custom alias
    if data.custom_alias:
        result = await db.execute(
            select(URL).where(URL.custom_alias == data.custom_alias)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom alias already taken"
            )
        short_code = data.custom_alias
    else:
        # Generate unique short code — retry if collision
        for _ in range(5):
            short_code = generate_short_code()
            result = await db.execute(
                select(URL).where(URL.short_code == short_code)
            )
            if not result.scalar_one_or_none():
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate unique short code. Try again."
            )

    new_url = URL(
        user_id=user_id,
        original_url=original_url,
        short_code=short_code,
        custom_alias=data.custom_alias,
        expires_at=data.expires_at
    )
    db.add(new_url)
    await db.flush()
    return new_url


# ── Get Original URL for Redirect ───────────────────────────
async def get_original_url(
    short_code: str,
    db: AsyncSession,
    redis_client: Redis
) -> str:
    # Check Redis cache first
    cached = await redis_client.get(f"url:{short_code}")
    if cached:
        return cached

    # Cache miss — hit database
    result = await db.execute(
        select(URL).where(URL.short_code == short_code)
    )
    url = result.scalar_one_or_none()

    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )

    if not url.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This URL has been deactivated"
        )

    from datetime import datetime
    if url.expires_at and url.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This URL has expired"
        )

    # Store in Redis cache for 24 hours
    await redis_client.setex(f"url:{short_code}", 86400, url.original_url)

    return url.original_url


# ── Track Click (runs in background) ────────────────────────
async def track_click(
    short_code: str,
    ip_address: str,
    user_agent: str,
    referer: str
) -> None:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(URL).where(URL.short_code == short_code)
        )
        url = result.scalar_one_or_none()
        if not url:
            return

        device_type = "mobile" if any(
            x in user_agent.lower()
            for x in ["mobile", "android", "iphone"]
        ) else "desktop"

        click = Click(
            url_id=url.id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            device_type=device_type
        )
        session.add(click)
        url.click_count += 1
        await session.commit()

# ── Get All URLs for User ────────────────────────────────────
async def get_user_urls(
    user_id: str,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20
) -> list[URL]:
    result = await db.execute(
        select(URL)
        .where(URL.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(URL.created_at.desc())
    )
    return result.scalars().all()


# ── Deactivate URL ───────────────────────────────────────────
async def deactivate_url(
    short_code: str,
    user_id: str,
    db: AsyncSession,
    redis_client: Redis
) -> dict:
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

    url.is_active = False

    # Remove from Redis cache
    await redis_client.delete(f"url:{short_code}")

    return {"message": "URL deactivated successfully"}


# ── Update URL ───────────────────────────────────────────────
async def update_url(
    short_code: str,
    user_id: str,
    data: URLUpdate,
    db: AsyncSession,
    redis_client: Redis
) -> URL:
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

    if data.custom_alias:
        url.custom_alias = data.custom_alias
        url.short_code = data.custom_alias
        # Update Redis cache key
        await redis_client.delete(f"url:{short_code}")

    if data.expires_at:
        url.expires_at = data.expires_at

    await db.flush()
    return url