from fastapi import Request, HTTPException, status
import redis.asyncio as aioredis


async def check_rate_limit(request: Request, redis_client: aioredis.Redis) -> None:
    ip = request.client.host
    key = f"rate_limit:{ip}"

    count = await redis_client.get(key)

    if count and int(count) >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in an hour."
        )

    pipe = redis_client.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, 3600)   # 1 hour window
    await pipe.execute()