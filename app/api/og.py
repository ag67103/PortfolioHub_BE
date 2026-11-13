"""
Link previews for shared portfolio links.

The frontend is a single-page app, so a crawler (LinkedIn, Slack, WhatsApp, Google) that fetches
https://<site>/u/<slug> only sees an empty page. The frontend's web server sends crawler requests here
instead; this returns a small HTML page with the right Open Graph / Twitter tags and a 1200x630 preview image.
Real visitors who land here are redirected straight to the portfolio.
"""
from html import escape
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.user import User

router = APIRouter()

SITE_NAME = "Portfolio Hub"


async def _find_user(db: AsyncSession, ref: str) -> User:
    try:
        user = await db.get(User, UUID(ref))
    except ValueError:
        user = (await db.execute(select(User).where(User.slug == ref.lower()))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Not found")
    return user


def _name(user: User) -> str:
    return " ".join(p for p in (user.first_name, user.middle_name, user.last_name) if p) or user.username


def _profile_url(user: User) -> str:
    base = settings.public_frontend_url
    return f"{base}/u/{user.slug}" if user.slug else f"{base}/user/{user.id}"


def _summary(user: User) -> str:
    text = (user.portfolio_description or "").strip().split("\n")[0]
    if len(text) > 200:
        text = text[:197].rsplit(" ", 1)[0] + "..."
    return text or user.portfolio_title or f"{_name(user)}'s portfolio"


@router.get("/{ref}", response_class=HTMLResponse)
async def og_page(ref: str, request: Request, db: AsyncSession = Depends(get_db)):
    user = await _find_user(db, ref)
    title = f"{_name(user)} | Portfolio"
    description = _summary(user)
    url = _profile_url(user)
    image = f"{str(request.base_url).rstrip('/')}/og/{ref}/image.png"
    t, d, u, i = (escape(x, quote=True) for x in (title, description, url, image))
    html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{u}">
<meta property="og:type" content="profile">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{u}">
<meta property="og:image" content="{i}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{i}">
<meta http-equiv="refresh" content="0;url={u}">
</head><body><p><a href="{u}">{t}</a></p></body></html>"""
    return HTMLResponse(html, headers={"Cache-Control": "public, max-age=300"})


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow: fixed-size bitmap font
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            line = trial
        else:
            lines.append(line)
            line = word
        if len(lines) == max_lines:
            break
    if line and len(lines) < max_lines:
        lines.append(line)
    if len(lines) == max_lines and " ".join(lines) != text:
        lines[-1] = lines[-1].rstrip(".,") + "..."
    return lines


@router.get("/{ref}/image.png")
async def og_image(ref: str, db: AsyncSession = Depends(get_db)):
    user = await _find_user(db, ref)
    img = Image.new("RGB", (1200, 630), (10, 10, 20))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 1200, 12], fill=(99, 102, 241))
    draw.rectangle([80, 120, 200, 240], fill=(99, 102, 241))
    initials = "".join(p[0] for p in (user.first_name, user.last_name) if p).upper() or _name(user)[:2].upper()
    f_init = _font(56)
    draw.text((140, 180), initials, font=f_init, fill=(255, 255, 255), anchor="mm")
    draw.text((240, 150), _name(user), font=_font(76), fill=(244, 244, 250))
    tagline = user.portfolio_title or ""
    for n, line in enumerate(_wrap(draw, tagline, _font(36), 880, 2)):
        draw.text((240, 250 + n * 48), line, font=_font(36), fill=(129, 140, 248))
    for n, line in enumerate(_wrap(draw, _summary(user), _font(30), 1040, 3)):
        draw.text((80, 380 + n * 42), line, font=_font(30), fill=(160, 160, 180))
    draw.text((80, 560), SITE_NAME, font=_font(30), fill=(129, 140, 248))
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
