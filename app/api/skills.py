from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._helpers import apply_update, error, get_owned
from app.db.database import get_db
from app.models.skill import Skill
from app.models.user import User
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse
from app.utils.auth import get_current_user

router = APIRouter()

# get skills by user id
@router.get('/skills/user/{user_id}', response_model=List[SkillResponse])
async def read_skills_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(Skill).where(Skill.user_id == user_id))).scalars().all()
    return items

# create skill
@router.post('/skills', response_model=SkillResponse)
async def create_skill(item: SkillCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # check if skill already exists
    existing = (await db.execute(select(Skill).where(Skill.name == item.name, Skill.user_id == current_user.id))).scalars().first()
    if existing:
        raise error(400, 'Skill already exists')

    new_item = Skill(**item.model_dump(), user_id=current_user.id)
    db.add(new_item)
    await db.commit()
    return new_item

# update skill
@router.put('/skills/{item_id}', response_model=SkillResponse)
async def update_skill(item_id: UUID, item: SkillUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Skill, item_id, current_user, 'Skill', 'update')
    return await apply_update(db, target, item.model_dump(exclude_unset=True))

# delete skill
@router.delete('/skills/{item_id}', response_model=dict)
async def delete_skill(item_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Skill, item_id, current_user, 'Skill', 'delete')
    await db.delete(target)
    await db.commit()
    return {'message': 'Skill deleted successfully'}
