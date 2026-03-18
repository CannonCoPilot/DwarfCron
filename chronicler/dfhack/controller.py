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
                 ssh_user: str = "Jarvis",
                 ssh_timeout: int = 10):
        self._host = host
        self._ssh_key = ssh_key
        self._ssh_user = ssh_user
        self._ssh_timeout = ssh_timeout
        # Build the PowerShell prefix for dfhack-run once
        self._dfhack_run_ps = _DFHACK_RUN.replace("\\", "\\\\")

    def _ssh(self, remote_cmd: str, timeout: int | None = None) -> str:
        """Execute a command on the VM via SSH and return stdout."""
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
                cmd, capture_output=True, text=True,
                timeout=t + 5,
            )
            if result.returncode != 0 and result.stderr.strip():
                log.warning("SSH stderr: %s", result.stderr.strip())
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise ControllerError(
                f"SSH command timed out after {self._ssh_timeout}s"
            )
        except FileNotFoundError:
            raise ControllerError("ssh binary not found")

    def _lua(self, code: str) -> str:
        """Execute a Lua snippet via SSH + PowerShell + dfhack-run.

        Uses PowerShell's & operator with single-quoted paths to avoid
        the SSH→cmd.exe→PowerShell quoting nightmare.
        """
        # PowerShell command: & 'path\to\dfhack-run.exe' lua 'code'
        # SSH wraps this in double quotes
        ps_cmd = (
            f"powershell -Command "
            f"\"& '{_DFHACK_RUN}' lua '{code}' \""
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
             timeout: float = 30.0) -> dict:
        """Advance the game by approximately `ticks` ticks, then re-pause.

        1. Record current tick
        2. Unpause
        3. Poll until tick has advanced by >= ticks
        4. Re-pause
        5. Return {start_tick, end_tick, elapsed_ticks, year, season}
        """
        start = self.get_game_time()
        start_tick = start["cur_year_tick"]
        start_year = start["cur_year"]
        target_tick = start_tick + ticks

        log.info("Stepping %d ticks from Y%d T%d", ticks, start_year, start_tick)

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
        """
        ps_cmd = (
            f"powershell -Command "
            f"\"& '{_DFHACK_RUN}' "
            f"'repeat --name chronicler --time {ticks} "
            f"--timeUnits ticks --command [ chronicler-bridge ]'\""
        )
        return self._ssh(ps_cmd)

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
