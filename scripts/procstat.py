#!/usr/bin/env python3
"""Per-process resource counters on macOS, no root: proc_pid_rusage(RUSAGE_INFO_V4) through ctypes.

Used by the FPS experiments (fps5-run.py) to follow what a long Dwarf Fortress session burns: CPU time (user,
system), physical footprint and resident size, page-ins, and disk bytes read and written, for DF itself and for
CrossOver's wineserver. Counters are cumulative since the process started; a sampler differences them.

    python3 scripts/procstat.py            # one reading of DF and wineserver, as JSON
"""
import ctypes, json, os, subprocess, time
from ctypes import c_uint64, c_uint8

class RUsageInfoV4(ctypes.Structure):
    _fields_ = [("ri_uuid", c_uint8 * 16), ("ri_user_time", c_uint64), ("ri_system_time", c_uint64),
                ("ri_pkg_idle_wkups", c_uint64), ("ri_interrupt_wkups", c_uint64), ("ri_pageins", c_uint64),
                ("ri_wired_size", c_uint64), ("ri_resident_size", c_uint64), ("ri_phys_footprint", c_uint64),
                ("ri_proc_start_abstime", c_uint64), ("ri_proc_exit_abstime", c_uint64),
                ("ri_child_user_time", c_uint64), ("ri_child_system_time", c_uint64),
                ("ri_child_pkg_idle_wkups", c_uint64), ("ri_child_interrupt_wkups", c_uint64),
                ("ri_child_pageins", c_uint64), ("ri_child_elapsed_abstime", c_uint64),
                ("ri_diskio_bytesread", c_uint64), ("ri_diskio_byteswritten", c_uint64),
                ("ri_cpu_time_qos_default", c_uint64), ("ri_cpu_time_qos_maintenance", c_uint64),
                ("ri_cpu_time_qos_background", c_uint64), ("ri_cpu_time_qos_utility", c_uint64),
                ("ri_cpu_time_qos_legacy", c_uint64), ("ri_cpu_time_qos_user_initiated", c_uint64),
                ("ri_cpu_time_qos_user_interactive", c_uint64), ("ri_billed_system_time", c_uint64),
                ("ri_serviced_system_time", c_uint64), ("ri_logical_writes", c_uint64),
                ("ri_lifetime_max_phys_footprint", c_uint64), ("ri_instructions", c_uint64),
                ("ri_cycles", c_uint64), ("ri_billed_energy", c_uint64), ("ri_serviced_energy", c_uint64),
                ("ri_interval_max_phys_footprint", c_uint64), ("ri_runnable_time", c_uint64)]

_libproc = ctypes.CDLL("/usr/lib/libproc.dylib")
_libproc.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(RUsageInfoV4)]
_RUSAGE_INFO_V4 = 4

# ri_*_time are in mach absolute-time units; on Apple silicon they are not nanoseconds
class _Timebase(ctypes.Structure):
    _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]
_tb = _Timebase()
ctypes.CDLL("/usr/lib/libSystem.dylib").mach_timebase_info(ctypes.byref(_tb))
_NS = _tb.numer / _tb.denom

def pid_of(pattern: str) -> int | None:
    p = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    pids = [int(x) for x in p.stdout.split()]
    return pids[0] if pids else None

def rusage(pid: int) -> dict | None:
    info = RUsageInfoV4()
    if _libproc.proc_pid_rusage(pid, _RUSAGE_INFO_V4, ctypes.byref(info)) != 0:
        return None
    return {"cpu_user_s": info.ri_user_time * _NS / 1e9, "cpu_sys_s": info.ri_system_time * _NS / 1e9,
            "phys_footprint_mb": info.ri_phys_footprint / 2**20, "resident_mb": info.ri_resident_size / 2**20,
            "max_footprint_mb": info.ri_lifetime_max_phys_footprint / 2**20, "pageins": info.ri_pageins,
            "disk_read_mb": info.ri_diskio_bytesread / 2**20, "disk_written_mb": info.ri_diskio_byteswritten / 2**20,
            "logical_writes_mb": info.ri_logical_writes / 2**20, "instructions": info.ri_instructions,
            "cycles": info.ri_cycles, "wall": time.monotonic()}

def snapshot() -> dict:
    """DF, wineserver and the host's 1-minute load average, at one moment."""
    out: dict[str, object] = {"load1": os.getloadavg()[0]}
    for name, pat in (("df", "Dwarf Fortress.exe"), ("wine", "wineserver")):
        pid = pid_of(pat)
        out[name] = rusage(pid) if pid else None
    return out

def rates(a: dict, b: dict) -> dict:
    """What happened between two snapshots of one process: CPU cores used, MB/s of disk, page-ins/s."""
    if not a or not b:
        return {}
    dt = b["wall"] - a["wall"]
    if dt <= 0:
        return {}
    cpu = (b["cpu_user_s"] + b["cpu_sys_s"] - a["cpu_user_s"] - a["cpu_sys_s"]) / dt
    return {"cpu_cores": cpu, "sys_share": (b["cpu_sys_s"] - a["cpu_sys_s"]) / max(1e-9, cpu * dt),
            "disk_read_mbs": (b["disk_read_mb"] - a["disk_read_mb"]) / dt,
            "disk_write_mbs": (b["disk_written_mb"] - a["disk_written_mb"]) / dt,
            "pageins_s": (b["pageins"] - a["pageins"]) / dt,
            "ipc": ((b["instructions"] - a["instructions"]) / (b["cycles"] - a["cycles"])) if b["cycles"] > a["cycles"] else None}

if __name__ == "__main__":
    s1 = snapshot(); time.sleep(2); s2 = snapshot()
    print(json.dumps({"df": s2["df"], "wine": s2["wine"], "load1": s2["load1"], "df_rates": rates(s1["df"], s2["df"]),
                      "wine_rates": rates(s1["wine"], s2["wine"])}, indent=1))
