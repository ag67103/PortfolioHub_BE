from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import datetime, date
from uuid import UUID
from app.schemas.base import ItemResponse


def _validate_http_url(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if v == '':
        return None   # a blank optional link means "no link"
    if not v.startswith(('http://', 'https://')):
        raise ValueError('URL must start with http:// or https://')
    return v


class ProjectBase(BaseModel):
    title: str
    description: str
    technologies: list[str]
    live_url: Optional[str] = None
    code_url: Optional[str] = None
    image_url: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None

    @field_validator('live_url', 'code_url', 'image_url', mode='before')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return _validate_http_url(v)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[list[str]] = None
    live_url: Optional[str] = None
    code_url: Optional[str] = None
    image_url: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator('live_url', 'code_url', 'image_url', mode='before')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return _validate_http_url(v)


class ProjectResponse(ItemResponse):
    # Plain fields (no URL validators): stored data is returned as-is
    title: str
    description: str
    technologies: list[str]
    live_url: Optional[str] = None
    code_url: Optional[str] = None
    image_url: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
