from pydantic import BaseModel, field_validator
from datetime import date, datetime
from uuid import UUID
from app.schemas.base import ItemResponse
from typing import Optional


def _validate_http_url(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if v == '':
        return None   # a blank optional link means "no link"
    if not v.startswith(('http://', 'https://')):
        raise ValueError('URL must start with http:// or https://')
    return v


class CertificationBase(BaseModel):
    name: str
    issuer: str
    issue_date: date
    description: str
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None

    @field_validator('credential_url', mode='before')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return _validate_http_url(v)


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    description: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None

    @field_validator('credential_url', mode='before')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return _validate_http_url(v)


class CertificationResponse(ItemResponse):
    # Plain fields (no URL validator): stored data is returned as-is
    name: str
    issuer: str
    issue_date: date
    description: str
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
