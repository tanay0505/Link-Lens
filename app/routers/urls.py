from fastapi import APIRouter, Depends, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.database import get_db
from app.dependencies import get_redis, get_current_user
from app.schemas.url import URLCreate, URLResponse, URLUpdate
from app.services.url_service import (
    create_short_url, get_original_url, track_click,
    get_user_urls, deactivate_url, update_url
)
from app.config import settings

router = APIRouter(tags=["URLs"])


# ── Shorten URL ──────────────────────────────────────────────
@router.post("/api/v1/urls/shorten", response_model=URLResponse, status_code=201)
async def shorten_url(
    data: URLCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    url = await create_short_url(data, current_user["sub"], db)
    url.short_url = f"{settings.BASE_URL}/{url.short_code}"
    return url


# ── List My URLs ─────────────────────────────────────────────
@router.get("/api/v1/urls", response_model=list[URLResponse])
async def list_urls(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    urls = await get_user_urls(current_user["sub"], db, skip, limit)
    for url in urls:
        url.short_url = f"{settings.BASE_URL}/{url.short_code}"
    return urls


# ── Redirect ─────────────────────────────────────────────────
@router.get("/{short_code}")
async def redirect(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
):
    original_url = await get_original_url(short_code, db, redis_client)

    # Extract everything from request BEFORE background task runs
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")
    referer = request.headers.get("referer")

    background_tasks.add_task(
        track_click, short_code, ip_address, user_agent, referer
    )

    return RedirectResponse(url=original_url, status_code=302)


# ── Deactivate URL ───────────────────────────────────────────
@router.delete("/api/v1/urls/{short_code}")
async def delete_url(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    return await deactivate_url(short_code, current_user["sub"], db, redis_client)


# ── Update URL ───────────────────────────────────────────────
@router.patch("/api/v1/urls/{short_code}", response_model=URLResponse)
async def patch_url(
    short_code: str,
    data: URLUpdate,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    url = await update_url(short_code, current_user["sub"], data, db, redis_client)
    url.short_url = f"{settings.BASE_URL}/{url.short_code}"
    return url