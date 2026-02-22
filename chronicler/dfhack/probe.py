"""Lua probe framework — probes DF's memory via DFHack console commands.

Uses DFHackClient.run_command() to execute `lua` console commands that print
JSON-parseable output. Each probe is a minimal single-line Lua snippet that
extracts specific data from df.global.

CoreRunCommandRequest is a core method — no allow_remote needed, no pause hang.
Output comes back as TEXT notification frames parsed by _recv_response().
"""

import json
import logging

import asyncpg

from chronicler.dfhack.client import DFHackClient

log = logging.getLogger(__name__)


def probe_armies(client: DFHackClient) -> dict | None:
    """Probe army count and positions from df.global.world.armies.all.

    Returns dict with 'count' and 'armies' (list of pos dicts), or None on error.
    """
    lua = (
        'local c=#df.global.world.armies.all;'
        'local out={};'
        'for i=0,math.min(c-1,19) do '
        'local a=df.global.world.armies.all[i];'
        'out[#out+1]=string.format("{\\"pos_x\\":%d,\\"pos_y\\":%d}", a.pos.x, a.pos.y) '
        'end;'
        'print(string.format("{\\"count\\":%d,\\"armies\\":[%s]}", c, table.concat(out, ",")))'
    )
    return _run_json_probe(client, lua, 'armies')


def probe_diplomacy(client: DFHackClient) -> dict | None:
    """Probe diplomacy info from df.global.world.diplomacy.

    Returns dict with 'agreement_count', or None on error.
    """
    lua = (
        'local n=#df.global.world.diplomacy.agreements;'
        'print(string.format("{\\"agreement_count\\":%d}", n))'
    )
    return _run_json_probe(client, lua, 'diplomacy')


def probe_unit_detail(client: DFHackClient, unit_id: int) -> dict | None:
    """Probe detailed personality/mood for a specific unit.

    Returns dict with stress, happiness, current_emotion, or None on error.
    """
    lua = (
        f'local u=df.unit.find({unit_id});'
        'if u and u.status.current_soul then '
        'local p=u.status.current_soul.personality;'
        'print(string.format("{\\"unit_id\\":%d,\\"stress\\":%d}", '
        f'{unit_id}, p.stress)) '
        'else print("null") end'
    )
    return _run_json_probe(client, lua, f'unit_detail_{unit_id}')


def _run_json_probe(client: DFHackClient, lua_code: str,
                    probe_name: str) -> dict | None:
    """Execute a Lua probe and parse JSON output.

    Returns parsed dict, or None if the probe fails or returns non-JSON.
    """
    try:
        lines = client.run_command('lua', lua_code)
        if not lines:
            log.debug("Probe %s returned no output", probe_name)
            return None

        # Join all output lines and try to parse as JSON
        text = ''.join(lines).strip()
        if text == 'null' or not text:
            return None
        return json.loads(text)
    except json.JSONDecodeError as e:
        log.warning("Probe %s returned non-JSON: %s (error: %s)",
                    probe_name, text[:200], e)
        return None
    except Exception as e:
        log.warning("Probe %s failed: %s", probe_name, e)
        return None


async def store_probe(conn: asyncpg.Connection, world_id: int,
                      probe_name: str, data: dict,
                      game_year: int | None = None,
                      game_tick: int | None = None):
    """Store a probe result in the lua_probes table."""
    await conn.execute(
        """
        INSERT INTO lua_probes (world_id, probe_name, data, game_year, game_tick)
        VALUES ($1, $2, $3, $4, $5)
        """,
        world_id,
        probe_name,
        json.dumps(data),
        game_year,
        game_tick,
    )
