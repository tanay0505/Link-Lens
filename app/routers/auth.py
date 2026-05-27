from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.database import get_db
from app.schemas.user import UserRegister, UserResponse, TokenResponse
from app.services.auth_service import (
    register_user, login_user, refresh_access_token, logout_user
)
from app.utils.jwt import decode_token
from app.dependencies import get_redis
from app.dependencies import get_redis, get_current_user
import redis.asyncio as Redis

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    user = await register_user(data, db)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    return await login_user(data.email, data.password, db)


@router.post("/refresh")
async def refresh(
    token: str,
    redis_client: aioredis.Redis = Depends(get_redis)
):
    return await refresh_access_token(token, redis_client)


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis)
):
    return {"message": "Logged out successfully"}