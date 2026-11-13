import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import created_at_col, updated_at_col, user_fk, uuid_pk


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(500))
    issuer: Mapped[str] = mapped_column(String(500))
    issue_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    credential_id: Mapped[Optional[str]] = mapped_column(Text)
    credential_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
