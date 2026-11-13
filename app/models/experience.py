import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import ARRAY, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import created_at_col, updated_at_col, user_fk, uuid_pk


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    technologies: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
