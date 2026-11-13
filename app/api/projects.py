from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._helpers import apply_update, error, get_owned
from app.db.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.utils.auth import get_current_user

router = APIRouter()

# get projects by user id
@router.get('/projects/user/{user_id}', response_model=List[ProjectResponse])
async def read_projects_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(Project).where(Project.user_id == user_id))).scalars().all()
    # newest first: end_date if available, else start_date
    items = sorted(items, key=lambda x: x.end_date if x.end_date else x.start_date, reverse=True)
    return items

# create project
@router.post('/projects', response_model=ProjectResponse)
async def create_project(item: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_item = Project(**item.model_dump(), user_id=current_user.id)
    db.add(new_item)
    await db.commit()
    return new_item

# update project
@router.put('/projects/{item_id}', response_model=ProjectResponse)
async def update_project(item_id: UUID, item: ProjectUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Project, item_id, current_user, 'Project', 'update')
    return await apply_update(db, target, item.model_dump(exclude_unset=True))

# delete project
@router.delete('/projects/{item_id}', response_model=dict)
async def delete_project(item_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Project, item_id, current_user, 'Project', 'delete')
    await db.delete(target)
    await db.commit()
    return {'message': 'Project deleted successfully'}
