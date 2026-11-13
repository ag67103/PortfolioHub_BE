import uuid
from datetime import date, datetime

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import created_at_col, updated_at_col, user_fk, uuid_pk


class Award(Base):
    __tablename__ = "awards"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(500))
    issuer: Mapped[str] = mapped_column(String(500))
    issue_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
