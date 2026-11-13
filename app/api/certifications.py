from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._helpers import apply_update, error, get_owned
from app.db.database import get_db
from app.models.certification import Certification
from app.models.user import User
from app.schemas.certification import CertificationCreate, CertificationUpdate, CertificationResponse
from app.utils.auth import get_current_user

router = APIRouter()

# get certifications by user id
@router.get('/certifications/user/{user_id}', response_model=List[CertificationResponse])
async def read_certifications_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(Certification).where(Certification.user_id == user_id))).scalars().all()
    return items

# create certification
@router.post('/certifications', response_model=CertificationResponse)
async def create_certification(item: CertificationCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_item = Certification(**item.model_dump(), user_id=current_user.id)
    db.add(new_item)
    await db.commit()
    return new_item

# update certification
@router.put('/certifications/{item_id}', response_model=CertificationResponse)
async def update_certification(item_id: UUID, item: CertificationUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Certification, item_id, current_user, 'Certification', 'update')
    return await apply_update(db, target, item.model_dump(exclude_unset=True))

# delete certification
@router.delete('/certifications/{item_id}', response_model=dict)
async def delete_certification(item_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await get_owned(db, Certification, item_id, current_user, 'Certification', 'delete')
    await db.delete(target)
    await db.commit()
    return {'message': 'Certification deleted successfully'}
