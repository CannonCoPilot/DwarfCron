"""DFHack RPC client — connects to a running Dwarf Fortress via DFHack's TCP interface.

Uses DFHack's core API methods (ListUnits, ListEnums, GetWorldInfo, etc.)
which work from remote hosts without needing allow_remote=true. Plugin methods
(RemoteFortressReader) require allow_remote=true in dfhack-config/remote-server.json.

Protocol: custom framing over TCP with protobuf payloads.
  - Handshake: send b'DFHack?\\n' + version(1), receive b'DFHack!\\n' + version(1)
  - Frame: int16 method_id | int16 padding | int32 payload_size | payload
  - Special IDs: -1=RESULT, -2=FAIL, -3=TEXT, -4=QUIT
  - Method 0 = BindMethod (CoreBindRequest → CoreBindReply with assigned_id)
"""

import logging
import socket
import struct
from typing import Optional

from google.protobuf.message import Message as ProtoMessage

from chronicler.dfhack.proto import (
    BasicApi_pb2 as api,
    Basic_pb2 as basic,
    CoreProtocol_pb2 as core,
    RemoteFortressReader_pb2 as rfr,
)

log = logging.getLogger(__name__)

# DFHack RPC response codes
_RESULT = -1
_FAIL = -2
_TEXT = -3
_QUIT = -4


class DFHackError(Exception):
    """Raised when a DFHack RPC call fails."""


class DFHackClient:
    """Synchronous DFHack RPC client.

    Usage::

        client = DFHackClient("192.168.4.194", 5000)
        client.connect()
        info = client.get_world_info()
        units = client.list_units(sane=True)
        client.close()
    """

    def __init__(self, host: str = "192.168.4.194", port: int = 5000,
                 timeout: float = 15.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._bound: dict[str, int] = {}  # method_name -> assigned_id
        self._enums: Optional[api.ListEnumsOut] = None
        self._job_skills: Optional[api.ListJobSkillsOut] = None
        self._creature_raws: Optional[dict[int, str]] = None

    # ── Connection ────────────────────────────────────────────────────

    def connect(self):
        """Establish TCP connection and perform DFHack handshake."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect((self.host, self.port))

        # Handshake: DFHack?\n + version 1
        self._sock.sendall(b'DFHack?\n' + struct.pack('<I', 1))
        resp = self._recv_exact(12)
        if resp[:8] != b'DFHack!\n':
            raise DFHackError(f"Bad handshake response: {resp!r}")
        version = struct.unpack('<I', resp[8:])[0]
        log.info("Connected to DFHack v%d at %s:%d", version, self.host, self.port)

    def close(self):
        """Send QUIT and close connection."""
        if self._sock:
            try:
                self._send_frame(_QUIT, b'')
            except OSError:
                pass
            self._sock.close()
            self._sock = None
        self._bound.clear()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    # ── Low-level protocol ────────────────────────────────────────────

    def _recv_exact(self, n: int) -> bytes:
        """Read exactly n bytes from socket."""
        buf = b''
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("DFHack connection closed")
            buf += chunk
        return buf

    def _send_frame(self, method_id: int, payload: bytes):
        """Send a DFHack RPC frame."""
        header = struct.pack('<hhI', method_id, 0, len(payload))
        self._sock.sendall(header + payload)

    def _recv_frame(self) -> tuple[int, bytes]:
        """Receive a single DFHack RPC frame."""
        header = self._recv_exact(8)
        msg_id = struct.unpack('<h', header[0:2])[0]
        size = struct.unpack('<I', header[4:8])[0]
        data = self._recv_exact(size) if size > 0 else b''
        return msg_id, data

    def _recv_response(self) -> tuple[int, bytes, list[str]]:
        """Read frames until a RESULT or FAIL, collecting TEXT notifications."""
        texts = []
        while True:
            msg_id, data = self._recv_frame()
            if msg_id == _TEXT:
                notif = core.CoreTextNotification()
                notif.ParseFromString(data)
                for frag in notif.fragments:
                    texts.append(frag.text)
                continue
            return msg_id, data, texts

    # ── Method binding ────────────────────────────────────────────────

    def _bind(self, method: str, in_type: type, out_type: type,
              plugin: str = '') -> int:
        """Bind an RPC method and cache the assigned ID."""
        key = f"{plugin}::{method}" if plugin else method
        if key in self._bound:
            return self._bound[key]

        br = core.CoreBindRequest()
        br.method = method
        br.input_msg = in_type.DESCRIPTOR.full_name
        br.output_msg = out_type.DESCRIPTOR.full_name
        br.plugin = plugin
        self._send_frame(0, br.SerializeToString())

        msg_id, data, texts = self._recv_response()
        if msg_id == _FAIL:
            raise DFHackError(f"Bind {key} failed: {texts}")
        reply = core.CoreBindReply()
        reply.ParseFromString(data)
        self._bound[key] = reply.assigned_id
        log.debug("Bound %s → id=%d", key, reply.assigned_id)
        return reply.assigned_id

    def _call(self, method: str, request: ProtoMessage, response_type: type,
              plugin: str = '') -> ProtoMessage:
        """Bind (if needed) and call an RPC method, returning parsed response."""
        in_type = type(request)
        aid = self._bind(method, in_type, response_type, plugin)
        self._send_frame(aid, request.SerializeToString())

        msg_id, data, texts = self._recv_response()
        if texts:
            log.debug("RPC %s texts: %s", method, texts)
        if msg_id == _FAIL:
            raise DFHackError(f"Call {method} failed: {texts}")
        result = response_type()
        result.ParseFromString(data)
        return result

    # ── High-level API (Core methods — no allow_remote needed) ────────

    def get_version(self) -> str:
        """Get DFHack version string."""
        result = self._call('GetVersion', core.EmptyMessage(),
                            core.StringMessage)
        return result.value

    def get_world_info(self) -> dict:
        """Get current world info (name, mode, civ_id, site_id)."""
        result = self._call('GetWorldInfo', core.EmptyMessage(),
                            api.GetWorldInfoOut)
        info = {
            'mode': api.GetWorldInfoOut.Mode.Name(result.mode),
            'save_dir': result.save_dir,
            'civ_id': result.civ_id,
            'site_id': result.site_id,
            'race_id': result.race_id,
        }
        if result.HasField('world_name'):
            wn = result.world_name
            info['world_name'] = wn.first_name or ''
            info['world_english'] = wn.english_name or ''
        return info

    def list_enums(self) -> api.ListEnumsOut:
        """Get all game enum mappings (profession, skill, labor, etc.)."""
        if self._enums is None:
            self._enums = self._call('ListEnums', core.EmptyMessage(),
                                     api.ListEnumsOut)
        return self._enums

    def list_job_skills(self) -> api.ListJobSkillsOut:
        """Get detailed skill/profession attributes."""
        if self._job_skills is None:
            self._job_skills = self._call('ListJobSkills', core.EmptyMessage(),
                                          api.ListJobSkillsOut)
        return self._job_skills

    def list_units(self, *, sane: bool = False, alive: bool = False,
                   scan_all: bool = True, skills: bool = True,
                   profession: bool = True,
                   labors: bool = False) -> list[dict]:
        """List units with optional filters, returning CDM-compatible dicts.

        Returns list of dicts with keys matching the CDM units table:
        id, name, race (numeric), caste, profession, pos_x/y/z,
        is_alive, hist_fig_id, civ_id, details (skills, labors, flags).
        """
        req = api.ListUnitsIn()
        req.scan_all = scan_all
        if sane:
            req.sane = True
        if alive:
            req.alive = True
        req.mask.skills = skills
        req.mask.profession = profession
        req.mask.labors = labors

        result = self._call('ListUnits', req, api.ListUnitsOut)
        return [self._unit_to_dict(u) for u in result.value]

    def list_squads(self) -> list[dict]:
        """List military squads."""
        result = self._call('ListSquads', api.ListSquadsIn(),
                            api.ListSquadsOut)
        squads = []
        for s in result.value:
            squad = {
                'squad_id': s.squad_id,
                'alias': s.alias or None,
                'members': list(s.members),
            }
            if s.HasField('name'):
                squad['name'] = self._format_name(s.name)
            squads.append(squad)
        return squads

    # ── Name resolution ───────────────────────────────────────────────

    def profession_name(self, prof_id: int) -> str:
        """Resolve a profession ID to its display name."""
        enums = self.list_enums()
        for p in enums.profession:
            if p.value == prof_id:
                return p.name
        return f"UNKNOWN_{prof_id}"

    def skill_name(self, skill_id: int) -> str:
        """Resolve a skill ID to its caption."""
        js = self.list_job_skills()
        for s in js.skill:
            if s.id == skill_id:
                return s.caption or s.key
        return f"SKILL_{skill_id}"

    # ── Core commands ────────────────────────────────────────────────

    def run_command(self, command: str, *args: str) -> list[str]:
        """Execute a DFHack console command and capture text output.

        Uses CoreRunCommandRequest (core method — no plugin needed, no pause hang).
        Output arrives as TEXT notification frames, already captured by _recv_response().

        Example: run_command("lua", 'print(#df.global.world.armies.all)')
        """
        req = core.CoreRunCommandRequest()
        req.command = command
        for arg in args:
            req.arguments.append(arg)

        aid = self._bind('RunCommand', core.CoreRunCommandRequest,
                         core.EmptyMessage)
        self._send_frame(aid, req.SerializeToString())
        msg_id, data, texts = self._recv_response()
        if msg_id == _FAIL:
            raise DFHackError(f"RunCommand '{command}' failed: {texts}")
        return texts

    # ── RemoteFortressReader (requires allow_remote=true) ────────────

    def get_world_map(self, timeout: float = 15.0) -> dict | None:
        """Get game time via WorldMapCenter (smaller payload than full map).

        Requires allow_remote=true AND game unpaused (plugin calls run on
        the game main loop, so they hang when paused).
        """
        old_timeout = self._sock.gettimeout()
        self._sock.settimeout(timeout)
        try:
            result = self._call('GetWorldMapCenter', core.EmptyMessage(),
                                rfr.WorldMap, plugin='RemoteFortressReader')
            return {
                'cur_year': result.cur_year,
                'cur_year_tick': result.cur_year_tick,
                'name': result.name or None,
                'name_english': result.name_english or None,
            }
        except (socket.timeout, TimeoutError):
            log.debug("GetWorldMap timed out (game paused?)")
            return None
        finally:
            self._sock.settimeout(old_timeout)

    def get_creature_raws(self, timeout: float = 30.0) -> dict[int, str] | None:
        """Build race_id → race_name mapping from creature raws.

        Cached after first successful call (creature raws don't change mid-game).
        Returns None on timeout.
        """
        if self._creature_raws is not None:
            return self._creature_raws

        old_timeout = self._sock.gettimeout()
        self._sock.settimeout(timeout)
        try:
            result = self._call('GetCreatureRaws', core.EmptyMessage(),
                                rfr.CreatureRawList,
                                plugin='RemoteFortressReader')
            self._creature_raws = {
                raw.index: raw.creature_id
                for raw in result.creature_raws
            }
            log.info("Cached %d creature raws", len(self._creature_raws))
            return self._creature_raws
        except (socket.timeout, TimeoutError):
            log.debug("GetCreatureRaws timed out (game paused?)")
            return None
        finally:
            self._sock.settimeout(old_timeout)

    def get_reports(self, timeout: float = 15.0) -> list[dict] | None:
        """Get game reports (announcements, combat logs) via RemoteFortressReader.

        Returns list of dicts with keys: id, type, text, year, time,
        pos_x, pos_y, pos_z, announcement, repeat_count.
        Returns None on timeout (game paused).
        """
        old_timeout = self._sock.gettimeout()
        self._sock.settimeout(timeout)
        try:
            result = self._call('GetReports', core.EmptyMessage(),
                                rfr.Status, plugin='RemoteFortressReader')
            reports = []
            for r in result.reports:
                reports.append({
                    'id': r.id,
                    'type': r.type,
                    'text': r.text,
                    'year': r.year if r.year else None,
                    'time': r.time if r.time else None,
                    'pos_x': r.pos.x if r.HasField('pos') else None,
                    'pos_y': r.pos.y if r.HasField('pos') else None,
                    'pos_z': r.pos.z if r.HasField('pos') else None,
                    'announcement': r.announcement,
                    'repeat_count': r.repeat_count,
                })
            return reports
        except (socket.timeout, TimeoutError):
            log.debug("GetReports timed out (game paused?)")
            return None
        finally:
            self._sock.settimeout(old_timeout)

    def get_full_world_map(self, timeout: float = 30.0) -> dict | None:
        """Get full world map data (geography, climate) via RemoteFortressReader.

        Returns dict with world dimensions, name, year/tick, and geography arrays
        (elevation, rainfall, vegetation, temperature, evilness, drainage,
        volcanism, savagery, salinity).

        Cached after first successful call — geography doesn't change mid-game.
        Returns None on timeout.
        """
        if hasattr(self, '_world_map_cache') and self._world_map_cache is not None:
            return self._world_map_cache

        old_timeout = self._sock.gettimeout()
        self._sock.settimeout(timeout)
        try:
            result = self._call('GetWorldMapNew', core.EmptyMessage(),
                                rfr.WorldMap, plugin='RemoteFortressReader')
            data = {
                'world_width': result.world_width,
                'world_height': result.world_height,
                'name': result.name or None,
                'name_english': result.name_english or None,
                'cur_year': result.cur_year,
                'cur_year_tick': result.cur_year_tick,
                'elevation': list(result.elevation),
                'rainfall': list(result.rainfall),
                'vegetation': list(result.vegetation),
                'temperature': list(result.temperature),
                'evilness': list(result.evilness),
                'drainage': list(result.drainage),
                'volcanism': list(result.volcanism),
                'savagery': list(result.savagery),
                'salinity': list(result.salinity),
            }
            self._world_map_cache = data
            log.info("Cached full world map: %dx%d '%s'",
                     data['world_width'], data['world_height'],
                     data['name_english'] or data['name'])
            return data
        except (socket.timeout, TimeoutError):
            log.debug("GetWorldMapNew timed out (game paused?)")
            return None
        finally:
            self._sock.settimeout(old_timeout)

    def get_enriched_units(self, timeout: float = 30.0) -> list[dict] | None:
        """Get enriched unit data via RemoteFortressReader's GetUnitList.

        Returns extended unit data including inventory, wounds, appearance,
        noble positions, blood stats, and soldier status.
        Returns None on timeout.
        """
        old_timeout = self._sock.gettimeout()
        self._sock.settimeout(timeout)
        try:
            result = self._call('GetUnitList', core.EmptyMessage(),
                                rfr.UnitList, plugin='RemoteFortressReader')
            units = []
            for u in result.creature_list:
                if not u.isValid:
                    continue
                unit = {
                    'id': u.id,
                    'pos_x': u.pos_x,
                    'pos_y': u.pos_y,
                    'pos_z': u.pos_z,
                    'is_soldier': u.is_soldier,
                    'blood_max': u.blood_max,
                    'blood_count': u.blood_count,
                    'age': u.age,
                    'noble_positions': list(u.noble_positions),
                    'inventory': [
                        {
                            'mode': rfr.InventoryMode.Name(item.mode),
                            'item_id': item.item.id if item.HasField('item') else None,
                            'body_part_id': item.body_part_id,
                        }
                        for item in u.inventory
                    ],
                    'wounds': [
                        {
                            'parts': [
                                {
                                    'body_part_id': p.body_part_id,
                                    'layer_idx': p.layer_idx,
                                }
                                for p in w.parts
                            ],
                            'severed': w.severed_part,
                        }
                        for w in u.wounds
                    ],
                }
                units.append(unit)
            return units
        except (socket.timeout, TimeoutError):
            log.debug("GetUnitList (RFR) timed out (game paused?)")
            return None
        finally:
            self._sock.settimeout(old_timeout)

    # ── Internal helpers ──────────────────────────────────────────────

    @staticmethod
    def _format_name(name_info) -> str:
        """Format a NameInfo protobuf into a readable string."""
        parts = []
        if name_info.first_name:
            parts.append(name_info.first_name.capitalize())
        if name_info.nickname:
            parts.append(f'"{name_info.nickname}"')
        if name_info.last_name:
            parts.append(name_info.last_name.capitalize())
        return ' '.join(parts) if parts else None

    def _unit_to_dict(self, u) -> dict:
        """Convert a BasicUnitInfo protobuf to a CDM-compatible dict."""
        name = self._format_name(u.name) if u.HasField('name') else None
        english = u.name.english_name if u.HasField('name') else None

        # Determine alive status from flags
        # flags1 bit 1 = dead, bit 2 = zombie (df-structures)
        is_alive = not bool(u.flags1 & 0x02)

        skills = [
            {'id': s.id, 'name': self.skill_name(s.id),
             'level': s.level, 'xp': s.experience}
            for s in u.skills
        ] if u.skills else []

        details = {
            'english_name': english,
            'caste': u.caste,
            'gender': u.gender,
            'custom_profession': u.custom_profession or None,
            'squad_id': u.squad_id if u.squad_id != -1 else None,
            'squad_position': u.squad_position if u.squad_position != -1 else None,
            'skills': skills,
            'labors': list(u.labors) if u.labors else [],
            'flags1': u.flags1,
            'flags2': u.flags2,
            'flags3': u.flags3,
            'death_id': u.death_id if u.death_id != -1 else None,
        }

        return {
            'id': u.unit_id,
            'name': name,
            'race': u.race,  # numeric — needs creature raws to resolve
            'caste': u.caste,
            'profession': self.profession_name(u.profession),
            'pos_x': u.pos_x,
            'pos_y': u.pos_y,
            'pos_z': u.pos_z,
            'is_alive': is_alive,
            'hist_fig_id': u.histfig_id if u.histfig_id != -1 else None,
            'civ_id': u.civ_id if u.civ_id != -1 else None,
            'details': details,
        }
