from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from app.schemas.base import ItemResponse

class ExperienceBase(BaseModel):
    title: str
    company: str
    description: str
    technologies: List[str]
    start_date: date
    end_date: Optional[date] = None

class ExperienceCreate(ExperienceBase):
    pass

class ExperienceUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ExperienceResponse(ItemResponse, ExperienceBase):
    created_at: datetime
    updated_at: datetime
