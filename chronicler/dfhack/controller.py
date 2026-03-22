"""Game controller — pause/unpause/step/status/bridge via DFHack.

Uses SSH + dfhack-run.exe as transport (the only method that works reliably
on DFHack 53.x under Prism/ARM emulation). TCP RPC's CoreRunCommand hangs
because the CoreSuspender is never acquired from the network thread.

dfhack-run.exe runs on the DFHack console thread inside the DF process,
bypassing the CoreSuspender entirely.

Bridge data collection also uses SSH (reading the JSON file directly) rather
than HTTP, avoiding Windows Firewall configuration.

No C++ plugin or df-ai integration needed.
"""

import base64
import json
import logging
import shlex
import subprocess
import time

log = logging.getLogger(__name__)

# Path to dfhack-run.exe on the Windows VM (root DF directory, NOT hack/)
_DFHACK_RUN = (
    r"C:\Program Files (x86)\Steam\steamapps\common"
    r"\Dwarf Fortress\dfhack-run.exe"
)


class ControllerError(Exception):
    """Raised when a game control command fails."""


class GameController:
    """Controls DF game state (pause/unpause/step) via SSH + dfhack-run.

    Usage::

        ctrl = GameController(host="192.168.64.3")
        ctrl.pause()
        status = ctrl.get_status()
        ctrl.unpause()
        ctrl.step(100)  # advance 100 ticks then pause
    """

    def __init__(self, host: str = "192.168.64.3",
                 ssh_key: str = "~/.ssh/df-vm",
                 ssh_user: str = "administrator",
                 ssh_timeout: int = 10):
        self._host = host
        self._ssh_key = ssh_key
        self._ssh_user = ssh_user
        self._ssh_timeout = ssh_timeout
        # Build the PowerShell prefix for dfhack-run once
        self._dfhack_run_ps = _DFHACK_RUN.replace("\\", "\\\\")

    def _ssh(self, remote_cmd: str, timeout: int | None = None) -> str:
        """Execute a command on the VM via SSH and return stdout.

        Uses raw bytes + encoding fallback (UTF-8 → latin-1) to handle
        Windows-1252 encoded DF names that contain non-ASCII characters.
        """
        t = timeout or self._ssh_timeout
        cmd = [
            "ssh",
            "-i", self._ssh_key,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", f"ConnectTimeout={t}",
            "-o", "LogLevel=ERROR",
            f"{self._ssh_user}@{self._host}",
            remote_cmd,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True,
                timeout=t + 5,
            )
            if result.returncode != 0 and result.stderr:
                log.warning("SSH stderr: %s",
                            result.stderr.decode('utf-8', errors='replace').strip())
            # Decode stdout with fallback for Windows-1252 DF names
            try:
                stdout = result.stdout.decode('utf-8')
            except UnicodeDecodeError:
                stdout = result.stdout.decode('latin-1')
            return stdout.strip()
        except subprocess.TimeoutExpired:
            raise ControllerError(
                f"SSH command timed out after {self._ssh_timeout}s"
            )
        except FileNotFoundError:
            raise ControllerError("ssh binary not found")

    def _lua(self, code: str) -> str:
        """Execute a Lua snippet via SSH + PowerShell + dfhack-run.

        Uses PowerShell's & operator with single-quoted paths. Inner
        single quotes in the Lua code are doubled ('') per PowerShell
        escaping rules for single-quoted strings.
        """
        # Escape single quotes for PowerShell single-quoted string
        escaped = code.replace("'", "''")
        ps_cmd = (
            f"powershell -Command "
            f"\"& '{_DFHACK_RUN}' lua '{escaped}' \""
        )
        return self._ssh(ps_cmd)

    # ── Core controls ─────────────────────────────────────────────

    def pause(self) -> bool:
        """Pause the game. Returns True if game is now paused."""
        self._lua("df.global.pause_state=true")
        paused = self.is_paused()
        if paused:
            log.info("Game paused")
        else:
            log.warning("Pause command sent but game reports unpaused")
        return paused

    def unpause(self) -> bool:
        """Unpause the game. Returns True if game is now unpaused."""
        self._lua("df.global.pause_state=false")
        paused = self.is_paused()
        if not paused:
            log.info("Game unpaused")
        else:
            log.warning("Unpause command sent but game reports paused")
        return not paused

    def is_paused(self) -> bool:
        """Check current pause state."""
        output = self._lua("print(df.global.pause_state)")
        return output.strip().lower() == "true"

    def step(self, ticks: int = 100, poll_interval: float = 0.5,
             timeout: float = 0) -> dict:
        """Advance the game by approximately `ticks` ticks, then re-pause.

        1. Record current tick
        2. Unpause
        3. Poll until tick has advanced by >= ticks
        4. Re-pause
        5. Return {start_tick, end_tick, elapsed_ticks, year, season}

        If timeout is 0 (default), it auto-scales based on tick count:
        ~30s per 10,000 ticks under Prism emulation.
        """
        if timeout <= 0:
            # Auto-scale: Prism emulation ~500 ticks/sec, add buffer
            timeout = max(30.0, ticks / 400)

        start = self.get_game_time()
        start_tick = start["cur_year_tick"]
        start_year = start["cur_year"]
        target_tick = start_tick + ticks

        log.info("Stepping %d ticks from Y%d T%d (timeout=%.0fs)",
                 ticks, start_year, start_tick, timeout)

        self._lua("df.global.pause_state=false")

        deadline = time.monotonic() + timeout
        end = start
        while time.monotonic() < deadline:
            time.sleep(poll_interval)
            end = self.get_game_time()
            if end["cur_year"] > start_year or end["cur_year_tick"] >= target_tick:
                break

        self._lua("df.global.pause_state=true")

        elapsed = end["cur_year_tick"] - start_tick
        if end["cur_year"] > start_year:
            elapsed += 403200

        log.info("Stepped %d ticks (target %d). Now Y%d T%d",
                 elapsed, ticks, end["cur_year"], end["cur_year_tick"])

        return {
            "start_year": start_year,
            "start_tick": start_tick,
            "end_year": end["cur_year"],
            "end_tick": end["cur_year_tick"],
            "elapsed_ticks": elapsed,
            "season": end.get("season", "?"),
        }

    # ── Status ────────────────────────────────────────────────────

    def get_game_time(self) -> dict:
        """Get current game time (year, tick, season) via Lua.

        Uses Lua print() with multiple args (tab-separated output).
        """
        output = self._lua(
            "print(df.global.cur_year,df.global.cur_year_tick,df.global.pause_state)"
        )
        if not output:
            raise ControllerError("No response from game time query")

        parts = output.strip().split()
        if len(parts) < 3:
            raise ControllerError(f"Unexpected game time response: {output}")

        year = int(parts[0])
        tick = int(parts[1])
        paused = parts[2].lower() == "true"

        # Season: 403200 ticks/year, ~100800 ticks/season
        season_idx = min(tick // 100800, 3)
        seasons = ["Spring", "Summer", "Autumn", "Winter"]

        return {
            "cur_year": year,
            "cur_year_tick": tick,
            "paused": paused,
            "season": seasons[season_idx],
        }

    def get_status(self) -> dict:
        """Get comprehensive game status including fortress name and citizen count."""
        game_time = self.get_game_time()

        # Fortress name — use site name from active site
        name_output = self._lua(
            "print(dfhack.translation.translateName("
            "df.global.world.world_data.active_site[0].name,true))"
        )

        # Citizen count
        count_output = self._lua(
            "local c=0 "
            "for _,u in ipairs(df.global.world.units.active) do "
            "if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) "
            "then c=c+1 end end "
            "print(c)"
        )

        fortress_name = name_output.strip() if name_output else "?"
        citizen_count = int(count_output.strip()) if count_output else 0

        return {
            **game_time,
            "fortress_name": fortress_name,
            "citizen_count": citizen_count,
        }

    # ── Bridge data ────────────────────────────────────────────────

    def run_bridge(self) -> str:
        """Execute the chronicler-bridge Lua script to refresh state JSON.

        Returns the dfhack-run output (bridge version info).
        """
        ps_cmd = (
            f"powershell -Command "
            f"\"& '{_DFHACK_RUN}' chronicler-bridge\""
        )
        return self._ssh(ps_cmd)

    def setup_bridge_repeat(self, ticks: int = 100) -> str:
        """Register bridge as a DFHack repeating job.

        Runs chronicler-bridge every N ticks automatically.
        Uses dfhack_command() which handles the PowerShell invocation.
        """
        return self.dfhack_command(
            f"repeat --name chronicler --time {ticks} "
            f"--timeUnits ticks --command [ chronicler-bridge ]"
        )

    def fetch_bridge_data(self) -> dict | None:
        """Read chronicler-state.json from the VM via SSH + base64.

        Returns parsed dict or None on error. Uses base64 encoding
        to handle non-ASCII DF names (Windows-1252) cleanly over SSH.
        """
        json_path = (
            r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\Dwarf Fortress\chronicler-state.json"
        )
        ps_cmd = (
            f"powershell -Command "
            f"\"[Convert]::ToBase64String("
            f"[IO.File]::ReadAllBytes('{json_path}'))\""
        )
        try:
            b64_output = self._ssh(ps_cmd, timeout=20)
            if not b64_output:
                log.warning("Bridge JSON file empty or missing")
                return None
            raw = base64.b64decode(b64_output)
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('latin-1')
            return json.loads(text)
        except json.JSONDecodeError as e:
            log.warning("Bridge JSON parse error: %s", e)
            return None
        except ControllerError as e:
            log.warning("Bridge data fetch failed: %s", e)
            return None

    # ── Utility commands ─────────────────────────────────────────

    def save(self) -> bool:
        """Trigger a quicksave. Game should be paused first.

        Returns True if the command completed without error.
        """
        ps_cmd = (
            f"powershell -Command "
            f"\"& '{_DFHACK_RUN}' quicksave\""
        )
        output = self._ssh(ps_cmd, timeout=30)
        log.info("Quicksave: %s", output or "done")
        return True

    def execute_lua(self, code: str) -> str:
        """Execute arbitrary Lua code and return the output.

        This is the raw introspection command — no wrapping, no parsing.
        Whatever Lua prints via print() is returned as a string.
        """
        return self._lua(code)

    def set_speed(self, speed: int) -> str:
        """Set game speed via timestream plugin (1=slow, 2=normal, 3=fast, 4=max).

        DF 53.x removed d_init.fps_cap. Use timestream for speed control:
        - 1: disable timestream (native ~30fps under Prism)
        - 2: timestream fps 50
        - 3: timestream fps 100
        - 4: timestream fps 200
        """
        if speed == 1:
            output = self.dfhack_command("disable timestream")
            log.info("Speed 1 (native): timestream disabled")
            return output
        fps_map = {2: 50, 3: 100, 4: 200}
        fps = fps_map.get(speed)
        if fps is None:
            return f"Invalid speed {speed}. Use 1-4 (1=native, 4=max)."
        self.dfhack_command("enable timestream")
        output = self.dfhack_command(f"timestream set fps {fps}")
        log.info("Speed %d (fps=%d): %s", speed, fps, output)
        return output

    def get_citizens(self) -> list[dict]:
        """List all living citizens with id, name, profession, and age.

        Returns a list of dicts with keys: id, name, profession, sex, age.
        """
        lua = (
            "local out={} "
            "for _,u in ipairs(df.global.world.units.active) do "
            "if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then "
            "local name=dfhack.translation.translateName(u.name,false) "
            "local prof=dfhack.units.getProfessionName(u) "
            "local sex=u.sex==0 and 'F' or 'M' "
            "local age=df.global.cur_year - u.birth_year "
            "print(u.id..'\t'..name..'\t'..prof..'\t'..sex..'\t'..age) "
            "end end"
        )
        output = self._lua(lua)
        citizens = []
        for line in output.strip().splitlines():
            parts = line.split('\t')
            if len(parts) >= 5:
                citizens.append({
                    "id": int(parts[0]),
                    "name": parts[1],
                    "profession": parts[2],
                    "sex": parts[3],
                    "age": int(parts[4]),
                })
        return citizens

    def get_announcements(self, limit: int = 20) -> list[dict]:
        """Read recent game announcements/log entries.

        Returns list of dicts with keys: year, tick, text.
        """
        lua = (
            f"local ann=df.global.world.status.announcements "
            f"local start=math.max(0,#ann-{limit}) "
            f"for i=start,#ann-1 do "
            f"local a=ann[i] "
            f"print(a.year..'\t'..a.time..'\t'..dfhack.df2utf(a.text)) "
            f"end"
        )
        output = self._lua(lua)
        results = []
        for line in output.strip().splitlines():
            parts = line.split('\t', 2)
            if len(parts) >= 3:
                results.append({
                    "year": int(parts[0]),
                    "tick": int(parts[1]),
                    "text": parts[2],
                })
        return results

    def probe_path(self, path: str) -> str:
        """Introspect a df.global path and return its type and child fields.

        Uses pairs() which works on both DF userdata and regular tables.
        Shows field names, their Lua type, and a truncated string value.

        Example: probe_path("df.global.world.units.active[0]")
        """
        lua = (
            f"local obj={path} "
            f"if obj==nil then print('NIL') return end "
            f"local t=type(obj) "
            f"print('TYPE:'..t) "
            f"if t=='userdata' or t=='table' then "
            f"local ok,td=pcall(function() return obj._type end) "
            f"if ok and td then print('DF_TYPE:'..tostring(td)) end "
            f"local fields={{}} "
            f"for k,v in pairs(obj) do "
            f"local vt=type(v) "
            f"local vs=tostring(v) "
            f"if #vs>60 then vs=vs:sub(1,60) end "
            f"table.insert(fields,k..'\t'..vt..'\t'..vs) end "
            f"table.sort(fields) "
            f"for _,f in ipairs(fields) do print(f) end "
            f"else print('VALUE:'..tostring(obj)) end"
        )
        return self._lua(lua)

    def enumerate_fields(self, path: str) -> str:
        """Enumerate all fields of a DF object at the given path with types.

        More detailed than probe_path — for userdata children, also shows
        the DF type name via _type. Used for CDM mapping.
        """
        lua = (
            f"local obj={path} "
            f"if obj==nil then print('NIL') return end "
            f"for k,v in pairs(obj) do "
            f"local vt=type(v) "
            f"local vs=tostring(v) "
            f"if vt=='userdata' then "
            f"local ok,td=pcall(function() return v._type end) "
            f"if ok and td then vs=tostring(td) end "
            f"end "
            f"if #vs>80 then vs=vs:sub(1,80) end "
            f"print(k..'\t'..vt..'\t'..vs) "
            f"end"
        )
        return self._lua(lua)

    # ── DFHack command execution ─────────────────────────────────

    def dfhack_command(self, command: str) -> str:
        """Execute any DFHack console command and return output.

        This is the general-purpose command runner. Examples:
            dfhack_command("allneeds")
            dfhack_command("enable timestream")
            dfhack_command("timestream set fps 200")
        """
        ps_cmd = (
            f"powershell -Command "
            f"\"& '{_DFHACK_RUN}' {command}\""
        )
        return self._ssh(ps_cmd, timeout=20)

    def enable_timestream(self, target_fps: int = 200) -> str:
        """Enable timestream for faster game advancement."""
        self.dfhack_command("enable timestream")
        return self.dfhack_command(f"timestream set fps {target_fps}")

    def disable_timestream(self) -> str:
        """Disable timestream."""
        return self.dfhack_command("disable timestream")

    def get_needs_summary(self) -> str:
        """Get fortress needs summary (allneeds)."""
        return self.dfhack_command("allneeds")

    def get_all_announcements(self, limit: int = 50) -> list[dict]:
        """Read game announcements with utf-8 safe encoding."""
        return self.get_announcements(limit)

    def advance_season(self, callback=None) -> dict:
        """Advance the game by one full season (~100,800 ticks).

        Enables timestream for speed, then steps in chunks of 10,000 ticks
        to allow periodic data collection. Calls optional callback after
        each chunk with the step result.
        """
        self.enable_timestream(200)

        start = self.get_game_time()
        chunk_size = 10000
        ticks_remaining = 100800
        total_elapsed = 0

        while ticks_remaining > 0:
            step_ticks = min(chunk_size, ticks_remaining)
            result = self.step(step_ticks)
            actual = result["elapsed_ticks"]
            total_elapsed += actual
            ticks_remaining -= actual

            if callback:
                callback(result, total_elapsed, ticks_remaining)

            # Safety: if we crossed a year boundary, stop
            if result["end_year"] > start["cur_year"]:
                break

        self.disable_timestream()

        end = self.get_game_time()
        return {
            "start_season": start["season"],
            "end_season": end["season"],
            "total_elapsed": total_elapsed,
            "start_year": start["cur_year"],
            "end_year": end["cur_year"],
        }

    # ── Composite operations ───────────────────────────────────────

    def step_and_collect(self, ticks: int = 100,
                         poll_interval: float = 0.5,
                         timeout: float = 30.0) -> dict:
        """Step the game, refresh bridge data, and return both.

        Combined operation for the streaming loop:
        1. Step game by N ticks (unpause → wait → re-pause)
        2. Run bridge script to capture current state
        3. Read bridge JSON via SSH
        4. Return {step_result, bridge_data}
        """
        step_result = self.step(ticks, poll_interval, timeout)

        # Run bridge to capture post-step state
        self.run_bridge()

        # Fetch the updated bridge data
        bridge_data = self.fetch_bridge_data()

        return {
            "step": step_result,
            "bridge_data": bridge_data,
        }
