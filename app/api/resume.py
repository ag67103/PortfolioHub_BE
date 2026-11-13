from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from app.models.user import User
from app.models.experience import Experience
from app.models.education import Education
from app.models.project import Project
from app.models.skill import Skill
from app.models.certification import Certification
from app.models.award import Award
from datetime import datetime
from app.ResumeGenerator.pdf_resume import build_resume_pdf
from uuid import UUID
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.base import to_dict

router = APIRouter()

@router.get('/latex')
async def get_resume_latex(user_id: UUID = Query(..., description="User ID for the resume to generate"), db: AsyncSession = Depends(get_db)):
    """
    Generate and download the resume PDF (ReportLab) for the specified user.
    The path still says `latex` for backwards compatibility with the frontend.
    This endpoint is public and does not require authentication.
    Anyone can download any user's resume by providing their user_id.
    """
    try:
        # Get user by ID
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user data
        user_data = to_dict(user)
        user_data.pop("hashed_password", None)
        
        # Get all related data
        
        experiences = (await db.execute(select(Experience).where(Experience.user_id == user_id))).scalars().all()
        experiences = sorted(experiences, key=lambda x: x.end_date if x.end_date else x.start_date, reverse=True)
        
        educations = (await db.execute(select(Education).where(Education.user_id == user_id))).scalars().all()
        educations = sorted(educations, key=lambda x: x.end_date if x.end_date else x.start_date, reverse=True)
        
        projects = (await db.execute(select(Project).where(Project.user_id == user_id))).scalars().all()
        projects = sorted(projects, key=lambda x: x.end_date if x.end_date else x.start_date, reverse=True)
        
        skills = (await db.execute(select(Skill).where(Skill.user_id == user_id))).scalars().all()
        
        certifications = (await db.execute(select(Certification).where(Certification.user_id == user_id))).scalars().all()
        
        awards = (await db.execute(select(Award).where(Award.user_id == user_id))).scalars().all()
        
        # Convert to dict format and format dates
        def format_date(date_obj):
            if date_obj is None:
                return None
            if isinstance(date_obj, datetime):
                return date_obj.strftime('%Y-%m-%d')
            if hasattr(date_obj, 'strftime'):
                return date_obj.strftime('%Y-%m-%d')
            return str(date_obj)
        
        experiences_data = []
        for exp in experiences:
            exp_dict = to_dict(exp)
            exp_dict['start_date'] = format_date(exp.start_date)
            exp_dict['end_date'] = format_date(exp.end_date) if exp.end_date else None
            experiences_data.append(exp_dict)
        
        educations_data = []
        for edu in educations:
            edu_dict = to_dict(edu)
            edu_dict['start_date'] = format_date(edu.start_date)
            edu_dict['end_date'] = format_date(edu.end_date) if edu.end_date else None
            educations_data.append(edu_dict)
        
        projects_data = []
        for proj in projects:
            proj_dict = to_dict(proj)
            # Format dates the same way as experience (convert epoch to date string)
            proj_dict['start_date'] = format_date(proj.start_date)
            proj_dict['end_date'] = format_date(proj.end_date) if proj.end_date else None
            projects_data.append(proj_dict)
        
        skills_data = [to_dict(skill) for skill in skills]
        certifications_data = [to_dict(cert) for cert in certifications]
        
        awards_data = []
        for award in awards:
            award_dict = to_dict(award)
            # Format issue_date the same way as other dates
            award_dict['issue_date'] = format_date(award.issue_date) if award.issue_date else None
            awards_data.append(award_dict)

        pdf_bytes = build_resume_pdf(
            user_data=user_data,
            experiences=experiences_data,
            educations=educations_data,
            projects=projects_data,
            skills=skills_data,
            certifications=certifications_data,
            awards=awards_data
        )

        # Generate filename — strip characters that could break the Content-Disposition header
        import re as _re
        first_name = _re.sub(r'[^\w\s-]', '', user_data.get('first_name', '') or '')
        last_name = _re.sub(r'[^\w\s-]', '', user_data.get('last_name', '') or '')
        raw = f"{first_name}_{last_name}_Resume.pdf".strip('_')
        filename = raw.replace(' ', '_') or "Resume.pdf"

        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        # Log full error for debugging
        print(f"Resume generation error: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Error generating resume: {str(e)}")
