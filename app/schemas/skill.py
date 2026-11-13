from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.schemas.base import ItemResponse

class SkillBase(BaseModel):
    name: str
    category: str
    proficiency: int = Field(ge=0, le=100)

class SkillCreate(SkillBase):
    pass

class SkillUpdate(SkillBase):
    name: Optional[str] = None
    category: Optional[str] = None
    proficiency: Optional[int] = Field(default=None, ge=0, le=100)

class SkillResponse(ItemResponse, SkillBase):
    created_at: datetime
    updated_at: datetime
