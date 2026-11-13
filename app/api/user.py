from fastapi import APIRouter, HTTPException, Request
from app.models.user import User
from app.schemas.user import UserResponse
from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from datetime import datetime, timezone
from sqlalchemy import select, update

router = APIRouter()

# Simple in-memory rate limiter: (ip, user_id) → last call timestamp
_visitor_rate_cache: dict[str, datetime] = {}
_VISITOR_RATE_LIMIT_SECONDS = 60

# get user by public link name (/u/<slug>)
@router.get('/user/slug/{slug}', response_model=UserResponse)
async def get_user_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.slug == slug.lower()))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# get user by id
@router.get('/user/{user_id}', response_model=UserResponse)
async def get_user_by_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# increment visitor count
@router.post('/user/{user_id}/increment-visitor')
async def increment_visitor_count(user_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    cache_key = f"{client_ip}:{user_id}"
    now = datetime.now(timezone.utc)

    last_call = _visitor_rate_cache.get(cache_key)
    if last_call is not None:
        elapsed = (now - last_call).total_seconds()
        if elapsed < _VISITOR_RATE_LIMIT_SECONDS:
            raise HTTPException(status_code=429, detail="Too many requests")

    _visitor_rate_cache[cache_key] = now

    # Prune stale entries to prevent unbounded memory growth
    if len(_visitor_rate_cache) > 10_000:
        cutoff = now.timestamp() - _VISITOR_RATE_LIMIT_SECONDS
        stale = [k for k, v in _visitor_rate_cache.items() if v.timestamp() < cutoff]
        for k in stale:
            del _visitor_rate_cache[k]

    # Atomic increment (no lost updates under concurrent visitors)
    result = await db.execute(
        update(User).where(User.id == user_id)
        .values(visitor_count=User.visitor_count + 1, updated_at=now)
        .returning(User.visitor_count)
    )
    new_count = result.scalar_one_or_none()
    if new_count is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()

    return {"visitor_count": new_count}