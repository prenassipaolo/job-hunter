"""FastAPI dashboard to browse a persona's shortlist locally.

11a is read-only: pick a persona, see its latest ranked roles. Filters, manual re-tier
and re-run actions arrive in later steps. Build the app with ``create_app(data_dir)`` so
it knows where ``personas/`` and ``roles/`` live.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from job_hunter.storage import load_latest_roles

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _personas(data_dir: Path) -> list[str]:
    """Available persona ids (yaml files under data/personas, minus the template)."""
    pdir = data_dir / "personas"
    return sorted(p.stem for p in pdir.glob("*.yaml") if p.stem != "_template")


def create_app(data_dir: str | Path) -> FastAPI:
    data_dir = Path(data_dir)
    app = FastAPI(title="job-hunter")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, persona: str = ""):
        personas = _personas(data_dir)
        if not persona and personas:
            persona = personas[0]
        roles = load_latest_roles(data_dir / "roles" / persona) if persona else []
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {"personas": personas, "persona": persona, "roles": roles},
        )

    return app
