from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID
from app.schemas.base import ItemResponse
from typing import Optional

class EducationBase(BaseModel):
    institution: str
    degree: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None
    
class EducationCreate(EducationBase):
    pass

class EducationUpdate(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

class EducationResponse(ItemResponse, EducationBase):
    created_at: datetime
    updated_at: datetime
