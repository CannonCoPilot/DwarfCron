"""Live fortress dashboard — WebSocket event feed, DotD, army tracking."""

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from chronicler.config import DFHACK_HOST, BRIDGE_PORT

log = logging.getLogger(__name__)

router = APIRouter()

# ── WebSocket client management ─────────────────────────────────────

_ws_clients: set[WebSocket] = set()
_bridge_poll_task: asyncio.Task | None = None
# Deduplication state: track what we've already seen from the bridge
_poll_state: dict[str, Any] = {
    "last_tick": -1,             # bridge cycle cursor — skip if unchanged
    "last_report_cursor": -1,    # announcement ID high-water mark
    "last_skill_hash": "",       # fingerprint of skill_changes to detect real changes
    "last_population": -1,       # population change detection
    "last_hostile_count": -1,    # threat level change detection
    "last_season": "",           # season transition detection
}


async def _broadcast(message: dict):
    """Send JSON message to all connected WebSocket clients."""
    if not _ws_clients:
        return
    payload = json.dumps(message)
    closed = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            closed.add(ws)
    _ws_clients.difference_update(closed)


async def _poll_bridge():
    """Background task: poll bridge data and broadcast only genuinely new events.

    Deduplication strategy:
    - Track the bridge's cur_year_tick as a cycle cursor. The bridge writes a
      new JSON file each repeat cycle (~100 ticks). If the tick hasn't changed,
      we're reading the same file — skip entirely.
    - Reactive events (deaths, jobs, items, invasions, syndromes) are flushed
      by the Lua bridge each cycle, so they're always fresh when the tick changes.
    - Announcements use cursor-based dedup (report ID high-water mark).
    - Skill changes use a content hash to detect actual changes vs. stale data.
    """
    from chronicler.dfhack.bridge import fetch_bridge_data
    import hashlib

    while True:
        try:
            if _ws_clients:
                data = fetch_bridge_data(DFHACK_HOST, BRIDGE_PORT)
                if data:
                    tick = data.get("cur_year_tick", 0)

                    # Skip if we've already processed this bridge cycle
                    if tick != _poll_state["last_tick"]:
                        _poll_state["last_tick"] = tick
                        events = _extract_new_events(data)
                        for ev in events:
                            await _broadcast(ev)
        except Exception as e:
            log.debug("Bridge poll error: %s", e)
        await asyncio.sleep(3.0)


def _extract_new_events(data: dict) -> list[dict]:
    """Extract genuinely new events from a fresh bridge cycle."""
    import hashlib

    events = []
    now = time.time()
    game_tick = data.get("cur_year_tick", 0)
    game_year = data.get("cur_year", 0)

    def _make_event(etype: str, edata: dict) -> dict:
        return {
            "type": etype,
            "data": edata,
            "game_year": game_year,
            "game_tick": game_tick,
            "timestamp": now,
        }

    # ── Reactive events (flushed each bridge cycle — always fresh) ──
    reactive = data.get("reactive_events", {})

    for death in (reactive.get("unit_deaths") or []):
        events.append(_make_event("death", death))

    for unit in (reactive.get("new_units") or []):
        events.append(_make_event("birth", unit))

    for job in (reactive.get("jobs_completed") or []):
        events.append(_make_event("job", job))

    for inv in (reactive.get("invasions") or []):
        events.append(_make_event("invasion", inv))

    for syn in (reactive.get("syndromes") or []):
        events.append(_make_event("syndrome", syn))

    # ── Announcements (cursor-based dedup) ──
    announcements = data.get("announcements", {})
    reports = announcements.get("reports", [])
    cursor = _poll_state["last_report_cursor"]
    for report in reports:
        rid = report.get("id", -1)
        if rid > cursor:
            events.append(_make_event("announcement", {
                "text": report.get("text", ""),
                "id": rid,
            }))
            _poll_state["last_report_cursor"] = max(
                _poll_state["last_report_cursor"], rid
            )

    # ── Skill changes (content-hash dedup) ──
    skill_changes = data.get("skill_changes") or []
    if skill_changes:
        # Hash the skill data to detect real changes vs stale repeats
        skill_hash = hashlib.md5(
            json.dumps(skill_changes, sort_keys=True).encode()
        ).hexdigest()[:12]
        if skill_hash != _poll_state["last_skill_hash"]:
            _poll_state["last_skill_hash"] = skill_hash
            for change in skill_changes:
                events.append(_make_event("skill_up", change))

    # ── Fortress state changes (population, threats, season) ──
    fortress_state = data.get("fortress_state", {})
    if isinstance(fortress_state, dict):
        pop = fortress_state.get("population")
        if pop is not None and pop != _poll_state["last_population"]:
            old_pop = _poll_state["last_population"]
            _poll_state["last_population"] = pop
            if old_pop >= 0:  # Don't emit on first cycle
                delta = pop - old_pop
                if delta > 0:
                    events.append(_make_event("population", {
                        "population": pop, "delta": delta,
                        "text": f"Population increased to {pop} (+{delta})",
                    }))
                elif delta < 0:
                    events.append(_make_event("population", {
                        "population": pop, "delta": delta,
                        "text": f"Population decreased to {pop} ({delta})",
                    }))

    # Threat level changes from unit_summary hostile count
    unit_summary = data.get("unit_summary", {})
    units_list = (unit_summary.get("units") if isinstance(unit_summary, dict)
                  else unit_summary) or []
    hostile_count = sum(1 for u in units_list
                        if isinstance(u, dict) and u.get("active_invader"))
    if hostile_count != _poll_state["last_hostile_count"]:
        old_hostile = _poll_state["last_hostile_count"]
        _poll_state["last_hostile_count"] = hostile_count
        if old_hostile >= 0 and hostile_count > old_hostile:
            events.append(_make_event("threat", {
                "hostile_count": hostile_count,
                "delta": hostile_count - old_hostile,
                "text": f"Hostile entities: {hostile_count} (+{hostile_count - old_hostile})",
            }))
        elif old_hostile >= 0 and hostile_count < old_hostile and hostile_count == 0:
            events.append(_make_event("threat_clear", {
                "text": "All threats eliminated",
            }))

    # Season transition
    season = data.get("cur_season", "")
    if season and season != _poll_state["last_season"]:
        old_season = _poll_state["last_season"]
        _poll_state["last_season"] = season
        if old_season:
            events.append(_make_event("season", {
                "season": season, "year": game_year,
                "text": f"{season} of Year {game_year}",
            }))

    return events


# ── WebSocket endpoint ──────────────────────────────────────────────

@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Stream live game events to the client."""
    global _bridge_poll_task

    await websocket.accept()
    _ws_clients.add(websocket)
    log.info("WS client connected (%d total)", len(_ws_clients))

    # Start background poller if not running
    if _bridge_poll_task is None or _bridge_poll_task.done():
        _bridge_poll_task = asyncio.create_task(_poll_bridge())

    try:
        while True:
            # Keep connection alive; client may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        log.info("WS client disconnected (%d remaining)", len(_ws_clients))


# ── Fortress dashboard page ────────────────────────────────────────

@router.get("/fortress", response_class=HTMLResponse)
async def fortress_dashboard(request: Request):
    """Serve the live fortress dashboard."""
    from chronicler.dfhack.bridge import fetch_bridge_data
    from fastapi.templating import Jinja2Templates
    import os

    templates = Jinja2Templates(
        directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    )

    # Fetch initial bridge state
    bridge = fetch_bridge_data(DFHACK_HOST, BRIDGE_PORT) or {}
    world_info = bridge.get("world_info", {})

    context = {
        "request": request,
        "game_year": bridge.get("cur_year", "?"),
        "game_tick": bridge.get("cur_year_tick", 0),
        "season": bridge.get("cur_season", "?"),
        "fortress_name": world_info.get("fortress_name", "Unknown Fortress"),
        "world_name": world_info.get("world_name", "Unknown World"),
        "unit_count": len(bridge.get("unit_summary", [])),
        "bridge_version": bridge.get("bridge_version", "?"),
    }
    return templates.TemplateResponse("fortress.html", context)


# ── Live API endpoints ──────────────────────────────────────────────

@router.get("/api/live/status")
async def live_status():
    """Current bridge state summary for auto-refresh."""
    from chronicler.dfhack.bridge import fetch_bridge_data

    data = fetch_bridge_data(DFHACK_HOST, BRIDGE_PORT)
    if not data:
        return {"connected": False}

    world_info = data.get("world_info", {})
    reactive = data.get("reactive_events", {})
    return {
        "connected": True,
        "game_year": data.get("cur_year"),
        "game_tick": data.get("cur_year_tick"),
        "season": data.get("cur_season"),
        "fortress_name": world_info.get("fortress_name"),
        "world_name": world_info.get("world_name"),
        "unit_count": len(data.get("unit_summary", [])),
        "bridge_version": data.get("bridge_version"),
        "event_counts": {
            k: v for k, v in reactive.items()
            if k != "total_count" and isinstance(v, (list, int))
        },
    }


@router.get("/api/live/dwarf-of-the-day")
async def dwarf_of_the_day(request: Request, world_id: int = 1):
    """Deprecated — redirects to random denizen. Use /api/live/denizens + /api/live/denizen/{id}."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id FROM units
            WHERE world_id = $1 AND is_alive = true AND race = 'DWARF'
              AND civ_id = (
                  SELECT civ_id FROM units
                  WHERE world_id = $1 AND race = 'DWARF' AND is_alive = true
                  GROUP BY civ_id ORDER BY count(*) DESC LIMIT 1
              )
            ORDER BY random() LIMIT 1
            """,
            world_id,
        )
        if not row:
            return {"error": "No living citizens found"}
        # Forward to denizen detail
        return await denizen_detail(request, row["id"], world_id)


@router.get("/api/live/denizens")
async def denizen_list(request: Request, world_id: int = 1):
    """List all living fortress denizens for dropdown selection."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.id, u.name, u.race, u.profession, u.civ_id,
                   u.hist_fig_id, u.birth_year,
                   u.details->'squad_id' AS squad_id,
                   u.details->'custom_profession' AS custom_prof
            FROM units u
            WHERE u.world_id = $1
              AND u.is_alive = true
              AND u.civ_id = (
                  SELECT civ_id FROM units
                  WHERE world_id = $1 AND race = 'DWARF' AND is_alive = true
                  GROUP BY civ_id ORDER BY count(*) DESC LIMIT 1
              )
            ORDER BY u.name ASC
            """,
            world_id,
        )
        return [
            {
                "id": r["id"],
                "name": r["name"] or f"Unit #{r['id']}",
                "race": r["race"],
                "profession": r["profession"],
                "custom_profession": r["custom_prof"],
                "hist_fig_id": r["hist_fig_id"],
                "birth_year": r["birth_year"],
                "squad_id": r["squad_id"],
            }
            for r in rows
        ]


def _parse_details(raw) -> dict:
    """Safely parse details JSONB — handles str or dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


@router.get("/api/live/denizen/{unit_id}")
async def denizen_detail(request: Request, unit_id: int, world_id: int = 1):
    """Full character sheet for a fortress denizen — as detailed as in-game."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # ── Core unit data ──
        unit = await conn.fetchrow(
            """
            SELECT u.id, u.name, u.english_name, u.race, u.caste, u.profession,
                   u.civ_id, u.hist_fig_id, u.birth_year, u.sex,
                   u.pos_x, u.pos_y, u.pos_z, u.is_alive, u.death_cause,
                   u.details, u.last_synced_at
            FROM units u
            WHERE u.id = $1 AND u.world_id = $2
            """,
            unit_id, world_id,
        )
        if not unit:
            return {"error": "Unit not found"}

        details = _parse_details(unit["details"])
        result = {
            "id": unit["id"],
            "name": unit["name"],
            "english_name": unit["english_name"],
            "race": unit["race"],
            "caste": unit["caste"],
            "profession": unit["profession"],
            "custom_profession": details.get("custom_profession"),
            "civ_id": unit["civ_id"],
            "hist_fig_id": unit["hist_fig_id"],
            "birth_year": unit["birth_year"],
            "sex": unit["sex"],
            "position": {"x": unit["pos_x"], "y": unit["pos_y"], "z": unit["pos_z"]},
            "is_alive": unit["is_alive"],
            "death_cause": unit["death_cause"],
            "last_synced_at": unit["last_synced_at"].isoformat() if unit["last_synced_at"] else None,
        }

        # ── Skills (sorted by level desc) ──
        skills = details.get("skills", [])
        if skills:
            skills = sorted(skills, key=lambda s: (-s.get("level", 0), -s.get("xp", 0)))
        result["skills"] = skills

        # ── Personality ──
        personality = details.get("personality", {})
        result["personality"] = {
            "traits": personality.get("traits", {}),
            "values": personality.get("values", []),
            "needs": personality.get("needs", []),
            "dreams": personality.get("dreams", []),
            "mental_attrs": personality.get("mental_attrs", {}),
            "physical_attrs": personality.get("physical_attrs", {}),
        }

        # ── Stress / Mood / Squad ──
        result["stress_level"] = details.get("stress_level") or personality.get("stress")
        result["mood"] = details.get("mood")
        result["squad_id"] = details.get("squad_id")
        result["squad_position"] = details.get("squad_position")
        result["labors"] = details.get("labors", [])
        result["cultural_identity"] = details.get("cultural_identity")

        # ── Family (from hf_links) ──
        family = {}
        if unit["hist_fig_id"] and unit["hist_fig_id"] > 0:
            hf_id = unit["hist_fig_id"]
            links = await conn.fetch(
                """
                SELECT hl.link_type, hl.target_hf_id,
                       hf.name AS target_name, hf.race AS target_race,
                       hf.is_alive AS target_alive
                FROM hf_links hl
                LEFT JOIN historical_figures hf
                    ON hf.id = hl.target_hf_id AND hf.world_id = hl.world_id
                WHERE hl.hf_id = $1 AND hl.world_id = $2
                  AND hl.link_type IN ('father', 'mother', 'spouse', 'child',
                                       'deceased spouse', 'lover', 'former spouse')
                """,
                hf_id, world_id,
            )
            for link in links:
                lt = link["link_type"]
                entry = {
                    "hf_id": link["target_hf_id"],
                    "name": link["target_name"],
                    "race": link["target_race"],
                    "is_alive": link["target_alive"],
                }
                if lt in ("child",):
                    family.setdefault("children", []).append(entry)
                else:
                    family[lt.replace(" ", "_")] = entry

            # HF biographical data
            hf = await conn.fetchrow(
                """
                SELECT name, race, caste, birth_year, death_year,
                       is_deity, is_force, kill_count, details
                FROM historical_figures
                WHERE id = $1 AND world_id = $2
                """,
                hf_id, world_id,
            )
            if hf:
                result["hf"] = {
                    "name": hf["name"],
                    "birth_year": hf["birth_year"],
                    "death_year": hf["death_year"],
                    "kill_count": hf["kill_count"],
                }
        result["family"] = family

        # ── Recent events (last 20) ──
        events = await conn.fetch(
            """
            SELECT event_type, old_value, new_value, game_year, game_tick, detected_at
            FROM unit_events
            WHERE unit_id = $1 AND world_id = $2
            ORDER BY game_year DESC, game_tick DESC
            LIMIT 20
            """,
            unit_id, world_id,
        )
        result["recent_events"] = [
            {
                "event_type": e["event_type"],
                "old_value": e["old_value"],
                "new_value": e["new_value"],
                "game_year": e["game_year"],
                "game_tick": e["game_tick"],
            }
            for e in events
        ]

        return result


# ── Worldgen Monitoring ─────────────────────────────────────────────

# Shared worldgen ingester instance
_worldgen_ingester = None


def _get_worldgen_ingester():
    global _worldgen_ingester
    if _worldgen_ingester is None:
        from chronicler.dfhack.worldgen import WorldgenIngester
        _worldgen_ingester = WorldgenIngester()
    return _worldgen_ingester


@router.websocket("/ws/worldgen")
async def websocket_worldgen(websocket: WebSocket):
    """Stream worldgen status to the client."""
    await websocket.accept()
    ingester = _get_worldgen_ingester()
    ingester.register_client(websocket)
    log.info("Worldgen WS client connected")

    try:
        # Send current status immediately if available
        if ingester.current_status:
            await websocket.send_json(ingester.current_status)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ingester.unregister_client(websocket)
        log.info("Worldgen WS client disconnected")


@router.get("/worldgen", response_class=HTMLResponse)
async def worldgen_dashboard(request: Request, world_id: int = 0):
    """Serve the worldgen monitoring / timeline dashboard."""
    from fastapi.templating import Jinja2Templates
    import os

    templates = Jinja2Templates(
        directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    )

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Available worlds
        worlds = await conn.fetch("SELECT id, name FROM worlds ORDER BY id")

        # If no world_id specified, use the first world
        if not world_id and worlds:
            world_id = worlds[0]["id"]

        # Check for timeline data
        has_timeline = False
        if world_id:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM worldgen_snapshots WHERE world_id = $1",
                world_id,
            )
            has_timeline = count > 0

        # Latest live snapshot (for live monitor mode)
        latest = await conn.fetchrow(
            """
            SELECT phase, progress_pct, year, hf_count, site_count,
                   entity_count, event_count, captured_at
            FROM worldgen_snapshots
            ORDER BY captured_at DESC LIMIT 1
            """
        )

    context = {
        "request": request,
        "worlds": [dict(w) for w in worlds],
        "world_id": world_id,
        "has_timeline": has_timeline,
        "latest_snapshot": dict(latest) if latest else None,
    }
    return templates.TemplateResponse("worldgen.html", context)


@router.get("/api/live/worldgen-history")
async def worldgen_history(request: Request, world_id: int = 0):
    """Return stored worldgen snapshots for timeline display."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if world_id:
            rows = await conn.fetch(
                """
                SELECT phase, progress_pct, year, hf_count, site_count,
                       entity_count, event_count, captured_at
                FROM worldgen_snapshots
                WHERE world_id = $1
                ORDER BY captured_at ASC
                """,
                world_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT phase, progress_pct, year, hf_count, site_count,
                       entity_count, event_count, captured_at
                FROM worldgen_snapshots
                ORDER BY captured_at DESC LIMIT 100
                """
            )
    return [dict(r) for r in rows]
