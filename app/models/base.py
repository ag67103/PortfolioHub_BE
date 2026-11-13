import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def user_fk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow)


def updated_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow)


def to_dict(obj) -> dict:
    """Column values of an ORM row as a plain dict (replacement for Beanie's model_dump())."""
    return {c.key: getattr(obj, c.key) for c in obj.__mapper__.column_attrs}
