"""
Can a project's live site be shown in an <iframe> on the portfolio?

Browsers refuse to embed a page that sends `X-Frame-Options: DENY|SAMEORIGIN` or a CSP `frame-ancestors`
that does not list the embedding site. The frontend cannot read those headers of another site, so it asks
here first and only renders a live preview for sites that allow it.

Only the `live_url` stored on a project is ever fetched (never a URL supplied in the request), private and
internal addresses are refused, and results are cached for a few minutes.
"""
import asyncio
import ipaddress
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.project import Project

router = APIRouter()

CACHE_SECONDS = 600
MAX_REDIRECTS = 3
_cache: Dict[str, Tuple[float, dict]] = {}


_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _ip_is_public(value: str) -> bool:
    """True only for globally routable addresses. IPv4-mapped and NAT64 (DNS64) IPv6 addresses are judged by the IPv4 inside."""
    ip = ipaddress.ip_address(value.split('%')[0])
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        elif ip in _NAT64:
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip.is_global and not ip.is_multicast


async def _host_is_public(host: str) -> bool:
    """False if the host resolves to any loopback / private / link-local / reserved address (blocks internal services)."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    except OSError:
        return False
    return bool(infos) and all(_ip_is_public(info[4][0]) for info in infos)


async def _fetch_headers(url: str) -> Tuple[int, Dict[str, str], str]:
    """GET the page headers only (body is never read). Follows a few redirects, re-checking every hop."""
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=False,
                                 headers={"User-Agent": "PortfolioHub-PreviewCheck/1.0"}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            parts = urlparse(url)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                raise ValueError("unsupported URL")
            if not await _host_is_public(parts.hostname):
                raise ValueError("address is not public")
            async with client.stream("GET", url) as response:
                if response.is_redirect and response.headers.get("location"):
                    url = urljoin(url, response.headers["location"])
                    continue
                headers = {k.lower(): v for k, v in response.headers.items()}
                return response.status_code, headers, url
    raise ValueError("too many redirects")


def _origin_allowed(source: str, origin: str) -> bool:
    source, origin = source.lower().rstrip('/'), origin.lower().rstrip('/')
    if source == origin or source == '*':
        return True
    if source in ("https:", "http:"):
        return origin.startswith(source + "//")
    if '*' in source:  # e.g. https://*.example.com
        scheme, _, host = source.partition('://')
        o_scheme, _, o_host = origin.partition('://')
        return (not scheme or scheme == o_scheme) and host.startswith('*.') and o_host.endswith(host[1:])
    return False


def evaluate_embedding(headers: Dict[str, str], embedder_origin: str) -> Tuple[bool, Optional[str]]:
    """Would a browser let `embedder_origin` embed a page with these response headers?"""
    csp = headers.get("content-security-policy", "")
    for directive in csp.split(";"):
        tokens = directive.strip().split()
        if tokens and tokens[0].lower() == "frame-ancestors":
            sources = tokens[1:]
            if any(_origin_allowed(s, embedder_origin) for s in sources):
                return True, None
            return False, "the site's Content-Security-Policy frame-ancestors does not allow this portfolio"
    xfo = headers.get("x-frame-options", "").strip().lower()
    if xfo in ("deny", "sameorigin"):
        return False, f"the site sends X-Frame-Options: {xfo.upper()}"
    return True, None


@router.get("/embeddable/{project_id}")
async def project_is_embeddable(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    url = (project.live_url or "").strip() if project else ""
    if not url or not url.lower().startswith(("http://", "https://")):
        return {"embeddable": False, "reason": "no live URL"}

    now = time.time()
    hit = _cache.get(url)
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]

    try:
        status, headers, _final = await _fetch_headers(url)
        if status >= 400:
            result = {"embeddable": False, "reason": f"the site answered with HTTP {status}"}
        else:
            ok, reason = evaluate_embedding(headers, settings.public_frontend_url)
            result = {"embeddable": ok, "reason": reason}
    except (httpx.HTTPError, ValueError) as exc:
        result = {"embeddable": False, "reason": f"could not check the site ({exc})"}

    if len(_cache) > 1000:
        _cache.clear()
    _cache[url] = (now, result)
    return result
