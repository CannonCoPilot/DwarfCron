"""Watcher Control Center API — monitor, configure, and control the live data pipeline."""

import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

log = logging.getLogger(__name__)

router = APIRouter()

# ── Paths ────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).resolve().parents[3] / "chronicler" / "data"
_LIVE_DIR = _DATA_DIR / "live"
_BRIDGE_LOGS_DIR = Path(__file__).resolve().parents[3] / "data" / "bridge-logs"


def _file_age_seconds(path: Path) -> float | None:
    """Seconds since file was last modified, or None if missing."""
    try:
        return time.time() - path.stat().st_mtime
    except FileNotFoundError:
        return None


# ── Watcher Dashboard Page ───────────────────────────────────────────

@router.get("/watcher", response_class=HTMLResponse)
async def watcher_dashboard(request: Request):
    """Serve the Watcher Control Center page."""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(
        directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    )
    return templates.TemplateResponse("watcher.html", {"request": request})


# ── Watcher Status API ───────────────────────────────────────────────

@router.get("/api/watcher/status")
async def watcher_status(request: Request, world_id: int = 1):
    """Comprehensive watcher pipeline status — for auto-refresh polling."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Snapshot stats
        snap_count = await conn.fetchval(
            "SELECT count(*) FROM fortress_state_snapshots WHERE world_id = $1",
            world_id,
        )
        latest_snap = await conn.fetchrow(
            """SELECT tick, year, season, population, food_stocks, drink_stocks,
                      captured_at
               FROM fortress_state_snapshots WHERE world_id = $1
               ORDER BY captured_at DESC LIMIT 1""",
            world_id,
        )

        # Unit event stats
        event_count = await conn.fetchval(
            "SELECT count(*) FROM unit_events WHERE world_id = $1", world_id
        )
        event_types = await conn.fetch(
            """SELECT event_type, count(*) c
               FROM unit_events WHERE world_id = $1
               GROUP BY event_type ORDER BY c DESC LIMIT 10""",
            world_id,
        )

        # Unit stats
        unit_count = await conn.fetchval(
            "SELECT count(*) FROM units WHERE world_id = $1", world_id
        )
        alive_units = await conn.fetchval(
            "SELECT count(*) FROM units WHERE world_id = $1 AND is_alive = true",
            world_id,
        )

        # HF linkage
        linked_hfs = await conn.fetchval(
            "SELECT count(*) FROM historical_figures WHERE world_id = $1 AND unit_id IS NOT NULL",
            world_id,
        )

        # Denizens
        denizen_count = await conn.fetchval(
            "SELECT count(*) FROM fortress_denizens WHERE world_id = $1", world_id
        )

        # Expanded ETL counts
        squads = await conn.fetchval(
            "SELECT count(*) FROM squads WHERE world_id = $1", world_id
        )
        beliefs = await conn.fetchval(
            "SELECT count(*) FROM belief_systems WHERE world_id = $1", world_id
        )

    # Bridge file freshness
    live_dir = _LIVE_DIR
    bridge_files = []
    if live_dir.exists():
        for f in sorted(live_dir.iterdir()):
            if f.suffix == ".json" and not f.name.startswith("_"):
                age = _file_age_seconds(f)
                bridge_files.append({
                    "name": f.name,
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "age_seconds": round(age, 1) if age else None,
                })

    # JSONL session logs
    session_logs = []
    if _BRIDGE_LOGS_DIR.exists():
        for world_dir in sorted(_BRIDGE_LOGS_DIR.iterdir()):
            if world_dir.is_dir():
                for logfile in sorted(world_dir.glob("session-*.jsonl"),
                                      key=lambda p: p.stat().st_mtime,
                                      reverse=True)[:3]:
                    age = _file_age_seconds(logfile)
                    session_logs.append({
                        "name": logfile.name,
                        "world": world_dir.name,
                        "size_mb": round(logfile.stat().st_size / (1024 * 1024), 1),
                        "age_seconds": round(age, 1) if age else None,
                    })

    # Bridge connectivity
    from chronicler.config import DFHACK_HOST, BRIDGE_PORT
    bridge_connected = False
    bridge_info = {}
    try:
        from chronicler.dfhack.bridge import fetch_bridge_data
        bd = fetch_bridge_data(DFHACK_HOST, BRIDGE_PORT)
        if bd:
            bridge_connected = True
            bridge_info = {
                "version": bd.get("bridge_version"),
                "game_year": bd.get("cur_year"),
                "game_tick": bd.get("cur_year_tick"),
                "season": bd.get("cur_season"),
                "creature_count": bd.get("creature_count", 0),
                "sections": len([k for k in bd.keys()
                                 if k not in ("cur_year", "cur_year_tick", "cur_season",
                                              "creature_raws", "creature_count",
                                              "timestamp", "bridge_version", "errors")]),
            }
    except Exception as e:
        bridge_info = {"error": str(e)}

    return {
        "bridge": {
            "connected": bridge_connected,
            **bridge_info,
        },
        "database": {
            "snapshots": snap_count,
            "events": event_count,
            "units": unit_count,
            "alive_units": alive_units,
            "linked_hfs": linked_hfs,
            "denizens": denizen_count,
            "squads": squads,
            "beliefs": beliefs,
        },
        "latest_snapshot": {
            "tick": latest_snap["tick"] if latest_snap else None,
            "year": latest_snap["year"] if latest_snap else None,
            "season": latest_snap["season"] if latest_snap else None,
            "population": latest_snap["population"] if latest_snap else None,
            "food": latest_snap["food_stocks"] if latest_snap else None,
            "drink": latest_snap["drink_stocks"] if latest_snap else None,
            "captured_at": latest_snap["captured_at"].isoformat() if latest_snap else None,
        },
        "event_types": [{"type": r["event_type"], "count": r["c"]} for r in event_types],
        "bridge_files": bridge_files,
        "session_logs": session_logs,
    }


@router.get("/api/watcher/snapshots")
async def watcher_snapshots(request: Request, world_id: int = 1, limit: int = 100):
    """Time-series snapshot data for charts."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT tick, year, season, population, food_stocks, drink_stocks,
                      wealth, captured_at
               FROM fortress_state_snapshots WHERE world_id = $1
               ORDER BY captured_at ASC LIMIT $2""",
            world_id, limit,
        )
    return [
        {
            "tick": r["tick"],
            "year": r["year"],
            "season": r["season"],
            "population": r["population"],
            "food": r["food_stocks"],
            "drink": r["drink_stocks"],
            "wealth": r["wealth"],
            "ts": r["captured_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/api/watcher/events/recent")
async def watcher_recent_events(request: Request, world_id: int = 1, limit: int = 50):
    """Most recent unit events for the activity log."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT ue.event_type, ue.unit_id, ue.old_value, ue.new_value,
                      ue.game_year, ue.game_tick, ue.detected_at,
                      u.name AS unit_name, u.english_name
               FROM unit_events ue
               LEFT JOIN units u ON u.id = ue.unit_id AND u.world_id = ue.world_id
               WHERE ue.world_id = $1
               ORDER BY ue.detected_at DESC LIMIT $2""",
            world_id, limit,
        )
    return [
        {
            "event_type": r["event_type"],
            "unit_id": r["unit_id"],
            "unit_name": r["unit_name"] or f"Unit #{r['unit_id']}",
            "english_name": r["english_name"],
            "old_value": r["old_value"],
            "new_value": r["new_value"],
            "game_year": r["game_year"],
            "game_tick": r["game_tick"],
            "detected_at": r["detected_at"].isoformat() if r["detected_at"] else None,
        }
        for r in rows
    ]
