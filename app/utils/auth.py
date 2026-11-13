import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.enums.user import UserStatus
from app.models.access_token import AccessToken
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token") 

# Secret key for JWT - from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", settings.secret_key)
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Validate that SECRET_KEY is set and not default
if SECRET_KEY == "your-secret-key-here" or SECRET_KEY == "your-256-bit-secret-key":
    import warnings
    warnings.warn(
        "WARNING: Using default SECRET_KEY! This is insecure. "
        "Please set SECRET_KEY environment variable for production.",
        UserWarning
    )

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def create_access_token(
    data: dict,
    user_id: uuid.UUID,
    db: AsyncSession,
    expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
) -> str:
    """Create a JWT access token and store it in the database."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "jti": uuid.uuid4().hex})  # jti keeps every token unique
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Store token in database
    db.add(AccessToken(
        token=token,
        user_id=user_id,
        username=data.get("username", ""),
        role=str(data.get("role", "")),
        expires_at=expire
    ))
    await db.commit()

    return token


async def get_token_row(db: AsyncSession, token: str) -> AccessToken | None:
    return (await db.execute(select(AccessToken).where(AccessToken.token == token))).scalar_one_or_none()


async def is_token_valid(token: str, db: AsyncSession) -> bool:
    """Check if a token exists in the database (not deleted) and has not expired."""
    token_doc = await get_token_row(db, token)
    if token_doc is None:
        return False

    if _as_utc(token_doc.expires_at) < datetime.now(timezone.utc):
        # Auto-delete expired token
        await db.delete(token_doc)
        await db.commit()
        return False

    return True

def verify_token(token: str) -> dict | None:
    """Verify a JWT token and return the payload, or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """Extract the user from a valid JWT token, or raise HTTPException if invalid."""
    # First verify JWT signature
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if token exists in database (not deleted)
    token_doc = await get_token_row(db, token)
    if token_doc is None:
        raise HTTPException(status_code=401, detail="Token has been revoked or expired")

    current_time = datetime.now(timezone.utc)
    if _as_utc(token_doc.expires_at) < current_time:
        await db.delete(token_doc)
        await db.commit()
        raise HTTPException(status_code=401, detail="Token has been revoked or expired")

    token_doc.last_used_at = current_time
    await db.commit()
    
    username = payload.get("username")
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.is_active == UserStatus.inactive:
        raise HTTPException(status_code=401, detail="Inactive user")

    return user

def require_role(required_role: str):
    def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:  # type: ignore
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_dependency
