#!/usr/bin/env python3
"""Talk to DFHack over RPC from the shell.

The thin CLI edge of `chronicler.dfhack.client`, so `cx-lifecycle.sh` can do
a real RPC handshake rather than inferring health from a listening socket. A
bound port only proves DFHack started a listener; it says nothing about
whether the core will answer or execute Lua, and those are separate failures.

Runs against any DFHack the client can reach, so it serves the VM rig too:

    cx-rpc.py --version
    cx-rpc.py --lua 'print(dfhack.getDFVersion())'
    cx-rpc.py --cmd ls
    cx-rpc.py --host 192.168.64.3 --port 5000 --version
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run from a checkout without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chronicler.dfhack.client import DFHackClient  # noqa: E402


def emit(lines) -> None:
    """Print DFHack's reply.

    ⚠️ `run_command` yields `bytes` for some replies and `str` for others --
    a Lua traceback comes back as bytes while a short `print` comes back as
    text. Assuming either one crashes on the other, and it crashes in the
    REPORTING path, so a working query looks like a broken tool.
    """
    for line in lines:
        text = line.decode("utf-8", "replace") if isinstance(line, bytes) else line
        print(text, end="" if text.endswith("\n") else "\n")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1",
                   help="default 127.0.0.1 — the CrossOver rig is local")
    p.add_argument("--port", type=int, default=5555)
    p.add_argument("--timeout", type=float, default=15.0)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--version", action="store_true", help="DFHack version")
    g.add_argument("--lua", metavar="SCRIPT", help="run a Lua script")
    # ⚠️ REMAINDER, not nargs="+": DFHack commands carry their own flags, and
    # `repeat --name x --time 100` had argparse claiming --name and --time as
    # cx-rpc's own options and refusing the call. REMAINDER stops parsing and
    # forwards everything verbatim.
    g.add_argument("--cmd", nargs=argparse.REMAINDER, metavar="ARG",
                   help="run a DFHack command (all following args are passed on)")
    args = p.parse_args()

    # A port of 0 or empty means the caller could not find a listener. Say so
    # rather than failing inside the socket layer with a confusing message.
    if not args.port:
        print("no DFHack port — is the session running?", file=sys.stderr)
        return 2

    client = DFHackClient(args.host, args.port, timeout=args.timeout)
    try:
        client.connect()
        if args.version:
            print(client.get_version())
        elif args.lua:
            emit(client.run_command("lua", args.lua))
        else:
            emit(client.run_command(*args.cmd))
    except (OSError, TimeoutError) as e:
        # ⚠️ A timeout here does NOT mean the rig is broken. With no world
        # loaded, world/unit queries hang until the deadline because the core
        # never answers -- measured at the title screen. Name the ambiguity
        # rather than reporting a fault we have not established.
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            client.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
