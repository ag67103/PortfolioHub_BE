"""
Resume PDF generation with ReportLab (pure Python, no system packages needed).

Layout follows the previous LaTeX template: centered name / title / contact links, then the sections
Technical Skills, Experience, Education, Projects, Achievements, Certifications, each with a heading rule.
Text stays selectable in the PDF, so it remains readable by applicant-tracking systems.
"""
from datetime import date, datetime
from io import BytesIO
from typing import Dict, List, Optional
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = HexColor("#130810")
MUTED = HexColor("#2E2E2E")
LINK = HexColor("#0E5484")

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Built-in PDF fonts only cover Latin-1 / WinAnsi; anything else is replaced so it never renders as a blank box
_ENCODING = "cp1252"

NAME = ParagraphStyle("name", fontName="Times-Bold", fontSize=22, leading=26, alignment=TA_CENTER, textColor=INK)
TAGLINE = ParagraphStyle("tagline", fontName="Times-Roman", fontSize=11.5, leading=14, alignment=TA_CENTER, textColor=INK)
CONTACT = ParagraphStyle("contact", fontName="Times-Roman", fontSize=10, leading=13, alignment=TA_CENTER, textColor=INK)
SECTION = ParagraphStyle("section", fontName="Times-Bold", fontSize=12.5, leading=15, textColor=INK, spaceBefore=7)
HEAD_L = ParagraphStyle("head_l", fontName="Times-Bold", fontSize=11.5, leading=14, textColor=INK)
HEAD_R = ParagraphStyle("head_r", fontName="Times-Bold", fontSize=10, leading=14, textColor=INK, alignment=2)
BODY = ParagraphStyle("body", fontName="Times-Roman", fontSize=10, leading=12.5, textColor=INK)
SKILL = ParagraphStyle("skill", parent=BODY, leftIndent=0, spaceAfter=2)


def clean(value) -> str:
    """Text safe for the built-in fonts, XML-escaped for Paragraph markup."""
    if value is None:
        return ""
    text = str(value).replace("\t", " ")
    text = text.encode(_ENCODING, errors="replace").decode(_ENCODING)
    return escape(text)


def format_date(value) -> str:
    """'Jan 05, 2024' for dates / ISO strings; 'Present' for empty values."""
    if value in (None, "", "None"):
        return "Present"
    if isinstance(value, (datetime, date)):
        return f"{_MONTHS[value.month - 1]} {value.day:02d}, {value.year}"
    try:
        year, month, day = str(value).split("-")[:3]
        return f"{_MONTHS[int(month) - 1]} {int(day):02d}, {year}"
    except (ValueError, IndexError):
        return str(value)


def _sort_key(value) -> str:
    return "" if value is None else str(value)


def _full_name(user: Dict) -> str:
    return " ".join(p for p in (user.get("first_name"), user.get("middle_name"), user.get("last_name")) if p)


def _link(url: str, label: str) -> str:
    return f'<a href={quoteattr(url)} color="#0E5484">{clean(label)}</a>'


def _short(url: str) -> str:
    return str(url).replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")


def _contact_lines(user: Dict) -> List[str]:
    items = []
    if user.get("phone"):
        items.append(_link("tel:" + str(user["phone"]), user["phone"]))
    if user.get("email"):
        items.append(_link("mailto:" + str(user["email"]), user["email"]))
    for key, prefix in (("linkedin_url", ""), ("github_url", ""), ("hackerrank_url", ""), ("leetcode_url", "LeetCode: ")):
        if user.get(key):
            items.append(_link(str(user[key]), prefix + _short(user[key])))
    # three links per line, like the previous layout
    return ["&nbsp;&nbsp;|&nbsp;&nbsp;".join(items[i:i + 3]) for i in range(0, len(items), 3)]


def _section(title: str, width: float) -> list:
    return [Paragraph(clean(title.upper()), SECTION),
            HRFlowable(width=width, thickness=0.8, color=INK, spaceBefore=1, spaceAfter=4)]


def _bullets(lines: List[str]) -> Optional[ListFlowable]:
    items = [ListItem(Paragraph(clean(line.strip()), BODY), leftIndent=14, bulletColor=INK) for line in lines if line and line.strip()]
    if not items:
        return None
    return ListFlowable(items, bulletType="bullet", start="•", leftIndent=14, bulletFontSize=9, bulletOffsetY=-1)


def _heading(left: str, right: str, width: float) -> Table:
    table = Table([[Paragraph(clean(left), HEAD_L), Paragraph(clean(right), HEAD_R)]], colWidths=[width * 0.68, width * 0.32])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return table


def _entry(left: str, right: str, lines: List[str], width: float, extra_first: Optional[str] = None) -> list:
    """One heading row plus its bullet list. The heading stays on the same page as the first bullet."""
    all_lines = ([extra_first] if extra_first else []) + list(lines)
    bullets = _bullets(all_lines)
    head = _heading(left, right, width)
    out = [KeepTogether([head, bullets]) if bullets else head]
    out.append(Spacer(1, 4))
    return out


def _dates(start, end) -> str:
    return f"{format_date(start)} – {format_date(end)}"


def build_resume_pdf(user_data: Dict, experiences: List[Dict], educations: List[Dict], projects: List[Dict],
                     skills: List[Dict], certifications: List[Dict], awards: List[Dict]) -> bytes:
    buffer = BytesIO()
    margin = 0.55 * inch
    name = _full_name(user_data) or "Resume"
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=margin, rightMargin=margin, topMargin=0.5 * inch,
                            bottomMargin=0.5 * inch, title=f"{name} - Resume", author=name)
    width = doc.width  # usable frame width (page minus margins and frame padding)
    story: list = [Paragraph(clean(name.upper()), NAME)]

    if user_data.get("portfolio_title"):
        story.append(Paragraph(clean(user_data["portfolio_title"]), TAGLINE))
    for line in _contact_lines(user_data):
        story.append(Paragraph(line, CONTACT))
    story.append(Spacer(1, 2))

    if skills:
        by_category: Dict[str, List[str]] = {}
        for skill in skills:
            by_category.setdefault(skill.get("category") or "Other", []).append(skill.get("name", ""))
        story += _section("Technical Skills", width)
        for category, names in by_category.items():
            story.append(Paragraph(f"<b>{clean(category)}:</b> {', '.join(clean(n) for n in names)}", SKILL))

    if experiences:
        story += _section("Experience", width)
        for e in sorted(experiences, key=lambda x: _sort_key(x.get("start_date")), reverse=True):
            story += _entry(f"{e.get('title', '')} ({e.get('company', '')})", _dates(e.get("start_date"), e.get("end_date")),
                            (e.get("description") or "").split("\n"), width)

    if educations:
        story += _section("Education", width)
        for e in sorted(educations, key=lambda x: _sort_key(x.get("start_date")), reverse=True):
            degree = e.get("degree")
            story += _entry(e.get("institution", ""), _dates(e.get("start_date"), e.get("end_date")),
                            (e.get("description") or "").split("\n"), width, extra_first=degree)

    if projects:
        story += _section("Projects", width)
        for p in sorted(projects, key=lambda x: _sort_key(x.get("start_date")), reverse=True):
            tech = ", ".join(str(t) for t in (p.get("technologies") or []))
            story += _entry(p.get("title", ""), _dates(p.get("start_date"), p.get("end_date")),
                            (p.get("description") or "").split("\n"), width, extra_first=f"Technologies: {tech}" if tech else None)

    if awards:
        story += _section("Achievements", width)
        for a in awards:
            story += _entry(f"{a.get('name', '')} ({a.get('issuer', '')})", format_date(a.get("issue_date")),
                            (a.get("description") or "").split("\n"), width)

    if certifications:
        story += _section("Certifications", width)
        for c in certifications:
            story += _entry(f"{c.get('name', '')} ({c.get('issuer', '')})", format_date(c.get("issue_date")),
                            (c.get("description") or "").split("\n"), width)

    doc.build(story)
    return buffer.getvalue()
