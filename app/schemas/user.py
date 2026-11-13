import re
from pydantic import BaseModel, ConfigDict, field_validator, EmailStr
from app.enums.user import UserRole, UserStatus
from uuid import UUID
from typing import Optional, List
from datetime import datetime


def _validate_http_url(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if v == '':
        return None   # a blank optional link means "no link"
    if not v.startswith(('http://', 'https://')):
        raise ValueError('URL must start with http:// or https://')
    return v


RESERVED_SLUGS = {'dashboard', 'login', 'register', 'user', 'u', 'api', 'og', 'admin', 'privacy-policy', 'terms-of-service', 'projects'}
_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def _validate_slug(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip().lower()
    if v == '':
        return None
    if not 3 <= len(v) <= 40 or not _SLUG_RE.match(v):
        raise ValueError('Link name must be 3-40 characters: lowercase letters, numbers and single hyphens')
    if v in RESERVED_SLUGS:
        raise ValueError('That link name is reserved')
    return v


class UserBase(BaseModel):
    email: EmailStr
    role: Optional[UserRole] = UserRole.viewer
    is_active: Optional[UserStatus] = UserStatus.active


class UserCreate(UserBase):
    username: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    password: str
    title: Optional[str] = None
    phone: Optional[str] = None
    portfolio_title: Optional[str] = None
    portfolio_description: Optional[str] = None
    portfolio_education: Optional[List[str]] = None
    portfolio_certifications: Optional[List[str]] = None
    portfolio_awards: Optional[List[str]] = None

    @field_validator('password')
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    role: UserRole
    is_active: UserStatus
    title: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    portfolio_title: Optional[str] = None
    portfolio_description: Optional[str] = None
    portfolio_education: Optional[List[str]] = None
    portfolio_certifications: Optional[List[str]] = None
    portfolio_awards: Optional[List[str]] = None
    github_url: Optional[str] = None
    twitter_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    leetcode_url: Optional[str] = None
    website_url: Optional[str] = None
    address: Optional[str] = None
    slug: Optional[str] = None
    open_to_work: bool = False
    visitor_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    portfolio_title: Optional[str] = None
    portfolio_description: Optional[str] = None
    portfolio_education: Optional[List[str]] = None
    portfolio_certifications: Optional[List[str]] = None
    portfolio_awards: Optional[List[str]] = None
    phone: Optional[str] = None
    github_url: Optional[str] = None
    twitter_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    leetcode_url: Optional[str] = None
    website_url: Optional[str] = None
    address: Optional[str] = None
    slug: Optional[str] = None
    open_to_work: Optional[bool] = None

    @field_validator('slug', mode='before')
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        return _validate_slug(v)

    @field_validator('github_url', 'twitter_url', 'instagram_url', 'linkedin_url', 'leetcode_url', 'website_url', mode='before')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return _validate_http_url(v)
