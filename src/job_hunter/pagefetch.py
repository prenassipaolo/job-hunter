"""Best-effort re-fetch of a live job page (phase 2).

Phase 1 keeps whatever description the API gave us. Phase 2 re-visits the link to
pull fuller, fresher text before handing it to the AI. Many career sites are
JS-rendered or bot-protected, so this is strictly best-effort: on any failure we keep
the phase-1 description and move on.
"""

from __future__ import annotations

import httpx

from .providers.base import strip_html

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_page_text(url: str, timeout: float = 15.0, limit: int = 8000) -> str | None:
    """Return cleaned page text, or None if the page can't be fetched usefully."""
    if not url:
        return None
    try:
        with httpx.Client(timeout=timeout, headers=_HEADERS, follow_redirects=True) as client:
            r = client.get(url)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            return None
        text = strip_html(r.text, limit=limit)
        # Guard against landing pages / walls that return almost no real content.
        return text if len(text) > 400 else None
    except httpx.HTTPError:
        return None
