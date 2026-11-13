from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._helpers import apply_update, error, get_owned
from app.db.database import get_db
from app.models.education import Education
from app.models.user import User
from app.schemas.education import EducationCreate, EducationUpdate, EducationResponse
from app.utils.auth import get_current_user

router = APIRouter()

# get current user's educations
@router.get('', response_model=List[EducationResponse])
async def get_current_user_educations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Education).where(Education.user_id == current_user.id))).scalars().all()

# get educations by user id
@router.get('/user/{user_id}', response_model=List[EducationResponse])
async def read_educations_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(Education).where(Education.user_id == user_id))).scalars().all()
    return items

# create education
@router.post('', response_model=EducationResponse)
async def create_education(item: EducationCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_item = Education(**item.model_dump(), user_id=current_user.id)
    db.add(new_item)
    await db.commit()
    return new_item

# update education
@router.put('/{item_id}', response_model=EducationResponse)
async def update_education(item_id: UUID, item: EducationUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Education, item_id, current_user, 'Education', 'update')
    return await apply_update(db, target, item.model_dump(exclude_unset=True))

# delete education
@router.delete('/{item_id}', response_model=dict)
async def delete_education(item_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Education, item_id, current_user, 'Education', 'delete')
    await db.delete(target)
    await db.commit()
    return {'message': 'Education deleted successfully'}
