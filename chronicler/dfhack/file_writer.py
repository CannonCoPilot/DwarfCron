"""Stage 2: Write bridge data to structured on-disk JSON files.

Bridge data arrives as a single dict with 26+ sections.
This module splits it into individual files under chronicler/data/live/,
preserving the previous cycle's files in _prev/ for CDC diffing.

File layout:
    chronicler/data/live/
    ├── _meta.json              # cycle metadata
    ├── fortress_units.json     # active fortress units
    ├── dwarf_skills.json       # per-unit skill arrays
    ├── ... (one file per section)
    └── _prev/                  # previous cycle (for CDC)
        └── (same files)
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

# All known bridge sections that get their own file
BRIDGE_SECTIONS = [
    "fortress_units", "dwarf_skills", "dwarf_personality", "dwarf_emotions",
    "squads", "noble_positions", "buildings", "artifacts",
    "announcements", "diplomacy", "history", "entities",
    "zones", "event_collections", "mandates", "incidents",
    "reactive_events", "skill_changes", "belief_systems",
    "cultural_identities", "occupations", "interaction_instances",
    "fortress_state", "daily_events", "world_info", "unit_summary",
    "armies",
]

# Top-level metadata keys in bridge dict (not data sections)
META_KEYS = {
    "cur_year", "cur_year_tick", "cur_season", "creature_raws",
    "creature_count", "timestamp", "bridge_version",
}


def _live_dir() -> Path:
    """Return the on-disk live data directory, creating it if needed."""
    # Resolve relative to the chronicler package location
    pkg_dir = Path(__file__).resolve().parent.parent  # chronicler/
    d = pkg_dir / "data" / "live"
    d.mkdir(parents=True, exist_ok=True)
    (d / "_prev").mkdir(exist_ok=True)
    return d


def rotate_previous(live_dir: Path) -> None:
    """Move current cycle files to _prev/ for CDC diffing."""
    prev_dir = live_dir / "_prev"
    # Clear old _prev files
    for f in prev_dir.glob("*.json"):
        f.unlink()
    # Move current files to _prev
    for f in live_dir.glob("*.json"):
        if f.name.startswith("_"):
            continue  # skip _meta.json itself from rotation
        shutil.copy2(f, prev_dir / f.name)


def write_bridge_to_disk(
    bridge_data: dict,
    world_id: int,
    cycle: int = 0,
    game_year: int | None = None,
    game_tick: int | None = None,
) -> Path:
    """Write bridge data to structured on-disk JSON files.

    Returns the live_dir path for downstream consumers.
    """
    live_dir = _live_dir()

    # Rotate current → _prev before writing new data
    rotate_previous(live_dir)

    # Extract metadata
    meta = {
        "world_id": world_id,
        "cycle": cycle,
        "game_year": game_year or bridge_data.get("cur_year"),
        "game_tick": game_tick or bridge_data.get("cur_year_tick"),
        "season": bridge_data.get("cur_season"),
        "bridge_version": bridge_data.get("bridge_version"),
        "creature_count": bridge_data.get("creature_count"),
    }

    # Write _meta.json
    (live_dir / "_meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8"
    )

    # Write each section to its own file
    sections_written = 0
    for section_name in BRIDGE_SECTIONS:
        data = bridge_data.get(section_name)
        if data is None:
            # Some sections are nested under different keys
            # e.g., fortress_units may be under unit_summary.fortress_units
            if section_name == "fortress_units":
                summary = bridge_data.get("unit_summary", {})
                data = summary.get("fortress_units") if isinstance(summary, dict) else None
            elif section_name == "announcements":
                ann = bridge_data.get("announcements", {})
                data = ann.get("recent") if isinstance(ann, dict) else ann
            elif section_name == "history":
                hist = bridge_data.get("history", {})
                data = hist.get("recent_events") if isinstance(hist, dict) else hist

        if data is not None:
            (live_dir / f"{section_name}.json").write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
            sections_written += 1

    log.info("Wrote %d bridge sections to %s (cycle %d, tick %s)",
             sections_written, live_dir, cycle, meta.get("game_tick"))

    return live_dir


def read_section(section_name: str, live_dir: Path | None = None) -> list | dict | None:
    """Read a single section from on-disk files."""
    if live_dir is None:
        live_dir = _live_dir()
    f = live_dir / f"{section_name}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def read_list_section(section_name: str, live_dir: Path | None = None) -> list:
    """Read a section expected to be a JSON array. Returns [] if missing or wrong type."""
    data = read_section(section_name, live_dir)
    return data if isinstance(data, list) else []


def read_dict_section(section_name: str, live_dir: Path | None = None) -> dict:
    """Read a section expected to be a JSON object. Returns {} if missing or wrong type."""
    data = read_section(section_name, live_dir)
    return data if isinstance(data, dict) else {}


def read_prev_section(section_name: str, live_dir: Path | None = None) -> list | dict | None:
    """Read a section from the previous cycle (for CDC diffing)."""
    if live_dir is None:
        live_dir = _live_dir()
    f = live_dir / "_prev" / f"{section_name}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def read_prev_list_section(section_name: str, live_dir: Path | None = None) -> list:
    """Read a previous-cycle section expected to be a JSON array."""
    data = read_prev_section(section_name, live_dir)
    return data if isinstance(data, list) else []


def read_meta(live_dir: Path | None = None) -> dict:
    """Read cycle metadata."""
    if live_dir is None:
        live_dir = _live_dir()
    f = live_dir / "_meta.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))
