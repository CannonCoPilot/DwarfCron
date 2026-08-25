# PyInstaller spec — builds a single stand-alone `chronicler` binary.
#
# The binary carries the code, the Jinja2 explorer templates, the .sql migration
# files, and the DFHack .proto/Lua assets. It does NOT carry the database: the
# CDM lives in Postgres and is reached through CHRONICLER_DSN at runtime.
#
# Build:  .venv/bin/pyinstaller packaging/chronicler.spec --clean --noconfirm
# Result: dist/chronicler

from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = []
binaries = []
hiddenimports = [
    # Reached only through dynamic import or string reference.
    "chronicler.api.app",
    # uvicorn selects these at runtime by name, so the analyser never sees them.
    "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    # asyncpg builds its codec/protocol layer through late imports.
    "asyncpg.pgproto", "asyncpg.protocol",
]

# Packages with data files, C extensions, or dynamic submodule loading.
for pkg in ("jinja2", "asyncpg", "pgvector", "lxml", "httpx", "google.protobuf",
            "sse_starlette", "multipart", "numpy"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

datas += collect_data_files("certifi")

# Package data that is loaded from disk at runtime and would otherwise be lost:
# the explorer UI templates, the schema/migration SQL, and the DFHack assets.
import os

_root = os.path.abspath(os.path.join(SPECPATH, ".."))
datas += [
    (os.path.join(_root, "chronicler/api/templates"), "chronicler/api/templates"),
    (os.path.join(_root, "chronicler/db"), "chronicler/db"),
    (os.path.join(_root, "chronicler/dfhack/proto"), "chronicler/dfhack/proto"),
    (os.path.join(_root, "chronicler/dfhack/scripts"), "chronicler/dfhack/scripts"),
]

a = Analysis(
    ["entry.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["tkinter", "matplotlib", "PIL", "pytest", "pandas"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="chronicler",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
