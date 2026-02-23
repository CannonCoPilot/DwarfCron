"""FastAPI application factory for the Chronicler web UI."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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

app.include_router(storyteller_router, prefix="/api")
app.include_router(world_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(explorer_router, prefix="/api")
app.include_router(people_router, prefix="/api")
app.include_router(civilizations_router, prefix="/api")
app.include_router(geography_router, prefix="/api")
app.include_router(events_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main Chronicler UI."""
    return templates.TemplateResponse("index.html", {"request": request, "active": "chat"})


@app.get("/explorer", response_class=HTMLResponse)
async def explorer_page(request: Request):
    """Serve the database explorer."""
    return templates.TemplateResponse("explorer.html", {"request": request, "active": "explorer"})


@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Serve the monitoring dashboard."""
    return templates.TemplateResponse("monitoring.html", {"request": request, "active": "monitoring"})
