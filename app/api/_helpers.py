from datetime import datetime, timezone
from typing import Type, TypeVar

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.error import Error

T = TypeVar("T")


def error(status_code: int, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=Error(message=message, status_code=status_code).model_dump())


async def get_owned(db: AsyncSession, model: Type[T], item_id, current_user: User, label: str, action: str) -> T:
    """Fetch an item by id and make sure the current user owns it (404 / 403 otherwise)."""
    item = await db.get(model, item_id)
    if item is None:
        raise error(404, f'{label} not found')
    if item.user_id != current_user.id:  # type: ignore[attr-defined]
        raise error(403, f'You are not allowed to {action} this {label.lower()}')
    return item


async def apply_update(db: AsyncSession, item, data: dict):
    for key, value in data.items():
        setattr(item, key, value)
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return item
