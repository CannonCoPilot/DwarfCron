"""Worldgen monitoring — polls worldgen-status.json and stores snapshots.

Polls the bridge HTTP server for worldgen status every 2 seconds.
Stores snapshots in worldgen_snapshots every 10 seconds.
Broadcasts updates to connected WebSocket clients for live dashboard.
"""

import asyncio
import json
import logging
import time

import asyncpg

from chronicler.config import DFHACK_HOST, BRIDGE_PORT
from chronicler.dfhack.bridge import fetch_bridge_data

log = logging.getLogger(__name__)


class WorldgenIngester:
    """Polls worldgen-status.json and stores snapshots in PostgreSQL."""

    POLL_INTERVAL = 2.0      # seconds between HTTP polls
    SNAPSHOT_INTERVAL = 10.0  # seconds between DB writes

    def __init__(self):
        self._current_status: dict | None = None
        self._ws_clients: set = set()
        self._running = False

    @property
    def current_status(self) -> dict | None:
        return self._current_status

    async def run(self, pool: asyncpg.Pool, world_id: int,
                  bridge_host: str = '', bridge_port: int = 0):
        """Main monitoring loop. Runs until worldgen completes or cancelled."""
        host = bridge_host or DFHACK_HOST
        port = bridge_port or BRIDGE_PORT
        self._running = True

        last_snapshot_time = 0.0
        last_state = None
        snapshot_count = 0

        log.info("Worldgen ingester started (polling %s:%d every %.1fs)",
                 host, port, self.POLL_INTERVAL)

        try:
            while self._running:
                status = self._fetch_status(host, port)

                if status:
                    self._current_status = status
                    state = status.get('state', 'None')

                    # Log state transitions
                    if state != last_state:
                        log.info("Worldgen phase: %s (%.1f%%)",
                                 state, status.get('progress_pct', 0))
                        last_state = state

                    # Periodic DB snapshots
                    now = time.time()
                    if now - last_snapshot_time >= self.SNAPSHOT_INTERVAL:
                        await self._store_snapshot(pool, world_id, status)
                        last_snapshot_time = now
                        snapshot_count += 1

                    # Broadcast to WebSocket clients
                    await self._broadcast(status)

                    # Check for completion
                    if state == 'Done':
                        # Final snapshot
                        await self._store_snapshot(pool, world_id, status)
                        log.info("Worldgen complete! %d snapshots stored", snapshot_count + 1)
                        break

                await asyncio.sleep(self.POLL_INTERVAL)

        except asyncio.CancelledError:
            log.info("Worldgen ingester cancelled (%d snapshots stored)", snapshot_count)
        finally:
            self._running = False

    def stop(self):
        """Signal the ingester to stop."""
        self._running = False

    def _fetch_status(self, host: str, port: int) -> dict | None:
        """Fetch worldgen status from bridge HTTP server."""
        return fetch_bridge_data(host, port, path='worldgen-status.json')

    async def _store_snapshot(self, pool: asyncpg.Pool, world_id: int,
                              status: dict):
        """Store snapshot in worldgen_snapshots table."""
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO worldgen_snapshots
                        (world_id, phase, progress_pct, year,
                         hf_count, site_count, entity_count, event_count,
                         data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    world_id,
                    status.get('state', 'Unknown'),
                    status.get('progress_pct', 0),
                    status.get('cur_year', 0),
                    status.get('figure_count'),
                    status.get('site_count'),
                    status.get('entity_count'),
                    status.get('event_count'),
                    json.dumps(status),
                )
        except Exception as e:
            log.error("Failed to store snapshot: %s", e)

    async def _broadcast(self, status: dict):
        """Send status to all connected WebSocket clients."""
        if not self._ws_clients:
            return
        payload = json.dumps(status)
        closed = set()
        for ws in self._ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                closed.add(ws)
        self._ws_clients.difference_update(closed)

    def register_client(self, ws):
        """Register a WebSocket client for updates."""
        self._ws_clients.add(ws)

    def unregister_client(self, ws):
        """Unregister a WebSocket client."""
        self._ws_clients.discard(ws)
