from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._helpers import apply_update, error, get_owned
from app.db.database import get_db
from app.models.award import Award
from app.models.user import User
from app.schemas.award import AwardCreate, AwardUpdate, AwardResponse
from app.utils.auth import get_current_user

router = APIRouter()

# get awards by user id
@router.get('/awards/user/{user_id}', response_model=List[AwardResponse])
async def read_awards_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(Award).where(Award.user_id == user_id))).scalars().all()
    return items

# create award
@router.post('/awards', response_model=AwardResponse)
async def create_award(item: AwardCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_item = Award(**item.model_dump(), user_id=current_user.id)
    db.add(new_item)
    await db.commit()
    return new_item

# update award
@router.put('/awards/{item_id}', response_model=AwardResponse)
async def update_award(item_id: UUID, item: AwardUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Award, item_id, current_user, 'Award', 'update')
    return await apply_update(db, target, item.model_dump(exclude_unset=True))

# delete award
@router.delete('/awards/{item_id}', response_model=dict)
async def delete_award(item_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Award, item_id, current_user, 'Award', 'delete')
    await db.delete(target)
    await db.commit()
    return {'message': 'Award deleted successfully'}
