from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.schemas.user import PortfolioUpdate
from datetime import datetime, timezone
from app.utils.auth import get_current_user
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

def _portfolio(user: User) -> dict:
    return {
        'first_name': user.first_name,
        'middle_name': user.middle_name,
        'last_name': user.last_name,
        'portfolio_title': user.portfolio_title,
        'portfolio_description': user.portfolio_description,
        'portfolio_education': user.portfolio_education or [],
        'portfolio_certifications': user.portfolio_certifications or [],
        'portfolio_awards': user.portfolio_awards or [],
        'title': user.title,
        'phone': user.phone,
        'address': user.address,
        'slug': user.slug,
        'open_to_work': user.open_to_work,
        'github_url': user.github_url,
        'twitter_url': user.twitter_url,
        'instagram_url': user.instagram_url,
        'linkedin_url': user.linkedin_url,
        'leetcode_url': user.leetcode_url,
        'website_url': user.website_url
    }

# get portfolio by user id
@router.get('/user/{user_id}')
async def read_portfolio_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return _portfolio(user)

# get current user's portfolio
@router.get('/')
async def get_current_user_portfolio(current_user: User = Depends(get_current_user)):
    return _portfolio(current_user)

# update portfolio
@router.put('/')
async def update_portfolio(portfolio: PortfolioUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Update only the portfolio fields
    update_data = portfolio.model_dump(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(current_user, field, value)
        current_user.updated_at = datetime.now(timezone.utc)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail='That link name is already taken')

    return {
        'message': 'Portfolio updated successfully',
        'portfolio': _portfolio(current_user)
    }
