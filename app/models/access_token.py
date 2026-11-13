import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import created_at_col, uuid_pk


class AccessToken(Base):
    """Active access tokens (a token missing from this table is revoked)."""
    __tablename__ = "access_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    token: Mapped[str] = mapped_column(Text, unique=True, index=True)  # The JWT string
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    username: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = created_at_col()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
