"""JSONL append log for raw bridge data — durable capture of live game state.

Each watcher cycle appends one JSON line containing the full bridge payload
plus metadata (timestamp, game time, cycle number). One file per session,
stored under data/bridge-logs/{world_name}/.

This ensures live data persists independently of the database and can be
replayed for re-ingestion, debugging, or historical analysis.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# Default base directory (relative to project root)
_DEFAULT_BASE = Path(__file__).resolve().parents[2] / "data" / "bridge-logs"


class BridgeLogger:
    """Append-only JSONL logger for bridge cycle data."""

    def __init__(self, base_dir: Path | str | None = None):
        self._base = Path(base_dir) if base_dir else _DEFAULT_BASE
        self._fh = None
        self._path: Path | None = None
        self._lines_written = 0

    def open(self, world_name: str = "unknown") -> Path:
        """Open a new session log file. Returns the file path."""
        # Sanitize world name for filesystem
        safe_name = "".join(
            c if c.isalnum() or c in "-_ " else "_" for c in world_name
        ).strip().replace(" ", "_").lower() or "unknown"

        session_dir = self._base / safe_name
        session_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self._path = session_dir / f"session-{ts}.jsonl"
        self._fh = open(self._path, "a", encoding="utf-8")
        self._lines_written = 0
        log.info("Bridge log opened: %s", self._path)
        return self._path

    def append(self, bridge_data: dict, cycle: int,
               game_year: int | None, game_tick: int | None):
        """Append one cycle's bridge data as a JSONL line."""
        if not self._fh:
            return

        record = {
            "ts": int(time.time()),
            "cycle": cycle,
            "game_year": game_year,
            "game_tick": game_tick,
            "bridge_version": bridge_data.get("bridge_version"),
            "data": bridge_data,
        }
        try:
            line = json.dumps(record, separators=(",", ":"))
            self._fh.write(line + "\n")
            self._fh.flush()
            self._lines_written += 1
        except Exception as e:
            log.debug("Bridge log write failed: %s", e)

    def close(self):
        """Close the log file."""
        if self._fh:
            self._fh.close()
            log.info("Bridge log closed: %s (%d cycles captured)",
                     self._path, self._lines_written)
            self._fh = None

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def lines_written(self) -> int:
        return self._lines_written
