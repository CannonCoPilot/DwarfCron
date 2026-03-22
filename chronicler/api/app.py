"""FastAPI application factory for the Chronicler web UI."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from chronicler.db.connection import get_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DB pool lifecycle."""
    pool = await get_pool()
    app.state.pool = pool
    yield
    await close_pool()


app = FastAPI(title="Chronicler", lifespan=lifespan)

_template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_template_dir)

# Import and include routers
from chronicler.api.routes.storyteller import router as storyteller_router
from chronicler.api.routes.world import router as world_router
from chronicler.api.routes.monitoring import router as monitoring_router
from chronicler.api.routes.explorer import router as explorer_router
from chronicler.api.routes.people import router as people_router
from chronicler.api.routes.civilizations import router as civilizations_router
from chronicler.api.routes.geography import router as geography_router
from chronicler.api.routes.events import router as events_router
from chronicler.api.routes.detail_pages import router as detail_pages_router
from chronicler.api.routes.statistics import router as statistics_router
from chronicler.api.routes.demographics import router as demographics_router
from chronicler.api.routes.deity_stats import router as deity_stats_router
from chronicler.api.routes.live import router as live_router
from chronicler.api.routes.narrative import router as narrative_router

app.include_router(storyteller_router, prefix="/api")
app.include_router(world_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(explorer_router, prefix="/api")
app.include_router(people_router, prefix="/api")
app.include_router(civilizations_router, prefix="/api")
app.include_router(geography_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(detail_pages_router)  # No prefix — routes already include /explorer/
app.include_router(statistics_router, prefix="/api")
app.include_router(demographics_router, prefix="/api")
app.include_router(deity_stats_router, prefix="/api")
app.include_router(live_router)  # /fortress, /ws/events at root; /api/live/* via explicit paths
app.include_router(narrative_router, prefix="/api")  # Stage 3.6 narrative endpoints


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Serve the landing page — world selection + getting started."""
    return templates.TemplateResponse("landing.html", {"request": request, "active": "home"})


@app.get("/explorer", response_class=HTMLResponse)
async def explorer_page(request: Request):
    """Serve the database explorer."""
    return templates.TemplateResponse("explorer.html", {"request": request, "active": "explorer"})


@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Serve the monitoring dashboard."""
    return templates.TemplateResponse("monitoring.html", {"request": request, "active": "monitoring"})


# ── Knowledge Horizon API ────────────────────────────────────────────

@app.get("/api/kh/status")
async def kh_status(request: Request, world_id: int = 1):
    """Check KH state: whether it's initialized and how many entities are visible."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM knowledge_horizon "
            "WHERE world_id = $1 AND visible = TRUE",
            world_id,
        )
    return {"initialized": count > 0, "visible_count": count, "world_id": world_id}


@app.get("/api/kh/check/{entity_type}/{entity_id}")
async def kh_check_visibility(entity_type: str, entity_id: int,
                               request: Request, world_id: int = 1):
    """Check if a specific entity is visible under KH."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        visible = await conn.fetchval(
            "SELECT visible FROM knowledge_horizon "
            "WHERE world_id = $1 AND entity_type = $2 AND entity_id = $3",
            world_id, entity_type, entity_id,
        )
    return {"visible": bool(visible), "entity_type": entity_type, "entity_id": entity_id}
