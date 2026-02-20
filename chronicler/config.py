"""Chronicler configuration — reads from environment or falls back to defaults."""

import os

PG_PASSWORD = os.environ.get("PG_PASSWORD", "OSDbeydP6TOBGoJUym6rTBfULKJYqqPE")
DB_DSN = os.environ.get(
    "CHRONICLER_DB_DSN",
    f"postgresql://jarvis:{PG_PASSWORD}@localhost:5432/chronicler",
)

DFHACK_HOST = os.environ.get("DFHACK_HOST", "192.168.64.2")
DFHACK_PORT = int(os.environ.get("DFHACK_PORT", "5000"))

MLX_EMBED_URL = os.environ.get("MLX_EMBED_URL", "http://localhost:8000")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://localhost:4000")

EMBED_DIM = 2560

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LEGENDS_DIR = os.path.join(DATA_DIR, "legends")
