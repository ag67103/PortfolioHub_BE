from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from app.utils.auth import require_role, pwd_context, create_access_token, get_current_user, get_token_row, oauth2_scheme
from app.models.user import User
from app.models.access_token import AccessToken
from app.schemas.user import UserCreate, UserResponse
from app.enums.user import UserRole, UserStatus
from datetime import datetime, timezone, timedelta

router = APIRouter()

@router.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(User).where(User.email == user.email))).scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if (await db.execute(select(User).where(User.username == user.username))).scalars().first():
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=pwd_context.hash(user.password),
        role=UserRole.viewer,  # Default role is viewer, not admin
        is_active=UserStatus.active,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        title=user.title
    )

    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        # Lost a race with a concurrent registration (unique constraint on email/username)
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email or username already registered")
    return new_user

@router.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(
        select(User).where(or_(User.username == form_data.username, User.email == form_data.username))
    )).scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(form_data.password, user.hashed_password):  # type: ignore
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.is_active is UserStatus.inactive:
        raise HTTPException(status_code=401, detail="Inactive user")

    access_token = await create_access_token(
        data={
            "username": user.username,
            "role": user.role
        },
        user_id=user.id,
        db=db
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/auth/refresh")
async def refresh_token(current_user: User = Depends(get_current_user), token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Refresh the access token, extending the expiry time."""
    # Delete old token
    old_token = await get_token_row(db, token)
    if old_token:
        await db.delete(old_token)
        await db.commit()
    
    # Create new token
    new_access_token = await create_access_token(
        data={
            "username": current_user.username,
            "role": current_user.role
        },
        user_id=current_user.id,
        db=db
    )
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user), token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Logout user by deleting the current token from database."""
    # Delete the token from database
    token_doc = await get_token_row(db, token)
    if token_doc:
        await db.delete(token_doc)
        await db.commit()
        return {"message": "Successfully logged out"}
    else:
        # Token already deleted or doesn't exist
        return {"message": "Token already revoked"}

@router.post("/auth/cleanup-tokens", dependencies=[Depends(require_role("admin"))])
async def manual_cleanup_tokens(db: AsyncSession = Depends(get_db)):
    """Manually trigger cleanup of expired tokens (admin only)."""
    from app.utils.token_cleanup import cleanup_expired_access_tokens
    deleted_count = await cleanup_expired_access_tokens()
    current_time = datetime.now(timezone.utc)
    total_count = (await db.execute(select(func.count()).select_from(AccessToken))).scalar_one()
    expired_count = (await db.execute(
        select(func.count()).select_from(AccessToken).where(AccessToken.expires_at < current_time)
    )).scalar_one()
    stats = {
        "total_tokens": total_count,
        "expired_tokens": expired_count,
        "active_tokens": total_count - expired_count
    }
    return {
        "message": "Cleanup completed",
        "deleted_tokens": deleted_count,
        "stats": stats
    }

@router.get("/auth/token-stats", dependencies=[Depends(require_role("admin"))])
async def get_token_stats(db: AsyncSession = Depends(get_db)):
    """Get statistics about active tokens (admin only)."""
    current_time = datetime.now(timezone.utc)
    total_count = (await db.execute(select(func.count()).select_from(AccessToken))).scalar_one()
    expired_count = (await db.execute(
        select(func.count()).select_from(AccessToken).where(AccessToken.expires_at < current_time)
    )).scalar_one()

    return {
        "total_tokens": total_count,
        "expired_tokens": expired_count,
        "active_tokens": total_count - expired_count
    }