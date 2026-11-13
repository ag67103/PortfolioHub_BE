"""
Token cleanup utility.
Removes expired tokens from the database to prevent database bloat.
"""
from datetime import datetime, timezone
import logging

from sqlalchemy import delete, func, select

from app.db.database import SessionLocal
from app.models.access_token import AccessToken

logger = logging.getLogger(__name__)

async def cleanup_expired_access_tokens() -> int:
    """
    Remove all expired access tokens from the database.
    Returns the number of tokens deleted.
    """
    try:
        async with SessionLocal() as db:
            result = await db.execute(
                delete(AccessToken).where(AccessToken.expires_at < datetime.now(timezone.utc))
            )
            await db.commit()
            deleted_count = result.rowcount or 0  # type: ignore[attr-defined]
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired access tokens")
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {e}")
        return 0

async def get_token_stats() -> dict:
    """
    Get statistics about active tokens.
    Returns count of total tokens and expired tokens.
    """
    try:
        async with SessionLocal() as db:
            total_count = (await db.execute(select(func.count()).select_from(AccessToken))).scalar_one()
            expired_count = (await db.execute(
                select(func.count()).select_from(AccessToken).where(AccessToken.expires_at < datetime.now(timezone.utc))
            )).scalar_one()
        return {
            "total_tokens": total_count,
            "expired_tokens": expired_count,
            "active_tokens": total_count - expired_count
        }
    except Exception as e:
        logger.error(f"Error getting token stats: {e}")
        return {"total_tokens": 0, "expired_tokens": 0, "active_tokens": 0}
