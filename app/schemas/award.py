from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID
from app.schemas.base import ItemResponse
from typing import Optional

class AwardBase(BaseModel):
    name: str
    issuer: str
    issue_date: date
    description: str
    category: str

class AwardCreate(AwardBase):
    pass

class AwardUpdate(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    description: Optional[str] = None
    category: Optional[str] = None

class AwardResponse(ItemResponse, AwardBase):
    created_at: datetime
    updated_at: datetime
