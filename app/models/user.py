import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import ARRAY, DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.enums.user import UserGender, UserRole, UserStatus
from app.models.base import created_at_col, updated_at_col, uuid_pk


def _enum(enum_cls):
    # Stored as plain strings (no native PG enum type), read back as the enum member
    return SAEnum(enum_cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Authentication & Basic Info
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[UserStatus] = mapped_column(_enum(UserStatus), default=UserStatus.active)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.viewer)

    # Personal Information
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    middle_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[UserGender]] = mapped_column(_enum(UserGender))

    # Contact Information
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    profile_image_url: Mapped[Optional[str]] = mapped_column(Text)

    # Portfolio/About Information
    portfolio_title: Mapped[Optional[str]] = mapped_column(Text)
    portfolio_description: Mapped[Optional[str]] = mapped_column(Text)
    portfolio_education: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    portfolio_certifications: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    portfolio_awards: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))

    # Social Media Links
    github_url: Mapped[Optional[str]] = mapped_column(Text)
    twitter_url: Mapped[Optional[str]] = mapped_column(Text)
    instagram_url: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text)
    leetcode_url: Mapped[Optional[str]] = mapped_column(Text)
    website_url: Mapped[Optional[str]] = mapped_column(Text)

    # Analytics
    visitor_count: Mapped[int] = mapped_column(default=0)

    # System Fields
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
