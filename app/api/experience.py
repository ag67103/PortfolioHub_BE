from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._helpers import apply_update, error, get_owned
from app.db.database import get_db
from app.models.experience import Experience
from app.models.user import User
from app.schemas.experience import ExperienceCreate, ExperienceUpdate, ExperienceResponse
from app.utils.auth import get_current_user

router = APIRouter()

# get experiences by user id
@router.get('/experiences/user/{user_id}', response_model=List[ExperienceResponse])
async def read_experiences_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(Experience).where(Experience.user_id == user_id))).scalars().all()
    # newest first: end_date if available, else start_date
    items = sorted(items, key=lambda x: x.end_date if x.end_date else x.start_date, reverse=True)
    return items

# create experience
@router.post('/experiences', response_model=ExperienceResponse)
async def create_experience(item: ExperienceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_item = Experience(**item.model_dump(), user_id=current_user.id)
    db.add(new_item)
    await db.commit()
    return new_item

# update experience
@router.put('/experiences/{item_id}', response_model=ExperienceResponse)
async def update_experience(item_id: UUID, item: ExperienceUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Experience, item_id, current_user, 'Experience', 'update')
    return await apply_update(db, target, item.model_dump(exclude_unset=True))

# delete experience
@router.delete('/experiences/{item_id}', response_model=dict)
async def delete_experience(item_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Experience, item_id, current_user, 'Experience', 'delete')
    await db.delete(target)
    await db.commit()
    return {'message': 'Experience deleted successfully'}
