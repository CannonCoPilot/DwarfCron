"""Chronicler configuration — reads from environment or falls back to defaults."""

import os

PG_PASSWORD = os.environ.get("PG_PASSWORD", "OSDbeydP6TOBGoJUym6rTBfULKJYqqPE")
DB_DSN = os.environ.get(
    "CHRONICLER_DB_DSN",
    f"postgresql://jarvis:{PG_PASSWORD}@localhost:5432/chronicler",
)

DFHACK_HOST = os.environ.get("DFHACK_HOST", "192.168.64.3")
DFHACK_PORT = int(os.environ.get("DFHACK_PORT", "5000"))

# Bridge: PowerShell HTTP server on DF machine serving chronicler-state.json
# Used when RFR is unavailable (DFHack 53.10-r1 — no RemoteFortressReader)
BRIDGE_HOST = os.environ.get("BRIDGE_HOST", "")  # empty = same as DFHACK_HOST
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8889"))

MLX_EMBED_URL = os.environ.get("MLX_EMBED_URL", "http://localhost:8000")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://localhost:4000")

EMBED_DIM = 2560

# LLM settings (for storyteller)
LLM_MODEL = os.environ.get("CHRONICLER_LLM_MODEL", "qwen3-8b-nothink")
LLM_TEMPERATURE = float(os.environ.get("CHRONICLER_LLM_TEMP", "0.8"))
LLM_MAX_TOKENS = int(os.environ.get("CHRONICLER_LLM_MAX_TOKENS", "2048"))

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LEGENDS_DIR = os.path.join(DATA_DIR, "legends")
