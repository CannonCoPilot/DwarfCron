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

app.include_router(storyteller_router, prefix="/api")
app.include_router(world_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main Chronicler UI."""
    return templates.TemplateResponse("index.html", {"request": request})
